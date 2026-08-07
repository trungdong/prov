"""PROV-JSONLD format-specific tests: encoder shape, options, error paths."""

import json

import pytest

from prov.model import ProvDocument
from prov.serializers.provjsonld import JSONLD_CONTEXT_URL, ProvJSONLDException

EX_URI = "http://example.org/"


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
