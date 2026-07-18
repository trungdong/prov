"""Covers the 2.4.0 deprecation signpost for 3.0 (roadmap step 26) that is
still pending.

``ProvBundle.unified()``/``ProvDocument.unified()`` emit a ``FutureWarning``
about the PROV-CONSTRAINTS unification rework; the full narrative lives in
docs/upgrading-3.0.md.

The matching ``prov.dot``/``prov.graph`` ``DeprecationWarning`` signposts
(also covered here previously) came true in 3.0.0.dev0: those modules now
require the ``dot``/``graph`` extras and raise ``ModuleNotFoundError``
instead of warning -- see test_minimal_install.py.
"""

import pytest

from prov.model import ProvDocument


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
