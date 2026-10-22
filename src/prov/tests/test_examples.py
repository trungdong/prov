"""Shared example round-trip test: every canonical document of ``examples.py``
through every target in ``SHARED_TARGETS``."""

from collections.abc import Callable

import pytest

from prov.model import ProvDocument
from prov.serializers.provjsonld import ProvJSONLDException
from prov.tests import examples

from .conftest import Roundtrip, contains_mention

EXAMPLES = [pytest.param(build, id=name) for name, build in examples.tests]


@pytest.mark.parametrize("build", EXAMPLES)
def test_example_round_trips(
    roundtrip: Roundtrip, fmt: str, build: Callable[[], ProvDocument]
) -> None:
    document = build()
    # PROV-JSONLD defines no Mention term (docs/reference/conformance.md), so
    # a mention-bearing example raises rather than round-trips.
    if fmt == "jsonld" and contains_mention(document):
        with pytest.raises(ProvJSONLDException, match=r"[Mm]ention"):
            _ = roundtrip(document)
        return
    roundtrip(document)
