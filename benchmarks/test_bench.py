"""Benchmarks for the operations the 3.2.0 performance track measures.

Run with ``uv run pytest benchmarks/ --benchmark-json=<file>`` and compare
against ``benchmarks/baseline.json`` with ``benchmarks/compare.py``.
"""

from __future__ import annotations

import pytest

from prov.model import ProvDocument

from .conftest import N, build_document, serialized

FORMATS = ("json", "xml", "rdf", "provn", "jsonld")


def test_construct(benchmark):
    benchmark(build_document, N)


@pytest.mark.parametrize("fmt", FORMATS)
def test_serialize(benchmark, document, fmt):
    benchmark(serialized, document, fmt)


@pytest.mark.parametrize("fmt", FORMATS)
def test_deserialize(benchmark, document, fmt):
    content = serialized(document, fmt)
    benchmark(ProvDocument.deserialize, content=content, format=fmt)


def test_unified(benchmark, document):
    benchmark(document.unified)


def test_prov_to_graph(benchmark, document):
    from prov.graph import prov_to_graph

    benchmark(prov_to_graph, document)


def test_equality(benchmark, document):
    other = build_document(N)
    benchmark(lambda: document == other)
