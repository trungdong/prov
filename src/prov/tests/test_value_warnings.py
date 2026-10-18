"""3.3.0 warnings about attribute values, and when they fire (#482, #513, #516)."""

from __future__ import annotations

import copy
import datetime
import decimal
import fractions
import pickle
import uuid
import warnings
from collections.abc import Callable
from typing import Any

import pytest

from prov.model import (
    XSD,
    XSD_DATETIME,
    XSD_DECIMAL,
    XSD_QNAME,
    Identifier,
    Literal,
    ProvBundle,
    ProvDocument,
    ProvFutureRejectionWarning,
    QualifiedName,
)
from prov.tests.conftest import ROUNDTRIP_FORMATS


def _document() -> ProvDocument:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    return document


class _Opaque:
    def __repr__(self) -> str:
        return "<opaque>"


CONVERTED: list[tuple[Any, str, str]] = [
    (decimal.Decimal("1.5"), "decimal.Decimal", "xsd:decimal"),
    (datetime.date(2026, 1, 1), "datetime.date", "xsd:date"),
    (datetime.time(10, 30), "datetime.time", "xsd:time"),
    (datetime.timedelta(hours=1), "datetime.timedelta", "xsd:duration"),
    (uuid.UUID(int=1), "uuid.UUID", "xsd:anyURI"),
    (b"abc", "bytes", "xsd:base64Binary"),
    (memoryview(b"abc"), "memoryview", "xsd:base64Binary"),
]


@pytest.mark.parametrize(
    ("value", "type_name", "datatype"), CONVERTED, ids=[c[1] for c in CONVERTED]
)
def test_value_3_3_converts_warns(value: Any, type_name: str, datatype: str) -> None:
    expected = (
        f"the value {value!r} of ex:v has type {type_name}."
        f" prov 3.3.0 will store it as a Literal of type {datatype} (#482)"
    )
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        entity = _document().entity("ex:e", {"ex:v": value})
    assert [str(w.message) for w in caught] == [expected]
    assert caught[0].filename == __file__
    assert entity.get_attribute("ex:v") == {value}


def test_unhashable_value_3_3_converts_warns_before_failing() -> None:
    with (
        pytest.warns(
            ProvFutureRejectionWarning,
            match=r"^the value bytearray\(b'ab'\) of ex:v has type bytearray\."
            r" prov 3\.3\.0 will store it as a Literal of type xsd:base64Binary \(#482\)$",
        ),
        pytest.raises(TypeError, match="unhashable"),
    ):
        _document().entity("ex:e", {"ex:v": bytearray(b"ab")})  # type: ignore[dict-item]


REJECTED: list[tuple[Any, str]] = [
    (fractions.Fraction(1, 3), "fractions.Fraction"),
    (complex(1, 2), "complex"),
    ((1, 2), "tuple"),
    (_Opaque(), f"{__name__}._Opaque"),
]


@pytest.mark.parametrize(
    ("value", "type_name"), REJECTED, ids=[r[1].rsplit(".")[-1] for r in REJECTED]
)
def test_value_with_no_prov_form_warns(value: Any, type_name: str) -> None:
    expected = (
        f"the value {value!r} of ex:v has type {type_name}, which has no PROV form."
        " prov 3.3.0 will reject this (#482)"
    )
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        entity = _document().entity("ex:e", {"ex:v": value})
    assert [str(w.message) for w in caught] == [expected]
    assert entity.get_attribute("ex:v") == {value}


def test_json_number_read_as_decimal_warns() -> None:
    content = (
        '{"prefix": {"ex": "http://example.org/"}, "entity": {"ex:e": {"ex:x": 1.5}}}'
    )
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        document = ProvDocument.deserialize(
            content=content, format="json", parse_float=decimal.Decimal
        )
    assert [str(w.message) for w in caught] == [
        "the value Decimal('1.5') of ex:x has type decimal.Decimal."
        " prov 3.3.0 will store it as a Literal of type xsd:decimal (#482)"
    ]
    assert caught[0].filename == __file__
    (entity,) = document.get_record("ex:e")
    assert entity.get_attribute("ex:x") == {decimal.Decimal("1.5")}


def test_long_value_is_shortened_in_the_message() -> None:
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        _document().entity("ex:e", {"ex:v": b"x" * 1000})  # type: ignore[dict-item]
    message = str(caught[0].message)
    assert "..." in message
    assert len(message) < 200


class _Float(float):
    pass


PROV_VALUES: list[Any] = [
    "text",
    1,
    True,
    1.5,
    _Float(1.5),
    datetime.datetime(2026, 1, 1, 12),
    Identifier("http://example.org/i"),
    QualifiedName(XSD, "x"),
    Literal("hi", langtag="en"),
    Literal("1.5", XSD_DECIMAL),
    Literal("2026-01-01", XSD["date"]),
    Literal("maybe", XSD["boolean"]),
]


@pytest.mark.parametrize("value", PROV_VALUES, ids=repr)
def test_value_with_a_prov_form_does_not_warn(value: Any) -> None:
    document = _document()
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        document.entity("ex:e", {"ex:v": value})
        document.entity("ex:f", {"ex:v": document.entity("ex:g")})


@pytest.mark.parametrize("fmt", ROUNDTRIP_FORMATS)
def test_typed_literals_read_without_warning(fmt: str) -> None:
    document = _document()
    document.entity(
        "ex:e",
        {
            "ex:d": Literal("1.5", XSD_DECIMAL),
            "ex:t": Literal("10:30:00", XSD["time"]),
            "ex:b": Literal("YWJj", XSD["base64Binary"]),
        },
    )
    text = document.serialize(format=fmt)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        ProvDocument.deserialize(content=text, format=fmt)


def _python_value(bundle: ProvBundle) -> None:
    bundle.entity("ex:r", {"ex:v": datetime.date(2026, 1, 1)})  # type: ignore[dict-item]


def _time(bundle: ProvBundle) -> None:
    bundle.activity("ex:r", startTime="2012-01-01T00:00:00+15:00")


def _typed_datetime(bundle: ProvBundle) -> None:
    bundle.entity("ex:r", {"ex:t": Literal("2011-11-16T16:05:33+15:00", XSD_DATETIME)})


def _qualified_name(bundle: ProvBundle) -> None:
    bundle.entity("ex:r", {"ex:q": Literal("zz:x", XSD_QNAME)})


ASSERTIONS: dict[str, Callable[[ProvBundle], None]] = {
    "python value": _python_value,
    "time": _time,
    "typed datetime": _typed_datetime,
    "qualified name": _qualified_name,
}


def _asserted_twice(assertion: Callable[[ProvBundle], None]) -> ProvDocument:
    # Twice in the document and twice in a bundle, so unified() merges a pair
    # in each scope and flattened() has a bundle to lift.
    document = _document()
    bundle = document.bundle("ex:b")
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        for scope in (document, bundle):
            assertion(scope)
            assertion(scope)
    assert len(caught) == 4
    return document


def _copied(document: ProvDocument) -> None:
    for record in document.get_records():
        record.copy()


def _added(document: ProvDocument) -> None:
    other = ProvDocument()
    for record in document.get_records():
        other.add_record(record)


def _updated(document: ProvDocument) -> None:
    _document().update(document)


def _dot(document: ProvDocument) -> object:
    return pytest.importorskip("prov.dot").prov_to_dot(document)


def _graph_round_trip(document: ProvDocument) -> object:
    graph = pytest.importorskip("prov.graph")
    return graph.graph_to_prov(graph.prov_to_graph(document))


REBUILDS: dict[str, Callable[[ProvDocument], object]] = {
    "copy": _copied,
    "add_record": _added,
    "unified": lambda document: document.unified(),
    "flattened": lambda document: document.flattened(),
    "update": _updated,
    "prov_to_dot": _dot,
    "graph": _graph_round_trip,
    "pickle": lambda document: pickle.loads(pickle.dumps(document)),  # nosec B301 - nosemgrep
    "deepcopy": copy.deepcopy,
}


@pytest.mark.parametrize("assertion", ASSERTIONS.values(), ids=ASSERTIONS.keys())
@pytest.mark.parametrize("rebuild", REBUILDS.values(), ids=REBUILDS.keys())
def test_rebuilt_records_do_not_warn_again(
    assertion: Callable[[ProvBundle], None],
    rebuild: Callable[[ProvDocument], object],
) -> None:
    document = _asserted_twice(assertion)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvFutureRejectionWarning)
        rebuild(document)


@pytest.mark.parametrize("assertion", ASSERTIONS.values(), ids=ASSERTIONS.keys())
def test_assertion_after_a_rebuild_warns(
    assertion: Callable[[ProvBundle], None],
) -> None:
    document = _asserted_twice(assertion)
    unified = document.unified()
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        assertion(unified)
    assert len(caught) == 1


def test_records_built_while_a_document_is_constructed_warn() -> None:
    source = _document()
    records = (
        source.entity(f"ex:e{i}", {"ex:v": fractions.Fraction(1, 3)})  # type: ignore[dict-item]
        for i in range(2)
    )
    with pytest.warns(ProvFutureRejectionWarning) as caught:
        ProvDocument(records=records)
    assert len(caught) == 2
