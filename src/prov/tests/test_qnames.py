"""Pytest-native shared qualified-name / namespace round-trip tests.

Migrated from the ``TestQualifiedNamesBase`` mixin (``qnames.py``): each test
method becomes a module-level function taking the ``roundtrip`` fixture, run
once per target in ``SHARED_TARGETS``. The legacy mixin remains for the
not-yet-migrated xml/rdf/dot modules.
"""

from prov.model import ProvDocument


def document_with_n_bundles_having_default_namespace(n):
    prov_doc = ProvDocument()
    prov_doc.add_namespace("ex", "http://www.example.org/")
    for i in range(n):
        x = str(i + 1)
        bundle = prov_doc.bundle("ex:bundle/" + x)
        bundle.set_default_namespace("http://www.example.org/default/" + x)
        bundle.entity("e")
    return prov_doc


def test_namespace_inheritance(roundtrip):
    prov_doc = ProvDocument()
    prov_doc.add_namespace("ex", "http://www.example.org/")
    bundle = prov_doc.bundle("ex:bundle")
    e1 = bundle.entity("ex:e1")
    assert e1.identifier is not None, "e1's identifier is None!"
    roundtrip(prov_doc)


def test_default_namespace_inheritance(roundtrip):
    prov_doc = ProvDocument()
    prov_doc.set_default_namespace("http://www.example.org/")
    bundle = prov_doc.bundle("bundle")
    e1 = bundle.entity("e1")
    assert e1.identifier is not None, "e1's identifier is None!"
    roundtrip(prov_doc)


def test_flattening_1_bundle_with_default_namespace(roundtrip):
    prov_doc = document_with_n_bundles_having_default_namespace(1)
    roundtrip(prov_doc.flattened())


def test_flattening_2_bundles_with_default_namespace(roundtrip):
    prov_doc = document_with_n_bundles_having_default_namespace(2)
    roundtrip(prov_doc.flattened())


def test_flattening_3_bundles_with_default_namespace(roundtrip):
    prov_doc = document_with_n_bundles_having_default_namespace(3)
    roundtrip(prov_doc.flattened())


def test_flattening_1_bundle_with_default_namespaces(roundtrip):
    prov_doc = document_with_n_bundles_having_default_namespace(1)
    prov_doc.set_default_namespace("http://www.example.org/default/0")
    roundtrip(prov_doc.flattened())


def test_flattening_2_bundle_with_default_namespaces(roundtrip):
    prov_doc = document_with_n_bundles_having_default_namespace(2)
    prov_doc.set_default_namespace("http://www.example.org/default/0")
    roundtrip(prov_doc.flattened())
