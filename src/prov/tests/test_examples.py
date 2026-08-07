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

# "Bundle2" is the one canonical example using mentionOf. PROV-JSONLD defines
# no Mention term (permanent, documented limitation, like the test_mention_1/
# test_mention_2 cases in test_statements.py — see
# docs/reference/conformance.md), so under the jsonld target it is expected to
# raise rather than round-trip.
_JSONLD_UNREPRESENTABLE = {"Bundle2"}


def test_all_examples(roundtrip, fmt):
    for name, build in examples.tests:
        if fmt == "jsonld" and name in _JSONLD_UNREPRESENTABLE:
            with pytest.raises(ProvJSONLDException, match=r"[Mm]ention"):
                roundtrip(build())
            continue
        roundtrip(build())
