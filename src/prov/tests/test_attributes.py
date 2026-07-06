"""Pytest-native shared attribute round-trip tests.

Migrated from the ``TestAttributesBase`` mixin (``attributes.py``): the 28
single-type-attribute cases collapse into one parametrized function (node ids
``attr-0``..``attr-27``), plus the multi-attribute and multi-value-attribute
cases. Each runs once per target in ``SHARED_TARGETS``. The legacy mixin
remains for the not-yet-migrated xml/rdf/dot modules; both share
``ATTRIBUTE_VALUES``.
"""

import pytest

from prov.model import ProvDocument
from prov.tests.attribute_values import ATTRIBUTE_VALUES, EX_NS


@pytest.mark.parametrize(
    "value",
    [pytest.param(v, id=f"attr-{i}") for i, v in enumerate(ATTRIBUTE_VALUES)],
)
def test_entity_with_one_type_attribute(roundtrip, value):
    document = ProvDocument()
    document.entity(EX_NS["et"], {"prov:type": value})
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
