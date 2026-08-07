"""Property-based round-trip tests over Hypothesis-generated PROV documents.

The ``prov_documents`` strategy (see ``strategies.py``) generates valid PROV
documents; this module asserts that each one survives a serialize ->
deserialize round trip through every *deserializable* format. PROV-N is
write-only (no parser), so it is excluded — the format axis is
``ROUNDTRIP_FORMATS`` (json, xml, rdf, jsonld), reusing the same
``roundtrip_document`` helper the example-based shared tests use.

Example counts and determinism are controlled by the Hypothesis profile
selected in ``conftest.py`` via ``HYPOTHESIS_PROFILE`` (CI uses the bounded
``ci`` profile).
"""

import pytest
from hypothesis import assume, given

from .conftest import ROUNDTRIP_FORMATS, contains_mention, roundtrip_document
from .strategies import prov_documents


@pytest.mark.parametrize("fmt", ROUNDTRIP_FORMATS)
@given(doc=prov_documents())
def test_generated_document_roundtrips(doc, fmt):
    """A generated document equals itself after a serialize/deserialize cycle."""
    # PROV-JSONLD defines no Mention term (documented limitation, see
    # docs/reference/conformance.md) — mention-bearing documents only apply
    # to the other formats.
    assume(fmt != "jsonld" or not contains_mention(doc))
    assert roundtrip_document(doc, fmt) == doc
