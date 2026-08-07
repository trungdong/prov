"""Pytest-native shared example round-trip test.

Migrated from the ``TestExamplesBase`` mixin (in ``test_model.py``): a single
function loops over the canonical ``examples.tests`` documents and round-trips
each, run once per target in ``SHARED_TARGETS``. It is kept as one looping node
per target (not expanded per example) to preserve the collected-count parity
baseline; per-example isolation is a deferred improvement. The legacy mixin
remains for the not-yet-migrated ``test_dot.py``.
"""

import pytest

from prov.serializers.provjsonld import ProvJSONLDException
from prov.tests import examples

from .conftest import contains_mention


def test_all_examples(roundtrip, fmt):
    for _name, build in examples.tests:
        document = build()
        # PROV-JSONLD defines no Mention term (permanent, documented
        # limitation, like the test_mention_1/test_mention_2 cases in
        # test_statements.py — see docs/reference/conformance.md), so a
        # mention-bearing example is expected to raise rather than round-trip.
        if fmt == "jsonld" and contains_mention(document):
            with pytest.raises(ProvJSONLDException, match=r"[Mm]ention"):
                roundtrip(document)
            continue
        roundtrip(document)
