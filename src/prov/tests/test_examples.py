"""Pytest-native shared example round-trip test.

Migrated from the ``TestExamplesBase`` mixin (in ``test_model.py``): a single
function loops over the canonical ``examples.tests`` documents and round-trips
each, run once per target in ``SHARED_TARGETS``. It is kept as one looping node
per target (not expanded per example) to preserve the collected-count parity
baseline; per-example isolation is a deferred improvement. The legacy mixin
remains for the not-yet-migrated ``test_dot.py``.
"""

from prov.tests import examples


def test_all_examples(roundtrip, fmt):
    for name, build in examples.tests:
        if name == "datatypes" and fmt == "rdf":
            # The "datatypes" example packs a mixed-XSD-datatype attribute set
            # onto one entity, the same shape that loses fidelity across an RDF
            # round trip as issue #218 (see test_attributes.py's
            # RDF_DATATYPE_XFAIL); the pre-migration test_rdf.py loop skipped
            # this example outright (`if name in ["datatypes"]: continue`).
            # Preserved here, scoped to the rdf target only.
            continue
        roundtrip(build())
