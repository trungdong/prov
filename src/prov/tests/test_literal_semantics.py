"""Literal value-space semantics (3.0): #77 decimal, #259 langtag, #89 string form."""

import datetime
import io

from prov.constants import XSD_DECIMAL, XSD_INT
from prov.model import Literal, ProvDocument


def _doc():
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    return document


def test_decimal_literals_compare_in_value_space():
    # #77: 10, 10.0 and "10.00" denote the same xsd:decimal value.
    assert Literal(10, XSD_DECIMAL) == Literal(10.0, XSD_DECIMAL)
    assert Literal(10, XSD_DECIMAL) == Literal("10.00", XSD_DECIMAL)
    assert hash(Literal(10, XSD_DECIMAL)) == hash(Literal("10.00", XSD_DECIMAL))
    assert Literal(10, XSD_DECIMAL) != Literal("10.01", XSD_DECIMAL)


def test_non_decimal_literals_compare_lexically():
    # value-space comparison is decimal-only; other datatypes stay lexical.
    assert Literal("1", XSD_INT) != Literal("01", XSD_INT)


def test_langtag_comparison_is_case_insensitive():
    # #259: RDF 1.1 language tags are case-insensitive in the value space.
    assert Literal("hello", langtag="EN") == Literal("hello", langtag="en")
    assert hash(Literal("hello", langtag="EN")) == hash(Literal("hello", langtag="en"))
    assert Literal("hello", langtag="en") != Literal("hello", langtag="fr")


def test_langtag_case_is_preserved_in_output():
    # #259 non-goal: the stored tag is not normalised -- output stays verbatim.
    document = _doc()
    document.entity("ex:e1", {"ex:a": Literal("hello", langtag="EN")})
    assert '"lang": "EN"' in document.serialize(format="json")


def test_rdf_plain_string_emitted_without_xsd_string():
    # #89: one canonical form for string literals -- the plain literal.
    document = _doc()
    document.entity("ex:e1", {"ex:a": "hello"})
    buf = io.BytesIO()
    document.serialize(buf, format="rdf", rdf_format="nt11")
    assert b"^^" not in buf.getvalue()


def test_exact_type_fast_path_preserves_values_and_subclass_handling():
    class MyStr(str):
        pass

    document = _doc()
    when = datetime.datetime(2026, 1, 1)
    entity = document.entity(
        "ex:e1",
        {
            "ex:s": "s",
            "ex:i": 1,
            "ex:f": 1.5,
            "ex:b": True,
            "ex:d": when,
            "ex:sub": MyStr("x"),
        },
    )
    values = {str(k): v for k, v in entity.attributes if str(k).startswith("ex:")}
    # exact-type checks below verify the fast path's own contract (identity
    # of the returned type), which isinstance() cannot distinguish from a
    # subclass match.
    assert values["ex:s"] == "s" and type(values["ex:s"]) is str  # pylint: disable=unidiomatic-typecheck
    assert values["ex:i"] == 1 and type(values["ex:i"]) is int  # pylint: disable=unidiomatic-typecheck
    assert values["ex:f"] == 1.5
    assert values["ex:b"] is True
    assert values["ex:d"] == when
    assert values["ex:sub"] == "x" and type(values["ex:sub"]) is str  # pylint: disable=unidiomatic-typecheck
