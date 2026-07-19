"""Pytest-native shared attribute round-trip tests.

Migrated from the ``TestAttributesBase`` mixin (``attributes.py``): the 28
single-type-attribute cases collapse into one parametrized function (node ids
``attr-0``..``attr-7``, ``attr-9``..``attr-27`` -- ``attr-8``, the
``xsd:decimal`` case, is isolated below), plus the multi-attribute and
multi-value-attribute cases. Each runs once per target in
``SHARED_TARGETS``. The legacy mixin remains for the not-yet-migrated
``test_dot.py``; both share ``ATTRIBUTE_VALUES``.

The multi-attribute cases were RDF-xfailed for #218 (a superset of #77,
decimal comparison, and #89, typed/untyped string): with both fixed, the
``xsd:decimal`` value was the only one in ``ATTRIBUTE_VALUES`` that did not
survive an RDF round trip, so these two reproductions now pass and run
under the plain module-wide ``fmt`` fixture like everything else here. #218
itself stays open: ``test_examples.py``'s ``datatypes`` example still hits a
distinct RDF multi-datatype fidelity loss (``xsd:double`` precision).
"""

import pytest

from prov.model import ProvDocument
from prov.tests.attribute_values import ATTRIBUTE_VALUES, EX_NS


@pytest.mark.parametrize(
    "value",
    [pytest.param(v, id=f"attr-{i}") for i, v in enumerate(ATTRIBUTE_VALUES) if i != 8],
)
def test_entity_with_one_type_attribute(roundtrip, value):
    document = ProvDocument()
    document.entity(EX_NS["et"], {"prov:type": value})
    roundtrip(document)


def test_entity_with_one_type_attribute_decimal(roundtrip):
    document = ProvDocument()
    document.entity(EX_NS["et"], {"prov:type": ATTRIBUTE_VALUES[8]})
    roundtrip(document)


def test_entity_with_multiple_attribute(roundtrip):
    document = ProvDocument()
    attributes = [(EX_NS[f"v_{i}"], value) for i, value in enumerate(ATTRIBUTE_VALUES)]
    document.entity(EX_NS["emov"], attributes)
    roundtrip(document)


def test_entity_with_multiple_value_attribute(roundtrip):
    document = ProvDocument()
    attributes = [("prov:value", value) for value in ATTRIBUTE_VALUES]
    document.entity(EX_NS["emv"], attributes)
    roundtrip(document)
