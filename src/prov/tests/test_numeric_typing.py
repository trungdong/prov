"""Numeric datatype fidelity (3.0): #249/#251 (PROV-N).

Old behaviour (2.x): PROV-N rendered out-of-int32 ints as bare INT_LITERALs
and floats as %g xsd:float.
"""

import json

import pytest

from prov.tests.conftest import ex_document

INT32_MAX = 2**31 - 1
INT64_MAX = 2**63 - 1


def test_plain_int_in_range_unchanged() -> None:
    entity = ex_document().entity("ex:e1", {"ex:attr": 42})
    ((_, value),) = entity.extra_attributes
    assert value == 42 and type(value) is int


def test_provn_int_magnitude_ladder() -> None:
    # #249: bare INT_LITERAL is xsd:int sugar, so out-of-int32 values must
    # carry an explicit in-range datatype.
    document = ex_document()
    document.entity("ex:small", {"ex:v": 5})
    document.entity("ex:big", {"ex:v": INT32_MAX + 1})
    document.entity("ex:huge", {"ex:v": INT64_MAX + 1})
    provn = document.get_provn()
    assert "[ex:v=5]" in provn
    assert f'"{INT32_MAX + 1}" %% xsd:long' in provn
    assert f'"{INT64_MAX + 1}" %% xsd:integer' in provn


def test_provn_float_full_precision_double() -> None:
    # #251: floats are xsd:double at full repr precision, matching JSON/XML/RDF.
    document = ex_document()
    document.entity("ex:e1", {"ex:v": 0.123456789})
    provn = document.get_provn()
    assert '"0.123456789" %% xsd:double' in provn
    assert "xsd:float" not in provn


BOUNDARY_INTS = [
    INT32_MAX,
    INT32_MAX + 1,
    -(2**31),
    -(2**31) - 1,
    INT64_MAX,
    INT64_MAX + 1,
]


@pytest.mark.parametrize("value", BOUNDARY_INTS)
def test_int_boundaries_roundtrip(value, roundtrip) -> None:
    document = ex_document()
    document.entity("ex:e1", {"ex:v": value})
    roundtrip(document)


def test_json_dollar_is_always_a_string() -> None:
    # #246: the submission's typedLiteral schema requires a string "$".
    document = ex_document()
    document.entity("ex:e1", {"ex:i": 100, "ex:f": 0.5, "ex:big": INT32_MAX + 1})
    container = json.loads(document.serialize(format="json"))
    attrs = container["entity"]["ex:e1"]
    assert attrs["ex:i"] == {"$": "100", "type": "xsd:int"}
    assert attrs["ex:f"] == {"$": "0.5", "type": "xsd:double"}
    assert attrs["ex:big"] == {"$": str(INT32_MAX + 1), "type": "xsd:long"}
