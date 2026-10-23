"""Shared qualified-name and namespace round-trip tests, run once per target
in ``SHARED_TARGETS``."""

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from prov.constants import XSD_INT
from prov.identifier import Namespace, QualifiedName
from prov.model import Literal, ProvBundle, ProvDocument, ProvException

from . import examples
from .attribute_values import document as attribute_values_document
from .conftest import Roundtrip
from .test_provn_corpus import (
    CORPUS,
    EXCLUDED_PROVTOOLBOX_DOCUMENTS,
    EXCLUDED_SPEC_EXAMPLES,
)

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet


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


def test_flattening_1_bundle_with_default_namespace(roundtrip: Roundtrip) -> None:
    prov_doc = document_with_n_bundles_having_default_namespace(1)
    roundtrip(prov_doc.flattened())


def test_flattening_2_bundles_with_default_namespace(roundtrip: Roundtrip) -> None:
    prov_doc = document_with_n_bundles_having_default_namespace(2)
    roundtrip(prov_doc.flattened())


def test_flattening_3_bundles_with_default_namespace(roundtrip: Roundtrip) -> None:
    prov_doc = document_with_n_bundles_having_default_namespace(3)
    roundtrip(prov_doc.flattened())


def test_flattening_1_bundle_with_default_namespaces(roundtrip: Roundtrip) -> None:
    prov_doc = document_with_n_bundles_having_default_namespace(1)
    prov_doc.set_default_namespace("http://www.example.org/default/0")
    roundtrip(prov_doc.flattened())


def test_flattening_2_bundle_with_default_namespaces(roundtrip: Roundtrip) -> None:
    prov_doc = document_with_n_bundles_having_default_namespace(2)
    prov_doc.set_default_namespace("http://www.example.org/default/0")
    roundtrip(prov_doc.flattened())


def test_provn_cannot_write_an_empty_local_part_without_a_prefix() -> None:
    qname = QualifiedName(Namespace("", "http://d/"), "")
    with pytest.raises(ProvException, match="prefix"):
        qname.provn_bare_representation()
    assert Namespace("ex", "http://e/")[""].provn_bare_representation() == "ex:"


# A JSON reader splits a name at its first ":", so a default-namespace local
# part containing one is written with a prefix bound to the namespace IRI
# (#517), and a prefix named "default", the PROV-JSON key for the default
# namespace, is renamed (#518).
DEFAULT_NS = Namespace("", "http://d.example/")
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
        pytest.param(
            "xml",
            marks=pytest.mark.xfail(
                strict=True,
                reason="#572: PROV-XML does not write a bundle's own default "
                "namespace, so the bundle's names read back in the document's",
            ),
        ),
        "rdf",
        "jsonld",
        "provn",
    ],
)
def test_default_namespace_colon_local_part_in_a_bundle_default_namespace(
    roundtrip: Roundtrip,
) -> None:
    # the bundle identifier, in the document's default namespace, takes the
    # document's prefix for it
    other_ns = Namespace("", "http://other.example/")
    prov_doc = document_with_default_namespace()
    prov_doc.entity(DEFAULT_NS["a:b"])
    bundle = prov_doc.bundle(DEFAULT_NS["b:c"])
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
    dn = prov_doc.add_namespace("dn", "http://dn.example/")
    prov_doc.entity(DEFAULT_NS["a:b"], {DEFAULT_PREFIX_NS["attr"]: dn["v"]})
    prov_doc.entity(default_1["e"])
    roundtrip(prov_doc)


def test_generated_prefixes_avoid_prefixes_declared_in_a_bundle(
    roundtrip: Roundtrip,
) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.add_namespace(DEFAULT_PREFIX_NS)
    prov_doc.entity(DEFAULT_PREFIX_NS["e"])
    bundle = prov_doc.bundle(DEFAULT_NS["b:c"])
    bundle.add_namespace("dn", "http://dn.example/")
    bundle.add_namespace("default_1", "http://x.example/")
    bundle.entity("dn:f", {"default_1:attr": DEFAULT_PREFIX_NS["v"]})
    bundle.entity(DEFAULT_NS["c:d"])
    roundtrip(prov_doc)


def _held_names(bundle: ProvBundle) -> Iterator[QualifiedName]:
    if bundle.identifier is not None:
        yield bundle.identifier
    for record in bundle.get_records():
        if record.identifier is not None:
            yield record.identifier
        for name, value in record.attributes:
            yield name
            if isinstance(value, QualifiedName):
                yield value
            elif isinstance(value, Literal) and value.datatype is not None:
                yield value.datatype


def _provn_corpus_files() -> list[Path]:
    excluded = {*EXCLUDED_SPEC_EXAMPLES, *EXCLUDED_PROVTOOLBOX_DOCUMENTS}
    return sorted(path for path in CORPUS.rglob("*.provn") if path.name not in excluded)


def _corpus_sources() -> "Iterator[ParameterSet]":
    for name, build in examples.tests:
        yield pytest.param(build, id=name)
    yield pytest.param(attribute_values_document, id="attribute_values")
    for path in _provn_corpus_files():
        yield pytest.param(path, id=path.name)


@pytest.mark.parametrize("source", list(_corpus_sources()))
def test_lookup_agrees_with_valid_qualified_name(
    source: Path | Callable[[], ProvDocument],
) -> None:
    document = (
        ProvDocument.deserialize(str(source), format="provn")
        if isinstance(source, Path)
        else source()
    )
    # Spec 3, 3.4: the reader's one-walk resolution and the model's resolver
    # give the same object for every name a document holds.
    scopes: list[ProvBundle] = [document, *document.bundles]
    for bundle in scopes:
        for name in _held_names(bundle):
            assert bundle._lookup(name.namespace.prefix, name.localpart) is name
            if not name.namespace.prefix and ":" in name.localpart:
                # A bare local part with a colon has no string form the
                # resolver splits correctly; the lookup half covers it.
                continue
            resolved = bundle.valid_qualified_name(str(name))
            assert resolved == name
            assert resolved is not None and resolved.namespace is name.namespace


def test_lookup_corners() -> None:
    doc = ProvDocument()
    doc.set_default_namespace("http://d.org/")
    doc.add_namespace("ex", "http://example.org/")
    bundle = doc.bundle("ex:b")
    assert doc._lookup("", "") is None
    assert doc._lookup("_", "x") is None
    doc.add_namespace("_", "http://blank.org/")
    assert doc._lookup("_", "x") is None
    assert doc._lookup("zz", "x") is None
    default = doc.get_default_namespace()
    assert default is not None
    assert doc._lookup("", "a:b") == default["a:b"]
    assert bundle._lookup("ex", "z") is doc.valid_qualified_name("ex:z")
    assert list(bundle.get_registered_namespaces()) == []


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
    tagged = Literal("chat", langtag="fr")
    typed = Literal("1", XSD_INT)
    # The caller never passes a langtag literal; this pins the direct call.
    assert record._literal_in_scope(tagged) is tagged
    assert record._literal_in_scope(typed) is typed


def test_literal_datatype_in_a_foreign_default_takes_the_dn_prefix() -> None:
    doc = ProvDocument()
    doc.set_default_namespace("http://d.org/")
    record = doc.entity(
        "e", {"a": Literal("1", Namespace("", "http://other.org/")["t"])}
    )
    (value,) = record.get_attribute("a")
    assert isinstance(value, Literal) and value.datatype is not None
    assert value.datatype.namespace.prefix == "dn"
    assert value.datatype.uri == "http://other.org/t"
    assert "dn" in {ns.prefix for ns in doc.get_registered_namespaces()}
    content = doc.serialize(format="provn")
    assert ProvDocument.deserialize(content=content, format="provn") == doc


@pytest.mark.parametrize(
    "fmt",
    [
        "model",
        "json",
        "xml",
        "jsonld",
        "provn",
        pytest.param(
            "rdf",
            marks=pytest.mark.xfail(
                strict=True,
                reason="spec 3 section 6.3: the PROV-O reader registers the writer's "
                "default binding as a prefix-less namespace, so dn is renamed away on "
                "read; fixed with the third-party reader changes",
            ),
        ),
    ],
)
def test_identifier_equal_to_the_default_namespace_iri(roundtrip: Roundtrip) -> None:
    # #473: the name has no PROV-N spelling in the default namespace, so the
    # model gives it a prefix bound to the same IRI at assertion.
    doc = document_with_default_namespace()
    for identifier in (DEFAULT_NS.uri, DEFAULT_NS[""]):
        record = doc.entity(identifier)
        assert record.identifier.namespace.prefix == "dn"
        assert record.identifier.uri == DEFAULT_NS.uri
    assert "dn" in {ns.prefix for ns in doc.get_registered_namespaces()}
    reloaded = roundtrip(doc)
    for read_back in reloaded.get_records():
        if read_back.identifier is not None:
            assert read_back.identifier.namespace.prefix
    reloaded.get_provn()


def test_identifier_equal_to_the_default_namespace_iri_reuses_a_prefix() -> None:
    doc = document_with_default_namespace()
    doc.add_namespace("ex", DEFAULT_NS.uri)
    assert str(doc.entity(DEFAULT_NS.uri).identifier) == "ex:"
    assert str(doc.entity(DEFAULT_NS[""]).identifier) == "ex:"
    assert "dn" not in {ns.prefix for ns in doc.get_registered_namespaces()}


def test_identifier_equal_to_the_default_namespace_iri_avoids_a_taken_dn() -> None:
    doc = document_with_default_namespace()
    doc.add_namespace("dn", "http://dn.example/")
    assert doc.entity(DEFAULT_NS.uri).identifier.namespace.prefix == "dn_1"


def test_a_bare_empty_local_name_still_has_no_provn_spelling() -> None:
    with pytest.raises(ProvException, match="empty local part"):
        Namespace("", DEFAULT_NS.uri)[""].provn_representation()
