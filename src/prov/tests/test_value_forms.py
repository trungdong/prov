"""The form an attribute value takes at assertion (#482, #526).

A Python value of a type with an XSD datatype is stored as a ``Literal`` of
that datatype, and one with no PROV form raises ``ProvValueError``. An
``Identifier`` is stored as an ``xsd:anyURI`` ``Literal``, and a ``Literal``
typed ``xsd:QName`` or ``prov:QUALIFIED_NAME`` whose prefix is declared is
stored as a ``QualifiedName``.
"""

from __future__ import annotations

import datetime
import decimal
import fractions
import re
import uuid
from collections.abc import Callable, Sequence
from typing import Any

import pytest

from prov.model import (
    PROV_QUALIFIEDNAME,
    XSD,
    XSD_ANYURI,
    XSD_BOOLEAN,
    XSD_DATE,
    XSD_DECIMAL,
    XSD_INT,
    XSD_QNAME,
    XSD_TIME,
    Identifier,
    Literal,
    Namespace,
    ProvDocument,
    ProvValueError,
    QualifiedName,
)
from prov.tests.conftest import EX_URI, ROUNDTRIP_FORMATS, ex_document


class _Opaque:
    def __repr__(self) -> str:
        return "<opaque>"


class _Float(float):
    pass


class _Iri(Identifier):
    pass


HALF_MINUTE = datetime.timezone(datetime.timedelta(seconds=30))

# A Python value and the Literal prov stores it as.
CONVERTED: list[tuple[Any, Literal]] = [
    (decimal.Decimal("1.5"), Literal("1.5", XSD_DECIMAL)),
    (decimal.Decimal("1E+2"), Literal("100", XSD_DECIMAL)),
    (datetime.date(2026, 1, 1), Literal("2026-01-01", XSD_DATE)),
    (datetime.time(10, 30), Literal("10:30:00", XSD_TIME)),
    (
        datetime.time(10, 30, 15, 500000, tzinfo=datetime.UTC),
        Literal("10:30:15.500000+00:00", XSD_TIME),
    ),
    (datetime.timedelta(hours=1), Literal("PT1H", XSD["duration"])),
    (
        datetime.timedelta(days=1, seconds=4, microseconds=500000),
        Literal("P1DT4.5S", XSD["duration"]),
    ),
    (datetime.timedelta(hours=49, minutes=3), Literal("P2DT1H3M", XSD["duration"])),
    (-datetime.timedelta(minutes=90), Literal("-PT1H30M", XSD["duration"])),
    (datetime.timedelta(0), Literal("PT0S", XSD["duration"])),
    (
        uuid.UUID(int=1),
        Literal("urn:uuid:00000000-0000-0000-0000-000000000001", XSD_ANYURI),
    ),
    (b"abc", Literal("YWJj", XSD["base64Binary"])),
    (bytearray(b"abc"), Literal("YWJj", XSD["base64Binary"])),
    (memoryview(b"abc"), Literal("YWJj", XSD["base64Binary"])),
]


def _ids(rows: Sequence[tuple[Any, Any]]) -> list[str]:
    return [f"{type(value).__name__}-{i}" for i, (value, _) in enumerate(rows)]


@pytest.mark.parametrize(("value", "literal"), CONVERTED, ids=_ids(CONVERTED))
def test_python_value_is_stored_as_a_literal(value: Any, literal: Literal) -> None:
    entity = ex_document().entity("ex:e", {"ex:v": value})
    (stored,) = entity.get_attribute("ex:v")
    assert isinstance(stored, Literal)
    assert (stored.value, stored.datatype) == (literal.value, literal.datatype)


# rdflib rewrites an xsd:duration lexical form when it parses a literal, so
# PT0S reads back as P0D (#620, conformance caveat C10).
RDF_UNREADABLE = Literal("PT0S", XSD["duration"])


@pytest.mark.parametrize("fmt", ROUNDTRIP_FORMATS)
def test_converted_values_round_trip(fmt: str) -> None:
    document = ex_document()
    for i, (value, literal) in enumerate(CONVERTED):
        if fmt == "rdf" and literal == RDF_UNREADABLE:
            continue
        document.entity(f"ex:e{i}", {"ex:v": value})
    text = document.serialize(format=fmt)
    assert ProvDocument.deserialize(content=text, format=fmt) == document


def test_prov_o_reads_an_exponent_decimal_as_a_value() -> None:
    # rdflib normalises any decimal text that Python's Decimal() accepts when
    # it parses a literal, so "1e1", outside xsd:decimal's lexical space and a
    # text in every other format, comes back from PROV-O as rdflib's decimal
    # text and compares as the value 10 (conformance caveat C10).
    document = ex_document()
    document.entity("ex:e", {"ex:v": Literal("1e1", XSD_DECIMAL)})
    (entity,) = ProvDocument.deserialize(
        content=document.serialize(format="rdf"), format="rdf"
    ).get_records()
    (value,) = entity.get_attribute("ex:v")
    assert isinstance(value, Literal)
    assert value == Literal("10", XSD_DECIMAL)
    assert value != Literal("1e1", XSD_DECIMAL)


@pytest.mark.parametrize("text", ["NaN", "sNaN"])
def test_prov_o_cannot_write_a_nan_decimal_beside_a_number(text: str) -> None:
    # rdflib's Turtle serializer orders the values of one predicate, and a
    # Decimal NaN has no order against a number (conformance caveat C11).
    document = ex_document()
    document.entity("ex:e", [("ex:v", Literal(text, XSD_DECIMAL)), ("ex:v", 0)])
    with pytest.raises(decimal.InvalidOperation):
        document.serialize(format="rdf")


# A value prov rejects, and the end of its message after "the value ... of ex:v ".
REJECTED: list[tuple[Any, str]] = [
    (fractions.Fraction(1, 3), "has type fractions.Fraction, which has no PROV form"),
    (complex(1, 2), "has type complex, which has no PROV form"),
    ((1, 2), "has type tuple, which has no PROV form"),
    (_Opaque(), f"has type {__name__}._Opaque, which has no PROV form"),
    (decimal.Decimal("NaN"), "has no xsd:decimal form"),
    (decimal.Decimal("Infinity"), "has no xsd:decimal form"),
    (datetime.time(10, 30, tzinfo=HALF_MINUTE), "has no xsd:time form"),
    (
        datetime.time(10, 30, tzinfo=datetime.timezone(datetime.timedelta(hours=15))),
        "has no xsd:time form",
    ),
    (decimal.Decimal("1E+10000"), "has no xsd:decimal form"),
    (decimal.Decimal("1E-10000"), "has no xsd:decimal form"),
]


@pytest.mark.parametrize(("value", "detail"), REJECTED, ids=_ids(REJECTED))
def test_value_with_no_prov_form_raises(value: Any, detail: str) -> None:
    message = f"^the value {re.escape(repr(value))} of ex:v {re.escape(detail)}$"
    with pytest.raises(ProvValueError, match=message):
        _ = ex_document().entity("ex:e", {"ex:v": value})


def test_long_rejected_value_is_shortened_in_the_message() -> None:
    with pytest.raises(ProvValueError) as info:
        _ = ex_document().entity("ex:e", {"ex:v": tuple(range(1000))})  # type: ignore[dict-item]
    assert "..." in str(info.value)
    assert len(str(info.value)) < 200


def test_json_number_read_as_decimal_is_stored_as_a_literal() -> None:
    content = (
        '{"prefix": {"ex": "http://example.org/"}, "entity": {"ex:e": {"ex:x": 1.5}}}'
    )
    document = ProvDocument.deserialize(
        content=content, format="json", parse_float=decimal.Decimal
    )
    (entity,) = document.get_record("ex:e")
    assert entity.get_attribute("ex:x") == {Literal("1.5", XSD_DECIMAL)}


PROV_VALUES: list[Any] = [
    "text",
    1,
    True,
    1.5,
    _Float(1.5),
    datetime.datetime(2026, 1, 1, 12),
    QualifiedName(XSD, "x"),
    Literal("hi", langtag="en"),
    Literal("1.5", XSD_DECIMAL),
    Literal("2026-01-01", XSD_DATE),
    Literal("maybe", XSD["boolean"]),
]


@pytest.mark.parametrize("value", PROV_VALUES, ids=repr)
def test_value_with_a_prov_form_is_stored_as_given(value: Any) -> None:
    entity = ex_document().entity("ex:e", {"ex:v": value})
    assert entity.get_attribute("ex:v") == {value}


@pytest.mark.parametrize(
    "value",
    [Identifier(f"{EX_URI}i"), _Iri(f"{EX_URI}i")],
    ids=["Identifier", "subclass"],
)
def test_identifier_value_is_stored_as_an_anyuri_literal(value: Identifier) -> None:
    entity = ex_document().entity("ex:e", {"ex:v": value})
    assert entity.get_attribute("ex:v") == {Literal(f"{EX_URI}i", XSD_ANYURI)}


@pytest.mark.parametrize("fmt", ROUNDTRIP_FORMATS)
def test_anyuri_value_reads_back_as_a_literal(fmt: str) -> None:
    document = ex_document()
    document.entity("ex:e", {"ex:v": Identifier("http://other.org/i")})
    text = document.serialize(format=fmt)
    (entity,) = ProvDocument.deserialize(content=text, format=fmt).get_records()
    (value,) = entity.get_attribute("ex:v")
    assert isinstance(value, Literal)
    assert value == Literal("http://other.org/i", XSD_ANYURI)


@pytest.mark.parametrize("datatype", [XSD_QNAME, PROV_QUALIFIEDNAME], ids=str)
def test_qualified_name_literal_is_stored_as_a_qualified_name(
    datatype: QualifiedName,
) -> None:
    entity = ex_document().entity("ex:e", {"ex:v": Literal("ex:x", datatype)})
    (value,) = entity.get_attribute("ex:v")
    assert isinstance(value, QualifiedName)
    assert value == Namespace("ex", EX_URI)["x"]


def _updated(document: ProvDocument) -> ProvDocument:
    other = ex_document()
    other.update(document)
    return other


def _added(document: ProvDocument) -> ProvDocument:
    other = ex_document()
    for bundle in document.bundles:
        for record in bundle.get_records():
            other.add_record(record)
    return other


REBUILDS: dict[str, Callable[[ProvDocument], ProvDocument]] = {
    "unified": lambda document: document.unified(),
    "flattened": lambda document: document.flattened(),
    "update": _updated,
    "add_record": _added,
}


@pytest.mark.parametrize("rebuild", REBUILDS.values(), ids=REBUILDS.keys())
def test_qualified_name_value_under_a_bundle_prefix_keeps_its_namespace(
    rebuild: Callable[[ProvDocument], ProvDocument],
) -> None:
    # A qualified-name value registers its namespace where it is asserted, so
    # a copy under another bundle or document declares the prefix and reads
    # back equal.
    document = ex_document()
    bundle = document.bundle("ex:b")
    bundle.add_namespace("zz", "http://example.org/zz/")
    bundle.entity("ex:e", {"ex:v": Literal("zz:x", XSD_QNAME)})
    rebuilt = rebuild(document)
    text = rebuilt.serialize(format="json")
    assert ProvDocument.deserialize(content=text, format="json") == rebuilt


# A text outside its datatype's lexical space has no value: it is stored as
# the Literal with its text and compares as text (#593, #594).
ILL_FORMED: list[Literal] = [
    Literal("sNaN", XSD_DECIMAL),
    Literal("NaN", XSD_DECIMAL),
    Literal("Infinity", XSD_DECIMAL),
    Literal("1e1", XSD_DECIMAL),
    Literal("True", XSD_BOOLEAN),
    Literal("1.0", XSD_INT),
]


@pytest.mark.parametrize("literal", ILL_FORMED, ids=str)
def test_ill_formed_text_is_stored_and_compared_as_text(literal: Literal) -> None:
    entity = ex_document().entity("ex:e", {"ex:v": literal})
    (stored,) = entity.get_attribute("ex:v")
    assert isinstance(stored, Literal)
    assert stored.value == literal.value
    assert stored == literal
    assert stored != Literal(literal.value + "0", literal.datatype)
