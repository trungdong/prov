"""Numeric datatype fidelity (3.0): #235 (xsd:long collapse), #249/#251 (PROV-N).

Old behaviour (2.x): Literal("42", XSD_LONG) was collapsed to int 42 at
assertion time and re-emitted as xsd:int everywhere; PROV-N rendered
out-of-int32 ints as bare INT_LITERALs and floats as %g xsd:float.
"""

from prov.constants import XSD_INT, XSD_LONG
from prov.model import Literal, ProvDocument

INT32_MAX = 2**31 - 1
INT64_MAX = 2**63 - 1


def _doc():
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    return document


def test_in_range_xsd_long_literal_stays_a_literal():
    # #235: the asserted datatype is part of the value; xsd:long for a value
    # whose canonical datatype is xsd:int must not be collapsed.
    entity = _doc().entity("ex:e1", {"ex:attr": Literal("42", XSD_LONG)})
    ((_, value),) = entity.extra_attributes
    assert value == Literal("42", XSD_LONG)


def test_out_of_int32_xsd_long_literal_collapses_losslessly():
    # canonical datatype of 123456789000 IS xsd:long, so collapsing to a
    # plain int loses nothing: re-serialization asserts xsd:long again.
    entity = _doc().entity("ex:e1", {"ex:attr": Literal("123456789000", XSD_LONG)})
    ((_, value),) = entity.extra_attributes
    assert value == 123456789000


def test_plain_int_in_range_unchanged():
    entity = _doc().entity("ex:e1", {"ex:attr": 42})
    ((_, value),) = entity.extra_attributes
    assert value == 42 and type(value) is int


def test_explicit_xsd_int_literal_in_range_still_collapses():
    # collapse remains lossless for xsd:int in range: today's behaviour kept.
    entity = _doc().entity("ex:e1", {"ex:attr": Literal("42", XSD_INT)})
    ((_, value),) = entity.extra_attributes
    assert value == 42


def test_provn_int_magnitude_ladder():
    # #249: bare INT_LITERAL is xsd:int sugar, so out-of-int32 values must
    # carry an explicit in-range datatype.
    document = _doc()
    document.entity("ex:small", {"ex:v": 5})
    document.entity("ex:big", {"ex:v": INT32_MAX + 1})
    document.entity("ex:huge", {"ex:v": INT64_MAX + 1})
    provn = document.get_provn()
    assert "[ex:v=5]" in provn
    assert f'"{INT32_MAX + 1}" %% xsd:long' in provn
    assert f'"{INT64_MAX + 1}" %% xsd:integer' in provn


def test_provn_float_full_precision_double():
    # #251: floats are xsd:double at full repr precision, matching JSON/XML/RDF.
    document = _doc()
    document.entity("ex:e1", {"ex:v": 0.123456789})
    provn = document.get_provn()
    assert '"0.123456789" %% xsd:double' in provn
    assert "xsd:float" not in provn


def test_literal_built_with_int_value_equals_json_roundtrip():
    document = _doc()
    document.entity("ex:e1", {"ex:attr": Literal(42, XSD_LONG)})
    roundtripped = ProvDocument.deserialize(
        content=document.serialize(format="json"), format="json"
    )
    assert document == roundtripped
