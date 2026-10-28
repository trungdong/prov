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

import math
import re
from collections import defaultdict

import pytest
from hypothesis import assume, given

from prov.model import XSD_DECIMAL, XSD_DOUBLE, XSD_FLOAT, Literal, ProvDocument

from .conftest import ROUNDTRIP_FORMATS, contains_mention, roundtrip_document
from .strategies import prov_documents, prov_record_pairs, prov_records


def _has_decimal_text(document: ProvDocument, pattern: str) -> bool:
    return any(
        isinstance(value, Literal)
        and value.datatype == XSD_DECIMAL
        and re.search(pattern, value.value)
        for record in document.get_records()
        for _, value in record.attributes
    )


def _is_decimal(value: object) -> bool:
    return isinstance(value, Literal) and value.datatype == XSD_DECIMAL


def _is_nan(value: object) -> bool:
    if isinstance(value, float):
        return math.isnan(value)
    return (
        isinstance(value, Literal)
        and value.datatype in (XSD_DOUBLE, XSD_FLOAT)
        and value.value == "NaN"
    )


def _has_nan_beside_decimal(document: ProvDocument) -> bool:
    """Whether one attribute of one record holds an xsd:decimal value and a NaN."""
    for record in document.get_records():
        values: defaultdict[object, list[object]] = defaultdict(list)
        for name, value in record.attributes:
            values[name].append(value)
        if any(
            any(map(_is_decimal, group)) and any(map(_is_nan, group))
            for group in values.values()
        ):
            return True
    return False


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
    # turning an ill-formed text into a value (conformance caveat C10), and
    # raises when it orders a NaN decimal against a number, or a NaN against an
    # xsd:decimal value under one attribute, on write (C11).
    assume(
        fmt != "rdf"
        or not (
            _has_decimal_text(doc, r"[0-9][eE]|NaN") or _has_nan_beside_decimal(doc)
        )
    )
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
