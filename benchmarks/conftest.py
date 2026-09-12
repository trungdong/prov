"""Shared document generator for the benchmark suite.

``PROV_BENCH_N`` sets the record count (default 10000, which keeps the CI
job under three minutes; use 100000 for local profiling).
"""

from __future__ import annotations

import datetime
import os

import pytest

from prov.model import ProvDocument

N = int(os.environ.get("PROV_BENCH_N", "10000"))


def build_document(n: int = N) -> ProvDocument:
    """Return a document with roughly ``n`` records in a realistic mix.

    Every fifth block of records lands in one of five named bundles, so
    bundle handling is exercised without dominating the numbers.
    """
    doc = ProvDocument()
    doc.add_namespace("ex", "http://example.org/")
    doc.add_namespace("dc", "http://purl.org/dc/terms/")
    bundles = [doc.bundle(f"ex:bundle{i}") for i in range(5)]
    base_time = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    per_block = 8  # records created per loop iteration
    for i in range(max(1, n // per_block)):
        target = bundles[i % 5] if i % 5 == 0 else doc
        e_in = target.entity(f"ex:input{i}", {"dc:title": f"Input {i}", "ex:size": i})
        e_out = target.entity(
            f"ex:output{i}", {"dc:title": f"Output {i}", "ex:score": i / 7.0}
        )
        act = target.activity(
            f"ex:run{i}",
            base_time + datetime.timedelta(seconds=i),
            base_time + datetime.timedelta(seconds=i + 1),
            {"ex:status": "ok"},
        )
        agent = target.agent(f"ex:agent{i % 50}", {"prov:type": "prov:SoftwareAgent"})
        target.used(act, e_in, base_time + datetime.timedelta(seconds=i))
        target.wasGeneratedBy(e_out, act, base_time + datetime.timedelta(seconds=i + 1))
        target.wasAssociatedWith(act, agent)
        target.wasDerivedFrom(e_out, e_in, act)
    return doc


@pytest.fixture(scope="session")
def document() -> ProvDocument:
    return build_document()


def serialized(doc: ProvDocument, fmt: str) -> str | bytes:
    return doc.serialize(format=fmt)
