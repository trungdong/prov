"""Shared qualified-name and namespace round-trip tests, run once per target
in ``SHARED_TARGETS``."""

from typing import TYPE_CHECKING

import pytest

from prov.constants import XSD_INT
from prov.identifier import Namespace, QualifiedName
from prov.model import (
    Literal,
    ProvDocument,
    ProvException,
    ProvExceptionInvalidQualifiedName,
)

from .conftest import Roundtrip, default_namespace

if TYPE_CHECKING:
    pass


def document_with_n_bundles_having_default_namespace(n: int) -> ProvDocument:
    prov_doc = ProvDocument()
    prov_doc.add_namespace("ex", "http://www.example.org/")
    for i in range(n):
        x = str(i + 1)
        bundle = prov_doc.bundle("ex:bundle/" + x)
        bundle.set_default_namespace("http://www.example.org/default/" + x)
        bundle.entity("e")
    return prov_doc


def test_namespace_inheritance(roundtrip: Roundtrip) -> None:
    prov_doc = ProvDocument()
    prov_doc.add_namespace("ex", "http://www.example.org/")
    bundle = prov_doc.bundle("ex:bundle")
    e1 = bundle.entity("ex:e1")
    assert e1.identifier is not None, "e1's identifier is None!"
    roundtrip(prov_doc)


def test_default_namespace_inheritance(roundtrip: Roundtrip) -> None:
    prov_doc = ProvDocument()
    prov_doc.set_default_namespace("http://www.example.org/")
    bundle = prov_doc.bundle("bundle")
    e1 = bundle.entity("e1")
    assert e1.identifier is not None, "e1's identifier is None!"
    roundtrip(prov_doc)


def _flat_names(flat: ProvDocument) -> list[str]:
    return [str(record.identifier) for record in flat.get_records()]


def test_flattening_1_bundle_with_default_namespace(roundtrip: Roundtrip) -> None:
    flat = document_with_n_bundles_having_default_namespace(1).flattened()
    assert _flat_names(flat) == ["dn:e"]
    roundtrip(flat)


def test_flattening_2_bundles_with_default_namespace(roundtrip: Roundtrip) -> None:
    flat = document_with_n_bundles_having_default_namespace(2).flattened()
    assert _flat_names(flat) == ["dn:e", "dn_1:e"]
    roundtrip(flat)


def test_flattening_3_bundles_with_default_namespace(roundtrip: Roundtrip) -> None:
    flat = document_with_n_bundles_having_default_namespace(3).flattened()
    assert _flat_names(flat) == ["dn:e", "dn_1:e", "dn_2:e"]
    roundtrip(flat)


def test_flattening_1_bundle_with_default_namespaces(roundtrip: Roundtrip) -> None:
    prov_doc = document_with_n_bundles_having_default_namespace(1)
    prov_doc.set_default_namespace("http://www.example.org/default/0")
    flat = prov_doc.flattened()
    assert _flat_names(flat) == ["dn:e"]
    roundtrip(flat)


def test_flattening_2_bundle_with_default_namespaces(roundtrip: Roundtrip) -> None:
    prov_doc = document_with_n_bundles_having_default_namespace(2)
    prov_doc.set_default_namespace("http://www.example.org/default/0")
    flat = prov_doc.flattened()
    assert _flat_names(flat) == ["dn:e", "dn_1:e"]
    roundtrip(flat)


def test_provn_cannot_write_an_empty_local_part_without_a_prefix() -> None:
    qname = QualifiedName(default_namespace("http://d/"), "")
    with pytest.raises(ProvException, match="prefix"):
        qname.provn_bare_representation()
    assert Namespace("ex", "http://e/")[""].provn_bare_representation() == "ex:"


# A JSON reader splits a name at its first ":", so a default-namespace local
# part containing one is written with a prefix bound to the namespace IRI
# (#517), and a prefix named "default", the PROV-JSON key for the default
# namespace, is renamed (#518).
DEFAULT_NS = default_namespace("http://d.example/")
DEFAULT_PREFIX_NS = Namespace("default", "http://u.example/")


def document_with_default_namespace() -> ProvDocument:
    prov_doc = ProvDocument()
    prov_doc.set_default_namespace(DEFAULT_NS.uri)
    return prov_doc


def test_default_namespace_colon_local_part_as_record_identifier(
    roundtrip: Roundtrip,
) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.entity(DEFAULT_NS["a:b"])
    roundtrip(prov_doc)


def test_default_namespace_colon_local_part_as_attribute_name(
    roundtrip: Roundtrip,
) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.entity(DEFAULT_NS["e"], {DEFAULT_NS["a:b"]: "v"})
    roundtrip(prov_doc)


def test_default_namespace_colon_local_part_as_formal_value(
    roundtrip: Roundtrip,
) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.wasGeneratedBy(DEFAULT_NS["e"], DEFAULT_NS["a:b"])
    roundtrip(prov_doc)


def test_default_namespace_colon_local_part_as_attribute_value(
    roundtrip: Roundtrip,
) -> None:
    # PROV-JSONLD writes a prov:type value as a bare string and any other
    # attribute's value as a value object
    prov_doc = document_with_default_namespace()
    prov_doc.entity(
        DEFAULT_NS["e"],
        {"prov:type": DEFAULT_NS["a:b"], DEFAULT_NS["attr"]: DEFAULT_NS["c:d"]},
    )
    roundtrip(prov_doc)


@pytest.mark.parametrize(
    "fmt",
    [
        "model",
        "json",
        pytest.param(
            "xml",
            marks=pytest.mark.xfail(
                strict=True,
                reason='#570: PROV-XML writes the datatype as xsi:type=":a:b", '
                'which reads back with the local part ":a:b"',
            ),
        ),
        "rdf",
        "jsonld",
        pytest.param(
            "provn",
            marks=pytest.mark.xfail(
                strict=True,
                reason="#571: PROV-N writes the datatype unescaped (%% a:b), which "
                "reads back as the undeclared prefix a",
            ),
        ),
    ],
)
def test_default_namespace_colon_local_part_as_literal_datatype(
    roundtrip: Roundtrip,
) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.entity(
        DEFAULT_NS["e"], {DEFAULT_NS["attr"]: Literal("1", DEFAULT_NS["a:b"])}
    )
    roundtrip(prov_doc)


def test_default_namespace_colon_local_part_as_bundle_identifier(
    roundtrip: Roundtrip,
) -> None:
    prov_doc = document_with_default_namespace()
    bundle = prov_doc.bundle(DEFAULT_NS["a:b"])
    bundle.entity(DEFAULT_NS["c:d"])
    roundtrip(prov_doc)


@pytest.mark.parametrize(
    "fmt",
    [
        "model",
        "json",
        "xml",
        "rdf",
        "jsonld",
        "provn",
    ],
)
def test_default_namespace_colon_local_part_in_a_bundle_default_namespace(
    roundtrip: Roundtrip,
) -> None:
    # the bundle is named under a prefix, since a bundle named in the
    # document's default cannot then declare a default of its own
    other_ns = default_namespace("http://other.example/")
    prov_doc = document_with_default_namespace()
    prov_doc.entity(DEFAULT_NS["a:b"])
    named = prov_doc.add_namespace("ex", "http://ex.example/")
    bundle = prov_doc.bundle(named["b:c"])
    bundle.set_default_namespace(other_ns.uri)
    bundle.entity(other_ns["c:d"])
    roundtrip(prov_doc)


def test_default_namespace_colon_local_part_reuses_a_prefix_for_the_iri(
    roundtrip: Roundtrip,
) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.add_namespace("d", DEFAULT_NS.uri)
    prov_doc.entity(DEFAULT_NS["a:b"])
    roundtrip(prov_doc)


def test_prefix_named_default(roundtrip: Roundtrip) -> None:
    prov_doc = ProvDocument()
    prov_doc.add_namespace(DEFAULT_PREFIX_NS)
    prov_doc.entity(
        DEFAULT_PREFIX_NS["e"],
        {
            DEFAULT_PREFIX_NS["attr"]: DEFAULT_PREFIX_NS["v"],
            "prov:type": Literal("1", DEFAULT_PREFIX_NS["dt"]),
        },
    )
    prov_doc.wasGeneratedBy(DEFAULT_PREFIX_NS["e"], DEFAULT_PREFIX_NS["a"])
    roundtrip(prov_doc)


def test_prefix_named_default_in_bundles(roundtrip: Roundtrip) -> None:
    prov_doc = ProvDocument()
    prov_doc.add_namespace(DEFAULT_PREFIX_NS)
    bundle = prov_doc.bundle(DEFAULT_PREFIX_NS["b1"])
    bundle.entity(DEFAULT_PREFIX_NS["e"])
    # a bundle's own "default" prefix, beside the document's; its identifier
    # avoids that prefix, which a reader would resolve in the bundle (#573)
    prov_doc.add_namespace("ex", "http://ex.example/")
    bundle = prov_doc.bundle("ex:b2")
    bundle.add_namespace("default", "http://w.example/")
    bundle.entity("default:f")
    bundle.entity(DEFAULT_PREFIX_NS["g"])
    roundtrip(prov_doc)


def test_generated_prefixes_avoid_prefixes_in_use(roundtrip: Roundtrip) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.add_namespace(DEFAULT_PREFIX_NS)
    default_1 = prov_doc.add_namespace("default_1", "http://x.example/")
    other = prov_doc.add_namespace("other", "http://other.example/")
    prov_doc.entity(DEFAULT_NS["a:b"], {DEFAULT_PREFIX_NS["attr"]: other["v"]})
    prov_doc.entity(default_1["e"])
    roundtrip(prov_doc)


def test_generated_prefixes_avoid_prefixes_declared_in_a_bundle(
    roundtrip: Roundtrip,
) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.add_namespace(DEFAULT_PREFIX_NS)
    prov_doc.entity(DEFAULT_PREFIX_NS["e"])
    bundle = prov_doc.bundle(DEFAULT_NS["b:c"])
    bundle.add_namespace("other", "http://other.example/")
    bundle.add_namespace("default_1", "http://x.example/")
    bundle.entity("other:f", {"default_1:attr": DEFAULT_PREFIX_NS["v"]})
    bundle.entity(DEFAULT_NS["c:d"])
    roundtrip(prov_doc)


def test_literal_datatype_registers_its_namespace(roundtrip: Roundtrip) -> None:
    # #615: a datatype in a namespace nothing declared is declared by every
    # writer, because asserting the literal registers it.
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e", {"ex:a": Literal("1", Namespace("zz", "http://zz.org/")["t"])})
    assert {ns.prefix for ns in doc.get_registered_namespaces()} == {"ex", "zz"}
    roundtrip(doc)


def test_literal_datatype_follows_a_renamed_prefix(roundtrip: Roundtrip) -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.add_namespace("zz", "http://taken.org/")
    record = doc.entity(
        "ex:e", {"ex:a": Literal("1", Namespace("zz", "http://zz.org/")["t"])}
    )
    (value,) = record.get_attribute("ex:a")
    assert isinstance(value, Literal)
    assert value.datatype is not None and value.datatype.namespace.prefix == "zz_1"
    roundtrip(doc)


def test_literal_in_scope_returns_built_in_datatypes_unchanged() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    record = doc.entity("ex:e")
    typed = Literal("1", XSD_INT)
    assert record._literal_in_scope(typed, XSD_INT) is typed


def test_literal_datatype_in_a_foreign_default_is_rejected() -> None:
    doc = ProvDocument()
    doc.set_default_namespace("http://d.org/")
    datatype = default_namespace("http://other.org/")["t"]
    with pytest.raises(ProvExceptionInvalidQualifiedName) as caught:
        doc.entity("e", {"a": Literal("1", datatype)})
    assert caught.value.detail == (
        "the name 't' is in the default namespace http://other.org/, "
        "which is not the default namespace in scope; declare a prefix for it"
    )


def test_identifier_equal_to_the_default_namespace_iri_is_rejected() -> None:
    # #473: the name has no spelling in the default namespace, and the model
    # mints no prefix for it.
    doc = document_with_default_namespace()
    default = doc.get_default_namespace()
    assert default is not None
    for identifier in (DEFAULT_NS.uri, default[""]):
        with pytest.raises(ProvExceptionInvalidQualifiedName) as caught:
            doc.entity(identifier)
        assert caught.value.detail == (
            f"the IRI {DEFAULT_NS.uri} is the default namespace and has no "
            "qualified-name form; declare a prefix for it"
        )
    assert list(doc.get_registered_namespaces()) == []


def test_identifier_equal_to_a_namespace_iri_under_a_prefix_is_that_prefix() -> None:
    # Production [52] allows an empty local part after a prefix.
    doc = document_with_default_namespace()
    ex = doc.add_namespace("ex", DEFAULT_NS.uri)
    assert doc.entity(DEFAULT_NS.uri).identifier == ex[""]
    assert str(doc.entity(DEFAULT_NS.uri).identifier) == "ex:"


def test_a_bare_empty_local_name_still_has_no_provn_spelling() -> None:
    with pytest.raises(ProvException, match="empty local part"):
        default_namespace(DEFAULT_NS.uri)[""].provn_representation()


def test_identifier_equal_to_the_default_in_a_bundle_that_rebinds_the_prefix() -> None:
    doc = ProvDocument()
    doc.set_default_namespace("http://d/")
    doc.add_namespace("ex", "http://d/")
    bundle = doc.bundle(doc.add_namespace("nm", "http://n/")["b3"])
    bundle.add_namespace("ex", "http://x/")
    with pytest.raises(ProvExceptionInvalidQualifiedName, match="declare a prefix"):
        bundle.entity(default_namespace("http://d/")[""])
