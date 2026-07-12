"""Characterization tests for the deserializers' error paths.

Locks in the CURRENT exception (or, for a couple of RDF/XML cases, the
current successful-but-vacuous outcome) that each deserializer produces for
various forms of malformed input. This is a characterization suite -- it
documents today's behaviour, it does not specify what the "right" behaviour
should be.

A few of the JSON cases surface a raw ``KeyError``/``AttributeError`` --
leaking an implementation detail -- instead of the package's own
``ProvJSONException``. Those are marked ``# 3.0 triage: (#228)`` below; per the
2.x output/behaviour freeze (see
docs/superpowers/specs/2026-07-03-modernisation-roadmap-design.md) they are
asserted as-is here rather than "fixed", pending the 3.0 fix tracked in #228.
"""

from json import JSONDecodeError
from pathlib import Path

import pytest
from lxml.etree import XMLSyntaxError
from rdflib.plugins.parsers.notation3 import BadSyntax

import prov
from prov.model import ProvDocument
from prov.serializers import DoNotExist
from prov.serializers.provxml import ProvXMLException

MALFORMED = Path(__file__).parent / "malformed"


@pytest.mark.parametrize(
    ("filename", "fmt", "expected_exc"),
    [
        pytest.param("not_json.json", "json", JSONDecodeError, id="json-syntax"),
        pytest.param(
            # 3.0 triage (#228): decode_json_container() does `PROV_RECORD_IDS_MAP[rec_type_str]`
            # where rec_type_str is a bare list item (int, here); raises a raw
            # KeyError instead of a ProvJSONException.
            "top_level_list.json",
            "json",
            KeyError,
            id="json-top-level-list",
        ),
        pytest.param(
            # 3.0 triage (#228): decode_json_container() does `jc[rec_type_str].items()`
            # assuming a dict-of-records; a string value raises a raw
            # AttributeError instead of a ProvJSONException.
            "bad_record_shape.json",
            "json",
            AttributeError,
            id="json-bad-record-shape",
        ),
        pytest.param(
            # 3.0 triage (#228): decode_json_container() does `prefixes.items()`
            # assuming the "prefix" value is itself a dict; a string value
            # raises a raw AttributeError instead of a ProvJSONException.
            "bad_prefix_map.json",
            "json",
            AttributeError,
            id="json-bad-prefix-map",
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
