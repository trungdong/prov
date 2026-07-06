"""Pytest-native shared attribute round-trip tests.

Migrated from the ``TestAttributesBase`` mixin (``attributes.py``): the 28
single-type-attribute cases collapse into one parametrized function (node ids
``attr-0``..``attr-7``, ``attr-9``..``attr-27`` -- ``attr-8``, the
``xsd:decimal`` case, is isolated below), plus the multi-attribute and
multi-value-attribute cases. Each runs once per target in
``SHARED_TARGETS``. The legacy mixin remains for the not-yet-migrated
``test_dot.py``; both share ``ATTRIBUTE_VALUES``.
"""

import pytest

from prov.model import ProvDocument
from prov.tests.attribute_values import ATTRIBUTE_VALUES, EX_NS

# Fixable RDF datatype-fidelity bugs slated for 3.0: strict xfails so an
# accidental fix flips XFAIL->XPASS and fails the run (design doc §2/§3).
RDF_DECIMAL_XFAIL = pytest.mark.xfail(
    reason="Literal(10, XSD_DECIMAL) round-trips to 10.0, losing xsd:decimal "
    "-- issue #77",
    strict=True,
    raises=AssertionError,
)
RDF_DATATYPE_XFAIL = pytest.mark.xfail(
    reason="RDF loses XSD datatype fidelity across a mixed attribute set -- issue #218",
    strict=True,
    raises=AssertionError,
)

# These functions opt out of the module-wide `fmt` fixture (see conftest.py)
# with their own explicit parametrization so the xfail mark attaches only to
# the rdf param; model/json/xml still run normally.
decimal_fmt = pytest.mark.parametrize(
    "fmt",
    ["model", "json", "xml", pytest.param("rdf", marks=RDF_DECIMAL_XFAIL)],
)
datatype_fmt = pytest.mark.parametrize(
    "fmt",
    ["model", "json", "xml", pytest.param("rdf", marks=RDF_DATATYPE_XFAIL)],
)


@pytest.mark.parametrize(
    "value",
    [pytest.param(v, id=f"attr-{i}") for i, v in enumerate(ATTRIBUTE_VALUES) if i != 8],
)
def test_entity_with_one_type_attribute(roundtrip, value):
    document = ProvDocument()
    document.entity(EX_NS["et"], {"prov:type": value})
    roundtrip(document)


@decimal_fmt
def test_entity_with_one_type_attribute_decimal(roundtrip):
    document = ProvDocument()
    document.entity(EX_NS["et"], {"prov:type": ATTRIBUTE_VALUES[8]})
    roundtrip(document)


@datatype_fmt
def test_entity_with_multiple_attribute(roundtrip):
    document = ProvDocument()
    attributes = [(EX_NS[f"v_{i}"], value) for i, value in enumerate(ATTRIBUTE_VALUES)]
    document.entity(EX_NS["emov"], attributes)
    roundtrip(document)


@datatype_fmt
def test_entity_with_multiple_value_attribute(roundtrip):
    document = ProvDocument()
    attributes = [("prov:value", value) for value in ATTRIBUTE_VALUES]
    document.entity(EX_NS["emv"], attributes)
    roundtrip(document)
