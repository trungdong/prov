"""PROV-JSONLD format-specific tests: encoder shape, options, error paths."""

import json
from pathlib import Path

import pytest

import prov
from prov.model import Literal, ProvDocument
from prov.serializers.provjsonld import JSONLD_CONTEXT_URL, ProvJSONLDException

EX_URI = "http://example.org/"
FIXTURE_DIR = Path(__file__).parent / "jsonld"


def _new_doc() -> ProvDocument:
    doc = ProvDocument()
    doc.add_namespace("ex", EX_URI)
    return doc


def _dump(doc: ProvDocument, **kwargs) -> dict:
    return json.loads(doc.serialize(format="jsonld", **kwargs))


def test_serialize_basic_shape():
    doc = _new_doc()
    doc.entity("ex:e1")
    doc.activity("ex:a1", "2011-11-16T16:05:00", "2011-11-16T16:06:00")
    doc.wasGeneratedBy("ex:e1", "ex:a1", time="2011-11-16T16:05:30")
    container = _dump(doc)
    assert set(container) == {"@context", "@graph"}
    assert container["@context"] == [{"ex": EX_URI}, JSONLD_CONTEXT_URL]
    by_type = {stmt["@type"]: stmt for stmt in container["@graph"]}
    assert by_type["Entity"]["@id"] == "ex:e1"
    assert by_type["Activity"]["startTime"] == "2011-11-16T16:05:00"
    assert by_type["Activity"]["endTime"] == "2011-11-16T16:06:00"
    gen = by_type["Generation"]
    assert gen["entity"] == "ex:e1"
    assert gen["activity"] == "ex:a1"
    assert gen["time"] == "2011-11-16T16:05:30"
    assert "@id" not in gen  # anonymous relation: no @id emitted


def test_serialize_special_and_extra_attributes():
    doc = _new_doc()
    doc.entity(
        "ex:e1",
        (
            ("prov:type", doc.valid_qualified_name("ex:Sort")),
            ("prov:label", "hello"),
            ("ex:price", 42),
            ("ex:note", "plain"),
        ),
    )
    (stmt,) = _dump(doc)["@graph"]
    assert stmt["type"] == ["ex:Sort"]  # @id-typed term: bare qualified name
    assert stmt["label"] == [{"@value": "hello"}]
    assert stmt["ex:price"] == [{"@value": "42", "@type": "xsd:int"}]
    assert stmt["ex:note"] == [{"@value": "plain"}]


def test_serialize_bundle_nesting():
    doc = _new_doc()
    bundle = doc.bundle("ex:b1")
    bundle.entity("ex:e2")
    container = _dump(doc)
    (bundle_obj,) = [s for s in container["@graph"] if s["@type"] == "Bundle"]
    assert bundle_obj["@id"] == "ex:b1"
    assert isinstance(bundle_obj["@context"], list)
    assert bundle_obj["@graph"][0]["@id"] == "ex:e2"


def test_serialize_default_namespace_as_vocab():
    doc = ProvDocument()
    doc.set_default_namespace(EX_URI)
    doc.entity("e1")
    container = _dump(doc)
    assert container["@context"][0]["@vocab"] == EX_URI


def test_serialize_context_embed():
    doc = _new_doc()
    doc.entity("ex:e1")
    container = _dump(doc, context="embed")
    embedded = container["@context"][1]
    assert isinstance(embedded, dict)
    assert "Entity" in embedded  # the vendored context object, not the URL


def test_serialize_context_bad_option():
    doc = _new_doc()
    doc.entity("ex:e1")
    with pytest.raises(ValueError, match="context"):
        doc.serialize(format="jsonld", context="nonsense")


def test_serialize_mention_raises():
    doc = _new_doc()
    doc.mention("ex:e2", "ex:e1", "ex:b")
    with pytest.raises(ProvJSONLDException, match=r"[Mm]ention"):
        doc.serialize(format="jsonld")


def _roundtrip(doc: ProvDocument) -> ProvDocument:
    return ProvDocument.deserialize(
        content=doc.serialize(format="jsonld"), format="jsonld"
    )


def test_roundtrip_all_record_types():
    doc = _new_doc()
    e1 = doc.entity("ex:e1")
    e2 = doc.entity("ex:e2")
    a1 = doc.activity("ex:a1", "2011-11-16T16:05:00")
    ag = doc.agent("ex:ag")
    doc.wasGeneratedBy(e1, a1)
    doc.used(a1, e2)
    doc.wasInformedBy(a1, a1)
    doc.wasStartedBy(a1, e2, time="2011-11-16T16:05:00")
    doc.wasEndedBy(a1, e2)
    doc.wasInvalidatedBy(e1, a1)
    doc.wasDerivedFrom(e1, e2)
    doc.wasAttributedTo(e1, ag)
    doc.wasAssociatedWith(a1, ag)
    doc.actedOnBehalfOf(ag, ag)
    doc.wasInfluencedBy(e1, a1)
    doc.specializationOf(e2, e1)
    doc.alternateOf(e1, e2)
    doc.membership(e1, e2)
    assert _roundtrip(doc) == doc


def test_roundtrip_bundle_and_default_namespace():
    doc = ProvDocument()
    doc.set_default_namespace(EX_URI)
    doc.entity("e1")
    bundle = doc.bundle("e_bundle")
    bundle.entity("e2")
    assert _roundtrip(doc) == doc


def test_roundtrip_attribute_values():
    import datetime

    doc = _new_doc()
    doc.entity(
        "ex:e1",
        (
            ("prov:label", "plain"),
            ("prov:label", Literal("bonjour", langtag="fr")),
            ("prov:type", doc.valid_qualified_name("ex:Sort")),
            ("ex:int", 42),
            ("ex:float", 3.14),
            ("ex:bool", True),
            ("ex:time", datetime.datetime(2011, 11, 16, 16, 5)),
        ),
    )
    assert _roundtrip(doc) == doc


def test_deserialize_accepts_provtoolbox_prefixed_terms():
    text = json.dumps(
        {
            "@context": [{"ex": EX_URI}, JSONLD_CONTEXT_URL],
            "@graph": [
                {
                    "@type": "prov:Entity",
                    "@id": "ex:e1",
                    "prov:type": ["prov:Collection"],
                }
            ],
        }
    )
    doc = ProvDocument.deserialize(content=text, format="jsonld")
    expected = _new_doc()
    expected.entity(
        "ex:e1",
        (("prov:type", expected.valid_qualified_name("prov:Collection")),),
    )
    assert doc == expected


@pytest.mark.parametrize(
    "payload, match",
    [
        ({"entity": {"ex:e1": {}}}, "@graph"),  # PROV-JSON shape rejected
        ({"@context": [], "@graph": [["not-an-object"]]}, "object"),
        (
            {"@context": [], "@graph": [{"@type": "Frobnication"}]},
            "Frobnication",
        ),
        ({"@context": [], "@graph": [{"@type": "Mention"}]}, "Mention"),
        ({"@context": [], "@graph": [{"@type": "Entity"}]}, "@id"),
        (
            {
                "@context": [],
                "@graph": [{"@type": "Generation", "entity": ["ex:e1", "ex:e2"]}],
            },
            "single",
        ),
        ({"@context": [], "@graph": [{"@type": None}]}, "@type"),
        ({"@context": [], "@graph": [{"@type": 123}]}, "@type"),
        ({"@context": [], "@graph": [{"@type": ["Entity"]}]}, "@type"),
    ],
)
def test_deserialize_malformed(payload, match):
    with pytest.raises(ProvJSONLDException, match=match):
        ProvDocument.deserialize(content=json.dumps(payload), format="jsonld")


def _expected_primer_document() -> ProvDocument:
    """Build the document ``submission-example-3.jsonld`` is expected to decode to."""
    doc = ProvDocument()
    doc.add_namespace("xsd", "http://www.w3.org/2001/XMLSchema#")
    doc.add_namespace("dcterms", "http://purl.org/dc/terms/")
    doc.add_namespace("ex", "http://example/")
    doc.add_namespace("foaf", "http://xmlns.com/foaf/0.1/")
    doc.entity("ex:dataSet1")
    doc.entity(
        "ex:article1",
        (("dcterms:title", Literal("Crime rises in cities", langtag="EN")),),
    )
    doc.wasDerivedFrom("ex:article1", "ex:dataSet1")
    doc.agent(
        "ex:derek",
        (
            ("prov:type", doc.valid_qualified_name("prov:Person")),
            ("foaf:givenName", "Derek"),
            ("foaf:mbox", "<mailto:derek@example.org>"),
        ),
    )
    doc.wasAssociatedWith("ex:compose", "ex:derek")
    doc.activity("ex:compose")
    doc.used("ex:compose", "ex:dataSet1")
    doc.wasGeneratedBy("ex:article1", "ex:compose")
    return doc


def test_interop_submission_example():
    doc = prov.read(str(FIXTURE_DIR / "submission-example-3.jsonld"), format="jsonld")
    assert doc == _expected_primer_document()
    assert _roundtrip(doc) == doc


def _expected_provtoolbox_primer_document() -> ProvDocument:
    """Build the document ``provtoolbox-mini-primer.jsonld`` is expected to decode to.

    Differs from :func:`_expected_primer_document` in ``ex:derek``'s
    ``foaf:mbox``: the ProvToolbox fixture (as vendored) carries an empty
    string there rather than the submission example's mailto value -- see
    ``src/prov/tests/jsonld/README.md``.
    """
    doc = ProvDocument()
    doc.add_namespace("xsd", "http://www.w3.org/2001/XMLSchema#")
    doc.add_namespace("dcterms", "http://purl.org/dc/terms/")
    doc.add_namespace("ex", "http://example/")
    doc.add_namespace("foaf", "http://xmlns.com/foaf/0.1/")
    doc.entity("ex:dataSet1")
    doc.entity(
        "ex:article1",
        (("dcterms:title", Literal("Crime rises in cities", langtag="EN")),),
    )
    doc.wasDerivedFrom("ex:article1", "ex:dataSet1")
    doc.agent(
        "ex:derek",
        (
            ("foaf:mbox", ""),
            ("prov:type", doc.valid_qualified_name("prov:Person")),
            ("foaf:givenName", "Derek"),
        ),
    )
    doc.wasAssociatedWith("ex:compose", "ex:derek")
    doc.activity("ex:compose")
    doc.used("ex:compose", "ex:dataSet1")
    doc.wasGeneratedBy("ex:article1", "ex:compose")
    return doc


def test_interop_provtoolbox_mini_primer():
    doc = prov.read(
        str(FIXTURE_DIR / "provtoolbox-mini-primer.jsonld"), format="jsonld"
    )
    assert doc == _expected_provtoolbox_primer_document()
    assert _roundtrip(doc) == doc
