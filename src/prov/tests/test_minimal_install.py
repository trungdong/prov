"""Degradation behaviour when optional extras are missing.

Run by the ``minimal-install`` CI job (which syncs without the rdf/xml
extras). Under the normal matrix (extras installed) the skipif-guarded tests
are skipped and the availability test asserts all four formats register.
"""

import importlib.util

import pytest

import prov.serializers
from prov.model import ProvDocument

HAS_RDFLIB = importlib.util.find_spec("rdflib") is not None
HAS_LXML = importlib.util.find_spec("lxml") is not None


def test_core_import_and_json_roundtrip() -> None:
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1")
    reloaded = ProvDocument.deserialize(content=doc.serialize(format="json"))
    assert reloaded == doc


@pytest.mark.skipif(HAS_RDFLIB, reason="only meaningful without rdflib")
def test_rdf_unavailable_raises_informative_error() -> None:
    with pytest.raises(prov.serializers.DoNotExist, match=r"prov\[rdf\]"):
        prov.serializers.get("rdf")


@pytest.mark.skipif(HAS_LXML, reason="only meaningful without lxml")
def test_xml_unavailable_raises_informative_error() -> None:
    with pytest.raises(prov.serializers.DoNotExist, match=r"prov\[xml\]"):
        prov.serializers.get("xml")


@pytest.mark.skipif(
    not (HAS_RDFLIB and HAS_LXML), reason="only meaningful with both extras"
)
def test_all_formats_available_with_extras() -> None:
    for fmt in ("json", "provn", "rdf", "xml"):
        assert prov.serializers.get(fmt) is not None
