"""PROV-JSONLD format-specific tests: encoder shape, options, error paths."""

import io
import json
import warnings
from pathlib import Path

import pytest

import prov
from prov.constants import PROV
from prov.model import (
    XSD_QNAME,
    Identifier,
    Literal,
    Namespace,
    ProvDocument,
    ProvFutureRejectionWarning,
    ProvMembership,
    ProvWarning,
)
from prov.serializers.provjsonld import (
    JSONLD_CONTEXT_URL,
    ProvJSONLDException,
    ProvJSONLDSerializer,
    decode_jsonld_value,
)

EX_URI = "http://example.org/"
FIXTURE_DIR = Path(__file__).parent / "jsonld"


def _new_doc() -> ProvDocument:
    doc = ProvDocument()
    doc.add_namespace("ex", EX_URI)
    return doc


def _dump(doc: ProvDocument, **kwargs) -> dict:
    return json.loads(doc.serialize(format="jsonld", **kwargs))


def test_serialize_basic_shape() -> None:
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


def test_serialize_special_and_extra_attributes() -> None:
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


def test_serialize_bundle_nesting() -> None:
    doc = _new_doc()
    bundle = doc.bundle("ex:b1")
    bundle.entity("ex:e2")
    container = _dump(doc)
    (bundle_obj,) = [s for s in container["@graph"] if s["@type"] == "Bundle"]
    assert bundle_obj["@id"] == "ex:b1"
    assert isinstance(bundle_obj["@context"], list)
    assert bundle_obj["@graph"][0]["@id"] == "ex:e2"


def test_serialize_default_namespace_as_vocab() -> None:
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


def test_serialize_no_default_namespace_omits_base() -> None:
    doc = _new_doc()
    doc.entity("ex:e1")
    container = _dump(doc)
    assert "@base" not in container["@context"][0]
    assert "@vocab" not in container["@context"][0]


def test_serialize_default_namespace_attribute_uses_absolute_iri_key() -> None:
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


def test_serialize_default_namespace_attribute_colliding_with_reserved_term() -> None:
    # "type" is one of the 5 special (bare) terms the context defines; a
    # default-namespace attribute that happens to be called "type" must not
    # collide with it.
    doc = ProvDocument()
    doc.set_default_namespace(EX_URI)
    doc.entity("e1", {"type": "y"})
    (stmt,) = _dump(doc)["@graph"]
    assert stmt[EX_URI + "type"] == [{"@value": "y"}]
    assert "type" not in stmt


def test_serialize_default_namespace_attribute_colliding_with_formal_attribute() -> (
    None
):
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


def test_serialize_context_embed() -> None:
    doc = _new_doc()
    doc.entity("ex:e1")
    container = _dump(doc, context="embed")
    embedded = container["@context"][1]
    assert isinstance(embedded, dict)
    assert "Entity" in embedded  # the vendored context object, not the URL


def test_serialize_context_bad_option() -> None:
    doc = _new_doc()
    doc.entity("ex:e1")
    with pytest.raises(ValueError, match="context"):
        doc.serialize(format="jsonld", context="nonsense")


def test_serialize_mention_raises() -> None:
    doc = _new_doc()
    doc.mention("ex:e2", "ex:e1", "ex:b")
    with pytest.raises(ProvJSONLDException, match=r"[Mm]ention"):
        doc.serialize(format="jsonld")


def test_serialize_without_a_document_raises() -> None:
    serializer = ProvJSONLDSerializer(document=None)
    with pytest.raises(ProvJSONLDException) as ctx:
        serializer.serialize(io.BytesIO())
    assert "No document to serialize" in str(ctx.value)


def _roundtrip(doc: ProvDocument) -> ProvDocument:
    return ProvDocument.deserialize(
        content=doc.serialize(format="jsonld"), format="jsonld"
    )


def test_deserialize_accepts_provtoolbox_prefixed_terms() -> None:
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


def test_deserialize_mixed_context_registers_namespace_prefixes() -> None:
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


def test_deserialize_context_with_version_registers_namespace_prefixes() -> None:
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


def test_deserialize_context_with_one_colliding_term_registers_namespace_prefixes() -> (
    None
):
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


def test_roundtrip_context_embed_registers_no_extra_namespaces() -> None:
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
        ({"@context": [], "@graph": {}}, "must be a JSON array; found dict"),
        (
            {"@context": [], "@graph": [{"@type": "Bundle"}]},
            'A Bundle requires an "@id"',
        ),
    ],
)
def test_deserialize_malformed(payload, match) -> None:
    with pytest.raises(ProvJSONLDException, match=match):
        ProvDocument.deserialize(content=json.dumps(payload), format="jsonld")


def _membership_payload(entities) -> str:
    return json.dumps(
        {
            "@context": [{"ex": EX_URI}, JSONLD_CONTEXT_URL],
            "@graph": [
                {"@type": "Entity", "@id": "ex:c"},
                {"@type": "Membership", "collection": "ex:c", "entity": entities},
            ],
        }
    )


def test_deserialize_membership_entity_array_gives_one_record_per_member() -> None:
    # Submission 4.18: "a single entity or an array of them"; PROV-DM's
    # hadMember is binary, so the array fans out.
    doc = ProvDocument.deserialize(
        content=_membership_payload(["ex:e1", "ex:e2"]), format="jsonld"
    )
    expected = _new_doc()
    expected.entity("ex:c")
    expected.hadMember("ex:c", "ex:e1")
    expected.hadMember("ex:c", "ex:e2")
    assert doc == expected


def test_deserialize_membership_single_element_array() -> None:
    # ProvToolbox writes the array form even for one member.
    doc = ProvDocument.deserialize(
        content=_membership_payload(["ex:e1"]), format="jsonld"
    )
    expected = _new_doc()
    expected.entity("ex:c")
    expected.hadMember("ex:c", "ex:e1")
    assert doc == expected


def test_deserialize_membership_empty_entity_array_raises() -> None:
    with pytest.raises(ProvJSONLDException, match="empty"):
        ProvDocument.deserialize(content=_membership_payload([]), format="jsonld")


def test_deserialize_membership_member_that_does_not_resolve_raises() -> None:
    with pytest.raises(ProvJSONLDException, match="'foo:e2'"):
        ProvDocument.deserialize(
            content=_membership_payload(["ex:e1", "foo:e2"]), format="jsonld"
        )


def _identified_membership_payload(entities) -> str:
    return json.dumps(
        {
            "@context": [{"ex": EX_URI}, JSONLD_CONTEXT_URL],
            "@graph": [
                {"@type": "Entity", "@id": "ex:c"},
                {
                    "@type": "Membership",
                    "@id": "ex:m",
                    "collection": "ex:c",
                    "entity": entities,
                    "label": [{"@value": "members"}],
                },
            ],
        }
    )


def test_deserialize_identified_membership_array_gives_every_member_the_id() -> None:
    # Submission section 4.18 lets a Membership carry an @id and an array of
    # members; every record of the fan-out keeps the @id and the attributes.
    payload = _identified_membership_payload(["ex:e1", "ex:e2"])
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvWarning)
        doc = ProvDocument.deserialize(content=payload, format="jsonld")
    memberships = sorted(doc.get_records(ProvMembership), key=lambda r: str(r.args[1]))
    assert [str(r.identifier) for r in memberships] == ["ex:m", "ex:m"]
    assert [str(r.args[1]) for r in memberships] == ["ex:e1", "ex:e2"]
    assert all(list(r.get_attribute(PROV["label"])) == ["members"] for r in memberships)
    assert len(list(doc.unified().get_records(ProvMembership))) == 2


def test_deserialize_identified_membership_with_one_member_keeps_the_id() -> None:
    payload = _identified_membership_payload(["ex:e1"])
    doc = ProvDocument.deserialize(content=payload, format="jsonld")
    (membership,) = doc.get_records(ProvMembership)
    assert str(membership.identifier) == "ex:m"


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


def test_interop_submission_example() -> None:
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


def test_interop_provtoolbox_mini_primer() -> None:
    doc = prov.read(FIXTURE_DIR / "provtoolbox-mini-primer.jsonld", format="jsonld")
    assert doc == _expected_provtoolbox_primer_document()
    assert _roundtrip(doc) == doc


FOAF_URI = "http://xmlns.com/foaf/0.1/"


def _arthur_document(past_project) -> ProvDocument:
    """Build the document the ProvToolbox ``prov-jsonld-7`` fixtures decode to."""
    doc = _new_doc()
    doc.add_namespace("foaf", FOAF_URI)
    doc.entity("ex:shed")
    doc.agent("ex:arthur", (("foaf:pastProject", past_project),))
    return doc


def test_interop_provtoolbox_node_reference_is_a_qualified_name() -> None:
    doc = prov.read(FIXTURE_DIR / "provtoolbox-node-reference.jsonld", format="jsonld")
    assert doc == _arthur_document(Namespace("ex", EX_URI)["shed"])


def test_interop_provtoolbox_bare_string_under_extension_key_is_a_string() -> None:
    doc = prov.read(FIXTURE_DIR / "provtoolbox-string.jsonld", format="jsonld")
    assert doc == _arthur_document("ex:shed")


def test_interop_provtoolbox_string_with_colon() -> None:
    doc = prov.read(
        FIXTURE_DIR / "provtoolbox-string-with-colon.jsonld", format="jsonld"
    )
    expected = _new_doc()
    expected.activity("ex:meeting", other_attributes={"ex:note": "Meeting at 10:30"})
    assert doc == expected


def _entity_with(key: str, values: list) -> str:
    return json.dumps(
        {
            "@context": [{"ex": EX_URI}, JSONLD_CONTEXT_URL],
            "@graph": [{"@type": "Entity", "@id": "ex:e1", key: values}],
        }
    )


@pytest.mark.parametrize("key", ["type", "prov:type", "value", "ex:ref"])
def test_deserialize_node_reference_under_any_key(key) -> None:
    doc = ProvDocument.deserialize(
        content=_entity_with(key, [{"@id": "ex:thing"}]), format="jsonld"
    )
    (entity,) = doc.get_records()
    (value,) = [v for _, v in entity.extra_attributes]
    assert value == doc.valid_qualified_name("ex:thing")


def test_deserialize_node_reference_with_absolute_iri() -> None:
    doc = ProvDocument.deserialize(
        content=_entity_with("ex:ref", [{"@id": EX_URI + "thing"}]), format="jsonld"
    )
    (entity,) = doc.get_records()
    (value,) = [v for _, v in entity.extra_attributes]
    assert value == doc.valid_qualified_name("ex:thing")


@pytest.mark.parametrize("iri", ["http://other.org/x", "nope:thing"])
def test_deserialize_node_reference_outside_every_namespace_is_an_identifier(
    iri,
) -> None:
    doc = ProvDocument.deserialize(
        content=_entity_with("ex:ref", [{"@id": iri}]), format="jsonld"
    )
    (entity,) = doc.get_records()
    (value,) = [v for _, v in entity.extra_attributes]
    assert value == Identifier(iri)


@pytest.mark.parametrize(
    "extra",
    [{"@value": "x"}, {"@type": "xsd:string"}, {"@language": "en"}, {"ex:p": "x"}],
)
def test_deserialize_node_reference_with_other_keys_raises(extra) -> None:
    payload = _entity_with("ex:ref", [{"@id": "ex:thing", **extra}])
    with pytest.raises(ProvJSONLDException, match="@id"):
        ProvDocument.deserialize(content=payload, format="jsonld")


@pytest.mark.parametrize("node_id", [42, ""])
def test_deserialize_node_reference_with_bad_id_raises(node_id) -> None:
    payload = _entity_with("ex:ref", [{"@id": node_id}])
    with pytest.raises(ProvJSONLDException, match="@id"):
        ProvDocument.deserialize(content=payload, format="jsonld")


def test_deserialize_value_object_without_value_raises() -> None:
    payload = _entity_with("ex:ref", [{"@type": "xsd:string"}])
    with pytest.raises(ProvJSONLDException, match="@value"):
        ProvDocument.deserialize(content=payload, format="jsonld")


@pytest.mark.parametrize("datatype", ["xsd:QName", "prov:QUALIFIED_NAME"])
def test_deserialize_typed_value_that_is_a_full_iri_warns(datatype: str) -> None:
    # The reader compacts the IRI to ex:thing; 3.3.0 rejects the value (#553).
    payload = _entity_with("ex:ref", [{"@value": EX_URI + "thing", "@type": datatype}])
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        doc = ProvDocument.deserialize(content=payload, format="jsonld")
    assert [str(w.message) for w in caught] == [
        "the qualified name 'http://example.org/thing' of ex:ref does not resolve,"
        " because its prefix 'http' is not declared; it reads as ex:thing."
        " prov 3.3.0 will reject this (#553)"
    ]
    assert [w.filename for w in caught] == [__file__]
    (entity,) = doc.get_records()
    (value,) = [v for _, v in entity.extra_attributes]
    assert value == doc.valid_qualified_name("ex:thing")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        pytest.param("ex:ref", {"@id": EX_URI + "thing"}, id="node-reference"),
        pytest.param("type", EX_URI + "thing", id="id-typed-term"),
        pytest.param(
            "ex:ref", {"@value": "ex:thing", "@type": "xsd:QName"}, id="declared"
        ),
    ],
)
def test_deserialize_iri_value_does_not_warn(
    key: str, value: str | dict[str, str]
) -> None:
    # An @id, or a compactable bare full IRI under an @id-typed term, does not warn.
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        doc = ProvDocument.deserialize(
            content=_entity_with(key, [value]), format="jsonld"
        )
    (entity,) = doc.get_records()
    (read,) = [v for _, v in entity.extra_attributes]
    assert read == doc.valid_qualified_name("ex:thing")


def test_decode_jsonld_value_without_an_attribute_does_not_warn() -> None:
    value = {"@value": EX_URI + "thing", "@type": "xsd:QName"}
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        read = decode_jsonld_value(value, _new_doc(), "ex:ref")
    assert str(read) == "ex:thing"


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        pytest.param(
            "http://other.org/x", "its prefix 'http' is not declared", id="full-iri"
        ),
        pytest.param("zz:x", "its prefix 'zz' is not declared", id="undeclared"),
    ],
)
def test_deserialize_unresolvable_bare_string_under_id_typed_term_warns(
    text: str, reason: str
) -> None:
    # No declared namespace compacts it, so it is kept as a Literal (#516).
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        doc = ProvDocument.deserialize(
            content=_entity_with("type", [text]), format="jsonld"
        )
    assert [str(w.message) for w in caught] == [
        f"the qualified name {text!r} of prov:type does not resolve, because"
        f" {reason}; it is kept as a Literal. prov 3.3.0 will reject this (#516)"
    ]
    assert [w.filename for w in caught] == [__file__]
    (entity,) = doc.get_records()
    (value,) = [v for _, v in entity.extra_attributes]
    assert value == Literal(text, XSD_QNAME)


def test_deserialize_node_reference_outside_every_namespace_does_not_warn() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        ProvDocument.deserialize(
            content=_entity_with("ex:ref", [{"@id": "http://other.org/x"}]),
            format="jsonld",
        )
