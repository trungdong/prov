"""Pytest-native shared example round-trip test.

Migrated from the ``TestExamplesBase`` mixin (in ``test_model.py``): a single
function loops over the canonical ``examples.tests`` documents and round-trips
each, run once per target in ``SHARED_TARGETS``. It is kept as one looping node
per target (not expanded per example) to preserve the collected-count parity
baseline; per-example isolation is a deferred improvement. The legacy mixin
remains for the not-yet-migrated xml/rdf/dot modules.
"""

from prov.tests import examples


def test_all_examples(roundtrip):
    for _name, build in examples.tests:
        roundtrip(build())
