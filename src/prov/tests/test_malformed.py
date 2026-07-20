"""Characterization tests for the deserializers' error paths.

Locks in the CURRENT exception (or, for a couple of RDF/XML cases, the
current successful-but-vacuous outcome) that each deserializer produces for
various forms of malformed input. This is a characterization suite -- it
documents today's behaviour, it does not specify what the "right" behaviour
should be.

Structurally malformed (but syntactically valid) PROV-JSON raises
``ProvJSONException`` -- the deserializer's own exception type -- rather than
leaking a raw ``KeyError``/``AttributeError`` (#228).
"""

from json import JSONDecodeError
from pathlib import Path

import pytest
from lxml.etree import XMLSyntaxError
from rdflib.plugins.parsers.notation3 import BadSyntax

import prov
from prov.model import ProvDocument
from prov.serializers import DoNotExist
from prov.serializers.provjson import ProvJSONException
from prov.serializers.provxml import ProvXMLException

MALFORMED = Path(__file__).parent / "malformed"


@pytest.mark.parametrize(
    ("filename", "fmt", "expected_exc"),
    [
        pytest.param("not_json.json", "json", JSONDecodeError, id="json-syntax"),
        pytest.param(
            # #228: a bare top-level JSON array, rather than an object; the
            # decoder rejects the container shape before it ever gets to
            # looking up record types.
            "top_level_list.json",
            "json",
            ProvJSONException,
            id="json-top-level-list",
        ),
        pytest.param(
            # #228: "entity" maps to a string instead of a dict-of-records.
            "bad_record_shape.json",
            "json",
            ProvJSONException,
            id="json-bad-record-shape",
        ),
        pytest.param(
            # #228: the "prefix" value is a string instead of a dict.
            "bad_prefix_map.json",
            "json",
            ProvJSONException,
            id="json-bad-prefix-map",
        ),
        pytest.param(
            # #228 sweep: a bare top-level JSON scalar (int/float/bool/null
            # all take the same path); the pre-fix code raised TypeError
            # from `"bundle" in content` before ever reaching the container
            # decoder.
            "top_level_scalar.json",
            "json",
            ProvJSONException,
            id="json-top-level-scalar",
        ),
        pytest.param(
            # #228 sweep: the "bundle" value is a string instead of a dict
            # mapping bundle identifiers to their containers.
            "bad_bundle_shape.json",
            "json",
            ProvJSONException,
            id="json-bad-bundle-shape",
        ),
        pytest.param(
            # #228 sweep: an "entity" record's content is `null` -- neither
            # a JSON object (single instance) nor a list of JSON objects
            # (multiple instances).
            "bad_record_content.json",
            "json",
            ProvJSONException,
            id="json-bad-record-content",
        ),
        pytest.param(
            # #228 sweep: a non-formal attribute's typed-literal
            # representation is missing its required "$" (value) key.
            "bad_typed_literal.json",
            "json",
            ProvJSONException,
            id="json-bad-typed-literal",
        ),
        pytest.param(
            # #228 sweep: a top-level key that isn't a recognised PROV-N
            # record-type keyword.
            "unknown_record_type.json",
            "json",
            ProvJSONException,
            id="json-unknown-record-type",
        ),
        pytest.param("empty.json", "json", JSONDecodeError, id="json-empty"),
        pytest.param(
            "not_well_formed.xml", "xml", XMLSyntaxError, id="xml-not-well-formed"
        ),
        pytest.param("wrong_root.xml", "xml", ProvXMLException, id="xml-wrong-root"),
        pytest.param("empty.xml", "xml", XMLSyntaxError, id="xml-empty"),
        pytest.param("not_turtle.ttl", "rdf", BadSyntax, id="rdf-not-turtle"),
    ],
)
def test_malformed_file_raises(filename, fmt, expected_exc):
    with (MALFORMED / filename).open() as f, pytest.raises(expected_exc):
        ProvDocument.deserialize(f, format=fmt)


# -- Cases that do NOT raise: the deserializer accepts the input but --------
# -- silently produces a vacuous (empty) document. That is itself a piece --
# -- of current behaviour worth locking in, rather than an exception. ------


def test_rdf_foreign_vocabulary_parses_but_yields_empty_document():
    """Well-formed Turtle with no PROV vocabulary at all.

    rdflib has no opinion on vocabulary, so it parses cleanly; none of the
    foaf triples are convertible to PROV records though, so
    ``decode_document()`` emits a ``UserWarning`` listing the un-converted
    subjects and returns an otherwise-empty ``ProvDocument``. No exception is
    raised.
    """
    path = MALFORMED / "foreign_vocabulary.ttl"
    with path.open() as f, pytest.warns(UserWarning, match="not converted"):
        doc = ProvDocument.deserialize(f, format="rdf")
    assert list(doc.get_records()) == []


def test_rdf_empty_file_parses_to_empty_document():
    """An empty file is vacuously valid Turtle/TriG.

    rdflib parses it to an empty graph and no exception is raised.
    """
    path = MALFORMED / "empty.rdf"
    with path.open() as f:
        doc = ProvDocument.deserialize(f, format="rdf")
    assert list(doc.get_records()) == []


# -- prov.read() and unknown-format cases: don't fit the file parametrize --


def test_xml_childless_foreign_root_parses_to_empty_document():
    """A well-formed, *childless* foreign root element yields an empty document.

    Note the asymmetry with the ``wrong_root.xml`` parametrize case above: a
    foreign root that *contains* a child element (``<html><body>...</body></html>``)
    raises ``ProvXMLException`` ("Non PROV element discovered..."), but a foreign
    root with no children (``<foo/>``) is walked with nothing to reject, so the
    deserializer returns an empty ``ProvDocument`` without raising. Both are
    current behaviour worth locking in.
    """
    path = MALFORMED / "empty_root.xml"
    with path.open() as f:
        doc = ProvDocument.deserialize(f, format="xml")
    assert list(doc.get_records()) == []


def test_read_on_unparseable_content_raises_type_error(tmp_path):
    """``prov.read()`` on content none of the auto-detected deserializers accept.

    With ``format=None``, ``read()`` tries each registered format in turn
    (json, rdf, provn, xml -- see ``Registry.load_serializers()``). Since
    #239, ANY exception from a candidate deserializer -- including rdflib's
    ``BadSyntax`` on the rdf attempt -- means "not this format" and
    auto-detection moves on to the next candidate. For a real file with
    genuinely unparseable content, every candidate fails and ``read()``
    raises its own ``TypeError`` rather than leaking the last candidate's
    exception. This mirrors ``test_read_auto_detect_swallows_any_deserializer_error``
    in test_read.py.
    """
    path = tmp_path / "garbage.txt"
    path.write_text("this is not any known prov serialization at all, just prose.")
    with pytest.raises(TypeError):
        prov.read(str(path))


def test_deserialize_unknown_format_raises_do_not_exist():
    """``ProvDocument.deserialize(..., format="nope")`` -- unknown format.

    ``serializers.get()`` looks the format up in the ``Registry`` and raises
    ``DoNotExist`` (imported from ``prov.serializers``, where it is defined)
    on a miss.
    """
    with pytest.raises(DoNotExist):
        ProvDocument.deserialize(content="{}", format="nope")
