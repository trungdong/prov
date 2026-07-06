"""Covers the 2.4.0 deprecation signposts for 3.0 (roadmap step 26).

``prov.dot`` and ``prov.graph`` emit a module-level ``DeprecationWarning``
pointing at the future ``prov[dot]``/``prov[graph]`` extras, and
``ProvBundle.unified()``/``ProvDocument.unified()`` emit a ``FutureWarning``
about the PROV-CONSTRAINTS unification rework. The full narrative for both
lives in docs/upgrading-3.0.md.

Module-level warnings only fire once, at import time, so a test that isn't
the first to import ``prov.dot``/``prov.graph`` (both are imported by other
test modules in this suite) must ``importlib.reload()`` the module to
observe the warning again.
"""

import importlib

import pytest

import prov.dot
import prov.graph
from prov.model import ProvDocument


def test_import_dot_warns_deprecation():
    with pytest.warns(DeprecationWarning, match=r"prov\[dot\]"):
        importlib.reload(prov.dot)


def test_import_graph_warns_deprecation():
    with pytest.warns(DeprecationWarning, match=r"prov\[graph\]"):
        importlib.reload(prov.graph)


def test_bundle_unified_warns_future():
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1")
    bundle = doc.bundle("ex:b1")
    bundle.entity("ex:e2")

    with pytest.warns(FutureWarning, match="PROV-CONSTRAINTS"):
        bundle.unified()


def test_document_unified_warns_future():
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.entity("ex:e1")

    with pytest.warns(FutureWarning, match="PROV-CONSTRAINTS"):
        doc.unified()
