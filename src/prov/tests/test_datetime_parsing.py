"""Unit tests for the stdlib-based xsd:dateTime parser (3.0 dateutil drop, #237)."""

import datetime
import warnings

import pytest

from prov.model import (
    XSD_DATETIME,
    XSD_STRING,
    Literal,
    ProvDocument,
    ProvException,
    ProvFutureRejectionWarning,
    parse_xsd_datetime,
)
from prov.tests.conftest import ROUNDTRIP_FORMATS

UTC = datetime.timezone.utc


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
        # fractional seconds of any length (fromisoformat on 3.10 takes only 3 or 6 digits)
        (
            "2012-12-03T21:08:16.68Z",
            datetime.datetime(2012, 12, 3, 21, 8, 16, 680000, tzinfo=UTC),
        ),
        (
            "2012-12-03T21:08:16.1234567Z",
            datetime.datetime(2012, 12, 3, 21, 8, 16, 123456, tzinfo=UTC),
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
    ],
)
def test_parse_xsd_datetime_rejects(text) -> None:
    assert parse_xsd_datetime(text) is None


def test_factory_rejects_bad_time_with_prov_exception() -> None:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    with pytest.raises(ProvException):
        document.activity("ex:a1", startTime="not a date")


def _document() -> ProvDocument:
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    return document


def test_time_attributes_accept_a_typed_datetime_literal() -> None:
    document = _document()
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
        _document().activity("ex:a1", startTime=value)


def test_prov_o_time_outside_the_lexical_space_raises() -> None:
    turtle = (
        "@prefix ex: <http://example.org/> .\n"
        "@prefix prov: <http://www.w3.org/ns/prov#> .\n"
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
        'ex:a1 a prov:Activity ; prov:startedAtTime "2012-13-01T00:00:00"^^xsd:dateTime .\n'
    )
    with pytest.raises(
        ProvException, match="Invalid value for attribute prov:startTime"
    ):
        ProvDocument.deserialize(content=turtle, format="rdf", rdf_format="turtle")


_BEYOND = "has a timezone offset beyond ±14:00"
_BEYOND_ISSUE = 513


@pytest.mark.parametrize(
    "time",
    [
        "2012-01-01T00:00:00+15:00",
        "2012-01-01T00:00:00-14:01",
        "2012-01-01T00:00:00+14:00:30",
        datetime.datetime(
            2012,
            1,
            1,
            tzinfo=datetime.timezone(datetime.timedelta(hours=14, minutes=30)),
        ),
        Literal("2012-01-01T00:00:00+15:00", XSD_DATETIME),
    ],
)
def test_time_beyond_the_offset_bound_warns(time) -> None:
    with pytest.warns(
        ProvFutureRejectionWarning,
        match=rf"^prov:startTime \S+ {_BEYOND}\. prov 3\.3\.0 will reject this \(#{_BEYOND_ISSUE}\)$",
    ) as caught:
        activity = _document().activity("ex:a1", startTime=time)
    assert len(caught) == 1
    offset = activity.get_startTime().utcoffset()
    assert abs(offset) > datetime.timedelta(hours=14)


@pytest.mark.parametrize(
    "text",
    [
        "2012-01-01T00:00:00+14:00",
        "2012-01-01T00:00:00-14:00",
        "2012-01-01T00:00:00Z",
        "2012-01-01T00:00:00",
    ],
)
def test_time_within_the_offset_bound_does_not_warn(text) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _document().activity("ex:a1", startTime=text)


def test_typed_datetime_value_beyond_the_offset_bound_warns() -> None:
    value = Literal("2011-11-16T16:05:33+15:00", XSD_DATETIME)
    with pytest.warns(
        ProvFutureRejectionWarning,
        match=r'^ex:t "2011-11-16T16:05:33\+15:00" %% xsd:dateTime'
        rf" {_BEYOND}\. prov 3\.3\.0 will keep it as a Literal \(#{_BEYOND_ISSUE}\)$",
    ) as caught:
        entity = _document().entity("ex:e1", {"ex:t": value})
    assert len(caught) == 1
    assert entity.get_attribute("ex:t") == {parse_xsd_datetime(value.value)}


@pytest.mark.parametrize(
    "text",
    [
        "2011-11-16T16:05:33+14:00",
        "2011-11-16T16:05:33-14:00",
        "2011-11-16T16:05:33Z",
        "2011-11-16T16:05:33",
    ],
)
def test_typed_datetime_value_within_the_offset_bound_does_not_warn(text) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _document().entity("ex:e1", {"ex:t": Literal(text, XSD_DATETIME)})


@pytest.mark.parametrize("fmt", ROUNDTRIP_FORMATS)
def test_every_reader_warns_about_an_offset_beyond_the_bound(fmt) -> None:
    document = _document()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ProvFutureRejectionWarning)
        document.activity("ex:a1", startTime="2012-01-01T00:00:00+15:00")
        document.entity(
            "ex:e1", {"ex:t": Literal("2011-11-16T16:05:33+15:00", XSD_DATETIME)}
        )
    text = document.serialize(format=fmt)

    with pytest.warns(ProvFutureRejectionWarning) as caught:
        read = ProvDocument.deserialize(content=text, format=fmt)

    future = [w for w in caught if w.category is ProvFutureRejectionWarning]
    assert {w.filename for w in future} == {__file__}
    messages = sorted(str(w.message) for w in future)
    assert messages == [
        f'ex:t "2011-11-16T16:05:33+15:00" %% xsd:dateTime {_BEYOND}.'
        f" prov 3.3.0 will keep it as a Literal (#{_BEYOND_ISSUE})",
        f"prov:startTime 2012-01-01T00:00:00+15:00 {_BEYOND}."
        f" prov 3.3.0 will reject this (#{_BEYOND_ISSUE})",
    ]
    assert read == document
