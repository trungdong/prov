"""Unit tests for the stdlib-based xsd:dateTime parser (3.0 dateutil drop, #237)."""

import datetime
import re
import warnings

import pytest

from prov.model import (
    XSD_DATETIME,
    XSD_STRING,
    Literal,
    ProvDocument,
    ProvException,
    ProvValueError,
    ProvWarning,
    parse_xsd_datetime,
)
from prov.serializers.provjson import ProvJSONException
from prov.serializers.provjsonld import ProvJSONLDException
from prov.serializers.provn_lexer import ProvNSyntaxError
from prov.serializers.provrdf import ProvRDFException
from prov.serializers.provxml import ProvXMLException
from prov.tests.conftest import ROUNDTRIP_FORMATS, TEXT_FORMATS, ex_document

UTC = datetime.UTC


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "2012-12-03T21:08:16.686Z",
            datetime.datetime(2012, 12, 3, 21, 8, 16, 686000, tzinfo=UTC),
        ),
        ("2012-12-03T21:08:16", datetime.datetime(2012, 12, 3, 21, 8, 16)),
        (
            "2012-12-03T21:08:16+05:30",
            datetime.datetime(
                2012,
                12,
                3,
                21,
                8,
                16,
                tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30)),
            ),
        ),
        # fractional seconds of one to six digits
        (
            "2012-12-03T21:08:16.68Z",
            datetime.datetime(2012, 12, 3, 21, 8, 16, 680000, tzinfo=UTC),
        ),
        (
            "2012-12-03T21:08:16.1Z",
            datetime.datetime(2012, 12, 3, 21, 8, 16, 100000, tzinfo=UTC),
        ),
        (
            "2012-12-03T21:08:16.1234",
            datetime.datetime(2012, 12, 3, 21, 8, 16, 123400),
        ),
        # xsd:dateTime end-of-day form maps to 00:00:00 of the next day
        ("2011-11-16T24:00:00", datetime.datetime(2011, 11, 17, 0, 0)),
        ("2011-11-16T24:00:00.000Z", datetime.datetime(2011, 11, 17, 0, 0, tzinfo=UTC)),
        ("2011-12-31T24:00:00", datetime.datetime(2012, 1, 1, 0, 0)),
        # hour-24 combined with a non-Zulu numeric offset: the offset is
        # attached to the rolled-over (next-day) datetime, not the original.
        (
            "2011-11-16T24:00:00+05:30",
            datetime.datetime(
                2011,
                11,
                17,
                0,
                0,
                tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30)),
            ),
        ),
    ],
)
def test_parse_xsd_datetime_accepts(text, expected) -> None:
    assert parse_xsd_datetime(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "not a date",
        "",
        "2011-11-16",  # xsd:date, not xsd:dateTime (no time part) — pre-3.0 dateutil accepted it; now rejected
        "2011-11-16T24:30:00",  # hour 24 is only valid with 00:00 minutes/seconds
        "Nov 7, 2011",  # dateutil-style leniency is gone in 3.0
        "9999-12-31T24:00:00",  # legal hour-24 form, but rollover overflows datetime.MAXYEAR
        "2011-11-16T21:08:16z",  # lowercase "z" is not a valid xsd:dateTime UTC designator
        # Outside the xsd:dateTime lexical form (XSD 1.1 section 3.3.7),
        # which fromisoformat alone would read.
        "2012-12-03T21:08Z",  # no seconds
        "20121203T210816Z",  # basic format
        "2012-W01-1T21:08:16Z",  # week date
        "2012-12-03T21:08:16,5Z",  # comma before the fraction
        "2012-12-03 21:08:16",  # space for the T
        "2012-12-03T21:08:16+0100",  # offset without a colon
        "2012-12-03T21:08:16.5 +01:00",  # space before the offset
        "2012-01-01T00:00:00+14:00:30",  # seconds in the offset
        "2012-12-03T21:08:16.1234567Z",  # a seventh fractional digit, which a datetime cannot hold (#514)
        "2012-12-03T21:08:16.999999999+01:00",  # nine fractional digits (#514)
    ],
)
def test_parse_xsd_datetime_rejects(text) -> None:
    assert parse_xsd_datetime(text) is None


def test_factory_rejects_bad_time_with_prov_exception() -> None:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    with pytest.raises(ProvException):
        document.activity("ex:a1", startTime="not a date")


def test_factory_accepts_the_hour_24_form() -> None:
    # #237: xsd:dateTime's end-of-day form reads as the next midnight.
    activity = ex_document().activity("ex:a1", startTime="2011-11-16T24:00:00")
    assert activity.get_startTime() == datetime.datetime(2011, 11, 17, 0, 0)


def test_time_attributes_accept_a_typed_datetime_literal() -> None:
    document = ex_document()
    activity = document.activity(
        "ex:a1",
        startTime=Literal("2012-01-01T00:00:00", XSD_DATETIME),
        endTime=Literal("2012-01-02T00:00:00Z", XSD_DATETIME),
    )
    generation = document.wasGeneratedBy(
        "ex:e1", "ex:a1", time=Literal("2012-01-01T00:00:00", XSD_DATETIME)
    )
    assert activity.get_startTime() == datetime.datetime(2012, 1, 1)
    assert activity.get_endTime() == datetime.datetime(2012, 1, 2, tzinfo=UTC)
    assert generation.get_attribute("prov:time") == {datetime.datetime(2012, 1, 1)}


@pytest.mark.parametrize(
    "value",
    [
        Literal("2012-13-01T00:00:00", XSD_DATETIME),
        Literal("2012-01-01T00:00:00", XSD_STRING),
        Literal("2012-01-01T00:00:00", langtag="en"),
    ],
)
def test_time_attribute_rejects_any_other_literal(value) -> None:
    with pytest.raises(
        ProvException, match="Invalid value for attribute prov:startTime"
    ):
        ex_document().activity("ex:a1", startTime=value)


def test_prov_o_time_outside_the_lexical_space_raises() -> None:
    turtle = (
        "@prefix ex: <http://example.org/> .\n"
        "@prefix prov: <http://www.w3.org/ns/prov#> .\n"
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
        'ex:a1 a prov:Activity ; prov:startedAtTime "2012-13-01T00:00:00"^^xsd:dateTime .\n'
    )
    with pytest.raises(
        ProvRDFException,
        match=re.escape(
            "subject 'http://example.org/a1': Invalid value for attribute prov:startTime"
        ),
    ) as ctx:
        ProvDocument.deserialize(content=turtle, format="rdf", rdf_format="turtle")
    assert type(ctx.value.__cause__) is ProvException


_BEYOND = "has a timezone offset beyond ±14:00"


@pytest.mark.parametrize(
    "time",
    [
        "2012-01-01T00:00:00+15:00",
        "2012-01-01T00:00:00-14:01",
        datetime.datetime(
            2012,
            1,
            1,
            tzinfo=datetime.timezone(datetime.timedelta(hours=14, minutes=30)),
        ),
        Literal("2012-01-01T00:00:00+15:00", XSD_DATETIME),
    ],
)
def test_time_beyond_the_offset_bound_raises(time) -> None:
    # XSD 1.1 section 3.3.7 bounds the offset, so no xsd:dateTime has it (#513).
    with pytest.raises(ProvValueError, match=rf"^prov:startTime \S+ {_BEYOND}$"):
        ex_document().activity("ex:a1", startTime=time)


@pytest.mark.parametrize(
    "text",
    [
        "2012-01-01T00:00:00+14:00",
        "2012-01-01T00:00:00-14:00",
        "2012-01-01T00:00:00Z",
        "2012-01-01T00:00:00",
    ],
)
def test_time_within_the_offset_bound_is_accepted(text) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ex_document().activity("ex:a1", startTime=text)


def test_datetime_value_beyond_the_offset_bound_raises() -> None:
    # A Python datetime is rejected in any position, not only as a time of
    # the statement, because no writer could emit it as an xsd:dateTime.
    value = datetime.datetime(
        2012, 1, 1, tzinfo=datetime.timezone(datetime.timedelta(hours=14, minutes=30))
    )
    with pytest.raises(
        ProvValueError, match=rf"^ex:t 2012-01-01T00:00:00\+14:30 {_BEYOND}$"
    ):
        ex_document().entity("ex:e1", {"ex:t": value})


def test_typed_datetime_value_beyond_the_offset_bound_stays_a_literal() -> None:
    # The text has no xsd:dateTime value, so it is kept as written, as an
    # ill-formed typed literal is.
    value = Literal("2011-11-16T16:05:33+15:00", XSD_DATETIME)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        entity = ex_document().entity("ex:e1", {"ex:t": value})
    assert entity.get_attribute("ex:t") == {value}


@pytest.mark.parametrize(
    "text",
    [
        "2011-11-16T16:05:33+14:00",
        "2011-11-16T16:05:33-14:00",
        "2011-11-16T16:05:33Z",
        "2011-11-16T16:05:33",
    ],
)
def test_typed_datetime_value_within_the_offset_bound_is_a_datetime(text) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        entity = ex_document().entity("ex:e1", {"ex:t": Literal(text, XSD_DATETIME)})
    assert entity.get_attribute("ex:t") == {parse_xsd_datetime(text)}


def _written_with(fmt: str, build, old: str, new: str) -> str:
    # The model no longer holds the value, so the text is written with an
    # accepted one and edited; the formats all write the offset as given.
    document = ex_document()
    build(document)
    text = document.serialize(format=fmt)
    assert text.count(old) == 1
    return text.replace(old, new)


# Each reader's error for a time outside the bound, and what starts its message.
# PROV-N chains it from a positioned syntax error; the other readers chain it
# from their own error, naming the record.
_TIME_ERRORS: dict[str, type[Exception]] = {
    "json": ProvJSONException,
    "xml": ProvXMLException,
    "jsonld": ProvJSONLDException,
    "rdf": ProvRDFException,
    "provn": ProvNSyntaxError,
}
_TIME_WHERE = {
    "json": r"record 'ex:a1': ",
    "xml": r"line 3, <prov:activity> 'ex:a1': ",
    "jsonld": r"Activity 'ex:a1': ",
    "rdf": r"subject 'http://example.org/a1': prov:startTime ",
    "provn": r"line \d+, column \d+: ",
}


@pytest.mark.parametrize("fmt", ROUNDTRIP_FORMATS)
def test_every_reader_rejects_a_time_beyond_the_bound(fmt) -> None:
    text = _written_with(
        fmt,
        lambda d: d.activity("ex:a1", startTime="2012-01-01T00:00:00+14:00"),
        "+14:00",
        "+15:00",
    )
    with pytest.raises(_TIME_ERRORS[fmt]) as ctx:
        ProvDocument.deserialize(content=text, format=fmt)
    error = ctx.value.__cause__
    assert isinstance(error, ProvValueError)
    assert str(error) == f"prov:startTime 2012-01-01T00:00:00+15:00 {_BEYOND}"
    assert re.match(_TIME_WHERE[fmt], str(ctx.value))
    assert isinstance(ctx.value, ValueError) is issubclass(
        _TIME_ERRORS[fmt], ValueError
    )


@pytest.mark.parametrize("fmt", ROUNDTRIP_FORMATS)
def test_every_reader_keeps_a_typed_time_beyond_the_bound_as_a_literal(fmt) -> None:
    document = ex_document()
    document.entity(
        "ex:e1", {"ex:t": Literal("2011-11-16T16:05:33+15:00", XSD_DATETIME)}
    )
    text = document.serialize(format=fmt)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvWarning)
        assert ProvDocument.deserialize(content=text, format=fmt) == document


# Each reader reports a fraction beyond six digits as it reports a time outside
# the lexical form (#514, the #513 precedent).
# PROV-O is the one format that cannot reject or keep the text; see
# test_prov_o_truncates_a_fraction_beyond_six_digits.
_FRACTION_ERRORS = {
    "json": ProvJSONException,
    "xml": ProvXMLException,
    "jsonld": ProvJSONLDException,
    "provn": ProvNSyntaxError,
}


@pytest.mark.parametrize("fmt", TEXT_FORMATS)
def test_every_reader_rejects_a_fraction_beyond_six_digits(fmt) -> None:
    text = _written_with(
        fmt,
        lambda d: d.activity("ex:a1", startTime="2012-01-01T00:00:00.123456Z"),
        ".123456",
        ".1234567",
    )
    with pytest.raises(_FRACTION_ERRORS[fmt]):
        ProvDocument.deserialize(content=text, format=fmt)


@pytest.mark.parametrize("fmt", TEXT_FORMATS)
def test_every_reader_keeps_a_typed_time_with_a_long_fraction_as_a_literal(fmt) -> None:
    document = ex_document()
    document.entity(
        "ex:e1", {"ex:t": Literal("2011-11-16T16:05:33.1234567Z", XSD_DATETIME)}
    )
    text = document.serialize(format=fmt)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ProvWarning)
        assert ProvDocument.deserialize(content=text, format=fmt) == document


def test_prov_o_truncates_a_fraction_beyond_six_digits() -> None:
    # rdflib normalises a literal when it builds it (NORMALIZE_LITERALS), so
    # the PROV-O reader never sees the seventh digit: a time of a statement
    # reads truncated to microseconds, and a typed attribute value reads as
    # the truncated datetime, where every other format rejects the first and
    # keeps the second as a Literal (#514; conformance caveat C10).
    truncated = datetime.datetime(2012, 1, 1, 0, 0, 0, 123456, tzinfo=UTC)
    text = _written_with(
        "rdf",
        lambda d: d.activity("ex:a1", startTime="2012-01-01T00:00:00.123456Z"),
        ".123456",
        ".1234567",
    )
    (activity,) = ProvDocument.deserialize(content=text, format="rdf").get_records()
    assert activity.get_startTime() == truncated
    document = ex_document()
    document.entity(
        "ex:e1", {"ex:t": Literal("2012-01-01T00:00:00.1234567Z", XSD_DATETIME)}
    )
    (entity,) = ProvDocument.deserialize(
        content=document.serialize(format="rdf"), format="rdf"
    ).get_records()
    assert entity.get_attribute("ex:t") == {truncated}
