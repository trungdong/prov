"""PROV-JSONLD format-specific tests: encoder shape, options, error paths."""

import io
import json
from pathlib import Path

import pytest

import prov
from prov.model import Literal, ProvDocument
from prov.serializers.provjsonld import (
    JSONLD_CONTEXT_URL,
    ProvJSONLDException,
    ProvJSONLDSerializer,
)

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
    # "@vocab" alone would only govern bare property terms and bare "@type"
    # values in real JSON-LD -- NOT "@id" values or @id-typed terms like
    # "entity"/"activity" -- so a bare identifier like "e1" would resolve
    # against a consumer's own document base rather than EX_URI. "@base"
    # must be emitted alongside "@vocab", pointing at the same URI, so those
    # values resolve correctly too (see the pyld-backed proof in
    # test_jsonld_semantics.py).
    assert container["@context"][0]["@base"] == EX_URI


def test_serialize_no_default_namespace_omits_base():
    doc = _new_doc()
    doc.entity("ex:e1")
    container = _dump(doc)
    assert "@base" not in container["@context"][0]
    assert "@vocab" not in container["@context"][0]


def test_serialize_default_namespace_attribute_uses_absolute_iri_key():
    # A non-formal attribute in the default namespace has no prefix, so its
    # bare local part ("mine") would be indistinguishable from a JSON-LD
    # term the context itself defines and is schema-invalid regardless
    # (patternProperties requires a "prefix:local" shape); the encoder must
    # emit the absolute IRI as the key instead.
    doc = ProvDocument()
    doc.set_default_namespace(EX_URI)
    doc.entity("e1", {"mine": "x"})
    (stmt,) = _dump(doc)["@graph"]
    assert stmt[EX_URI + "mine"] == [{"@value": "x"}]
    assert "mine" not in stmt


def test_serialize_default_namespace_attribute_colliding_with_reserved_term():
    # "type" is one of the 5 special (bare) terms the context defines; a
    # default-namespace attribute that happens to be called "type" must not
    # collide with it.
    doc = ProvDocument()
    doc.set_default_namespace(EX_URI)
    doc.entity("e1", {"type": "y"})
    (stmt,) = _dump(doc)["@graph"]
    assert stmt[EX_URI + "type"] == [{"@value": "y"}]
    assert "type" not in stmt


def test_serialize_default_namespace_attribute_colliding_with_formal_attribute():
    # Regression for a formal attribute being silently overwritten: Usage's
    # formal "entity" attribute is written first, then a non-formal
    # default-namespace attribute also called "entity" must not clobber it.
    doc = ProvDocument()
    doc.set_default_namespace(EX_URI)
    doc.activity("a1")
    doc.entity("e1")
    doc.used("a1", "e1", other_attributes={"entity": "collides"})
    (stmt,) = [s for s in _dump(doc)["@graph"] if s["@type"] == "Usage"]
    assert stmt["entity"] == "e1"  # the formal attribute, untouched
    assert stmt[EX_URI + "entity"] == [{"@value": "collides"}]


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


def test_serialize_without_a_document_raises():
    serializer = ProvJSONLDSerializer(document=None)
    with pytest.raises(ProvJSONLDException) as ctx:
        serializer.serialize(io.BytesIO())
    assert "No document to serialize" in str(ctx.value)


def _roundtrip(doc: ProvDocument) -> ProvDocument:
    return ProvDocument.deserialize(
        content=doc.serialize(format="jsonld"), format="jsonld"
    )


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


def test_deserialize_mixed_context_registers_namespace_prefixes():
    # A third-party context object can carry plain prefix strings alongside
    # one inline term definition (a dict value) without being the vendored
    # submission context (see _is_embedded_submission_context): every
    # string-valued prefix in it must still be registered, and "ex:e1" must
    # resolve, even though "myTerm" (a dict value this library doesn't model)
    # sits right next to "ex" in the same object.
    text = json.dumps(
        {
            "@context": [
                {"ex": EX_URI, "myTerm": {"@id": EX_URI + "myTerm"}},
                JSONLD_CONTEXT_URL,
            ],
            "@graph": [{"@type": "Entity", "@id": "ex:e1"}],
        }
    )
    doc = ProvDocument.deserialize(content=text, format="jsonld")
    expected = _new_doc()
    expected.entity("ex:e1")
    assert doc == expected
    assert {ns.prefix: ns.uri for ns in doc.get_registered_namespaces()} == {
        "ex": EX_URI
    }


def test_deserialize_context_with_version_registers_namespace_prefixes():
    # "@version": 1.1 is a normal, common JSON-LD 1.1 context marker, not
    # unique to the vendored embedded submission context -- a namespace map
    # that happens to declare it must not be misclassified as that context
    # and have its prefixes silently dropped.
    text = json.dumps(
        {
            "@context": [
                {"@version": 1.1, "ex": EX_URI},
                JSONLD_CONTEXT_URL,
            ],
            "@graph": [{"@type": "Entity", "@id": "ex:e1"}],
        }
    )
    doc = ProvDocument.deserialize(content=text, format="jsonld")
    expected = _new_doc()
    expected.entity("ex:e1")
    assert doc == expected
    assert {ns.prefix: ns.uri for ns in doc.get_registered_namespaces()} == {
        "ex": EX_URI
    }


def test_deserialize_context_with_one_colliding_term_registers_namespace_prefixes():
    # A single object-valued term whose key happens to collide with one of
    # PROV-DM's own record-type local names ("Entity") is not, by itself,
    # evidence that the whole object is the embedded submission context
    # (which defines all 17 such terms) -- a lone coincidence must not
    # cause "ex" to be dropped.
    text = json.dumps(
        {
            "@context": [
                {"ex": EX_URI, "Entity": {"@id": EX_URI + "SomeUnrelatedThing"}},
                JSONLD_CONTEXT_URL,
            ],
            "@graph": [{"@type": "Entity", "@id": "ex:e1"}],
        }
    )
    doc = ProvDocument.deserialize(content=text, format="jsonld")
    expected = _new_doc()
    expected.entity("ex:e1")
    assert doc == expected
    assert {ns.prefix: ns.uri for ns in doc.get_registered_namespaces()} == {
        "ex": EX_URI
    }


def test_roundtrip_context_embed_registers_no_extra_namespaces():
    # The embedded submission context (context="embed") must still be
    # recognised as a whole and skipped -- not treated as a namespace map --
    # or its own prov/xsd/rdfs/rdf prefix strings would get registered on
    # the bundle, changing what deserialize() produces (see the docstring of
    # _is_embedded_submission_context).
    doc = _new_doc()
    doc.entity("ex:e1")
    doc.activity("ex:a1", "2011-11-16T16:05:00")
    doc.wasGeneratedBy("ex:e1", "ex:a1")
    roundtripped = ProvDocument.deserialize(
        content=doc.serialize(format="jsonld", context="embed"), format="jsonld"
    )
    assert roundtripped == doc
    assert {ns.prefix for ns in roundtripped.get_registered_namespaces()} == {"ex"}


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
    doc = prov.read(FIXTURE_DIR / "submission-example-3.jsonld", format="jsonld")
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
    doc = prov.read(FIXTURE_DIR / "provtoolbox-mini-primer.jsonld", format="jsonld")
    assert doc == _expected_provtoolbox_primer_document()
    assert _roundtrip(doc) == doc
