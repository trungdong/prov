"""Pytest-native shared qualified-name / namespace round-trip tests.

Migrated from the ``TestQualifiedNamesBase`` mixin (``qnames.py``): each test
method becomes a module-level function taking the ``roundtrip`` fixture, run
once per target in ``SHARED_TARGETS``. The legacy mixin remains for the
not-yet-migrated xml/rdf/dot modules.
"""

import pytest

from prov.identifier import Namespace, QualifiedName
from prov.model import Literal, ProvDocument, ProvException


def document_with_n_bundles_having_default_namespace(n):
    prov_doc = ProvDocument()
    prov_doc.add_namespace("ex", "http://www.example.org/")
    for i in range(n):
        x = str(i + 1)
        bundle = prov_doc.bundle("ex:bundle/" + x)
        bundle.set_default_namespace("http://www.example.org/default/" + x)
        bundle.entity("e")
    return prov_doc


def test_namespace_inheritance(roundtrip) -> None:
    prov_doc = ProvDocument()
    prov_doc.add_namespace("ex", "http://www.example.org/")
    bundle = prov_doc.bundle("ex:bundle")
    e1 = bundle.entity("ex:e1")
    assert e1.identifier is not None, "e1's identifier is None!"
    roundtrip(prov_doc)


def test_default_namespace_inheritance(roundtrip) -> None:
    prov_doc = ProvDocument()
    prov_doc.set_default_namespace("http://www.example.org/")
    bundle = prov_doc.bundle("bundle")
    e1 = bundle.entity("e1")
    assert e1.identifier is not None, "e1's identifier is None!"
    roundtrip(prov_doc)


def test_flattening_1_bundle_with_default_namespace(roundtrip) -> None:
    prov_doc = document_with_n_bundles_having_default_namespace(1)
    roundtrip(prov_doc.flattened())


def test_flattening_2_bundles_with_default_namespace(roundtrip) -> None:
    prov_doc = document_with_n_bundles_having_default_namespace(2)
    roundtrip(prov_doc.flattened())


def test_flattening_3_bundles_with_default_namespace(roundtrip) -> None:
    prov_doc = document_with_n_bundles_having_default_namespace(3)
    roundtrip(prov_doc.flattened())


def test_flattening_1_bundle_with_default_namespaces(roundtrip) -> None:
    prov_doc = document_with_n_bundles_having_default_namespace(1)
    prov_doc.set_default_namespace("http://www.example.org/default/0")
    roundtrip(prov_doc.flattened())


def test_flattening_2_bundle_with_default_namespaces(roundtrip) -> None:
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


def test_default_namespace_colon_local_part_as_record_identifier(roundtrip) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.entity(DEFAULT_NS["a:b"])
    roundtrip(prov_doc)


def test_default_namespace_colon_local_part_as_attribute_name(roundtrip) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.entity(DEFAULT_NS["e"], {DEFAULT_NS["a:b"]: "v"})
    roundtrip(prov_doc)


def test_default_namespace_colon_local_part_as_formal_value(roundtrip) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.wasGeneratedBy(DEFAULT_NS["e"], DEFAULT_NS["a:b"])
    roundtrip(prov_doc)


def test_default_namespace_colon_local_part_as_attribute_value(roundtrip) -> None:
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
def test_default_namespace_colon_local_part_as_literal_datatype(roundtrip) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.entity(
        DEFAULT_NS["e"], {DEFAULT_NS["attr"]: Literal("1", DEFAULT_NS["a:b"])}
    )
    roundtrip(prov_doc)


def test_default_namespace_colon_local_part_as_bundle_identifier(roundtrip) -> None:
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
    roundtrip,
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
    roundtrip,
) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.add_namespace("d", DEFAULT_NS.uri)
    prov_doc.entity(DEFAULT_NS["a:b"])
    roundtrip(prov_doc)


def test_prefix_named_default(roundtrip) -> None:
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


def test_prefix_named_default_in_bundles(roundtrip) -> None:
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


def test_generated_prefixes_avoid_prefixes_in_use(roundtrip) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.add_namespace(DEFAULT_PREFIX_NS)
    default_1 = prov_doc.add_namespace("default_1", "http://x.example/")
    dn = prov_doc.add_namespace("dn", "http://dn.example/")
    prov_doc.entity(DEFAULT_NS["a:b"], {DEFAULT_PREFIX_NS["attr"]: dn["v"]})
    prov_doc.entity(default_1["e"])
    roundtrip(prov_doc)


def test_generated_prefixes_avoid_prefixes_declared_in_a_bundle(roundtrip) -> None:
    prov_doc = document_with_default_namespace()
    prov_doc.add_namespace(DEFAULT_PREFIX_NS)
    prov_doc.entity(DEFAULT_PREFIX_NS["e"])
    bundle = prov_doc.bundle(DEFAULT_NS["b:c"])
    bundle.add_namespace("dn", "http://dn.example/")
    bundle.add_namespace("default_1", "http://x.example/")
    bundle.entity("dn:f", {"default_1:attr": DEFAULT_PREFIX_NS["v"]})
    bundle.entity(DEFAULT_NS["c:d"])
    roundtrip(prov_doc)
