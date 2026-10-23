"""Property-based round-trip tests over Hypothesis-generated PROV documents.

The ``prov_documents`` strategy (see ``strategies.py``) generates valid PROV
documents; this module asserts that each one survives a serialize ->
deserialize round trip through every *deserializable* format. The format axis
is ``ROUNDTRIP_FORMATS`` (json, xml, rdf, jsonld, provn), reusing the same
``roundtrip_document`` helper the example-based shared tests use.

Example counts and determinism are controlled by the Hypothesis profile
selected in ``conftest.py`` via ``HYPOTHESIS_PROFILE`` (CI uses the bounded
``ci`` profile).
"""

import pytest
from hypothesis import assume, given

from prov.model import XSD_DECIMAL, Literal, ProvDocument

from .conftest import ROUNDTRIP_FORMATS, contains_mention, roundtrip_document
from .strategies import prov_documents, prov_record_pairs, prov_records


def _has_exponent_decimal(document: ProvDocument) -> bool:
    return any(
        isinstance(value, Literal)
        and value.datatype == XSD_DECIMAL
        and ("e" in value.value or "E" in value.value)
        for record in document.get_records()
        for _, value in record.attributes
    )


@pytest.mark.parametrize("fmt", ROUNDTRIP_FORMATS)
@given(doc=prov_documents())
def test_generated_document_roundtrips(doc: ProvDocument, fmt: str) -> None:
    """A generated document equals itself after a serialize/deserialize cycle."""
    # PROV-JSONLD defines no Mention term (documented limitation, see
    # docs/reference/conformance.md) — mention-bearing documents only apply
    # to the other formats.
    assume(fmt != "jsonld" or not contains_mention(doc))
    assert roundtrip_document(doc, fmt) == doc


@pytest.mark.parametrize("fmt", ROUNDTRIP_FORMATS)
@given(doc=prov_records())
def test_generated_record_roundtrips(doc: ProvDocument, fmt: str) -> None:
    """A record holding typed literals in any spelling, identified or not, survives a round trip."""
    # rdflib rewrites an exponent-form xsd:decimal to its decimal text on read,
    # turning an ill-formed text into a value (conformance caveat C10).
    assume(fmt != "rdf" or not _has_exponent_decimal(doc))
    assert roundtrip_document(doc, fmt) == doc


@given(pair=prov_record_pairs())
def test_respelled_values_give_equal_records(
    pair: tuple[ProvDocument, ProvDocument],
) -> None:
    """Two spellings of the same values give equal records from both sides, with equal hashes (#527)."""
    left, right = pair
    assert left == right
    assert right == left
    for a, b in zip(left.get_records(), right.get_records(), strict=True):
        assert a == b
        assert hash(a) == hash(b)
