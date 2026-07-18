"""Unit tests for the stdlib-based xsd:dateTime parser (3.0 dateutil drop, #237)."""

import datetime

import pytest

from prov.model import ProvDocument, ProvException, parse_xsd_datetime

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
def test_parse_xsd_datetime_accepts(text, expected):
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
def test_parse_xsd_datetime_rejects(text):
    assert parse_xsd_datetime(text) is None


def test_factory_rejects_bad_time_with_prov_exception():
    document = ProvDocument()
    document.add_namespace("ex", "http://example.org/")
    with pytest.raises(ProvException):
        document.activity("ex:a1", startTime="not a date")
