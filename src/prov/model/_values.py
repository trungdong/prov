"""Checks and conversions on attribute values at assertion.

:mod:`prov.model.records` calls :func:`time_offset_detail` for a time value,
:func:`python_value_form` and :func:`no_prov_form_detail` for a value of a type
the model does not hold as it is, :func:`unresolved_name_detail` for a literal
typed as a qualified name, and :func:`xsd_value` for the value a typed literal's
text denotes. This module imports nothing from
:mod:`prov.model.records`, so it returns text and datatypes and the caller
builds the ``Literal`` or raises.
"""

from __future__ import annotations

import base64
import datetime
import decimal
import functools
import math
import re
import reprlib
import sys
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from prov.constants import (
    XSD,
    XSD_ANYURI,
    XSD_BOOLEAN,
    XSD_BYTE,
    XSD_DATE,
    XSD_DATETIME,
    XSD_DECIMAL,
    XSD_DOUBLE,
    XSD_FLOAT,
    XSD_INT,
    XSD_INTEGER,
    XSD_LONG,
    XSD_NEGATIVEINTEGER,
    XSD_NONNEGATIVEINTEGER,
    XSD_NONPOSITIVEINTEGER,
    XSD_POSITIVEINTEGER,
    XSD_SHORT,
    XSD_STRING,
    XSD_TIME,
    XSD_UNSIGNEDBYTE,
    XSD_UNSIGNEDINT,
    XSD_UNSIGNEDLONG,
    XSD_UNSIGNEDSHORT,
)
from prov.identifier import QualifiedName

if TYPE_CHECKING:
    from prov.model.bundle import ProvBundle

# PROV-N's LANGTAG ([63]) without the "@"; every BCP 47 tag matches it. The
# lexer builds its "@"-prefixed token pattern from the same string.
LANGTAG_PATTERN = r"[A-Za-z]+(?:-[A-Za-z0-9]+)*"

# xsd:dateTime's lexical form (XSD 1.1 section 3.3.7): a year of four or more
# digits, the date, "T", the time, an optional fraction and an optional zone.
# The PROV-N lexer's DATETIME token ([62]) is the same form.
XSD_DATETIME_PATTERN = (
    r"-?[0-9]{4,}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})?"
)
_LANGTAG = re.compile(LANGTAG_PATTERN)

# The lexical spaces of the datatypes prov compares in value space (XSD 1.1
# Part 2: 3.3.2 boolean, 3.3.3 decimal, 3.3.4 float, 3.3.5 double, 3.4.x the
# integer family). A text outside them has no value and compares as text.
_XSD_INTEGER_RE = re.compile(r"[+-]?[0-9]+")
_XSD_DECIMAL_RE = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")
_XSD_DOUBLE_RE = re.compile(
    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|[+-]?INF|NaN"
)
_XSD_BOOLEANS = {"true": True, "false": False, "1": True, "0": False}

# xsd:integer and its twelve subtypes with their bounds; None is unbounded.
_XSD_INTEGER_BOUNDS: dict[QualifiedName, tuple[int | None, int | None]] = {
    XSD_INTEGER: (None, None),
    XSD_LONG: (-(2**63), 2**63 - 1),
    XSD_INT: (-(2**31), 2**31 - 1),
    XSD_SHORT: (-(2**15), 2**15 - 1),
    XSD_BYTE: (-(2**7), 2**7 - 1),
    XSD_UNSIGNEDLONG: (0, 2**64 - 1),
    XSD_UNSIGNEDINT: (0, 2**32 - 1),
    XSD_UNSIGNEDSHORT: (0, 2**16 - 1),
    XSD_UNSIGNEDBYTE: (0, 2**8 - 1),
    XSD_NONNEGATIVEINTEGER: (0, None),
    XSD_NONPOSITIVEINTEGER: (None, 0),
    XSD_POSITIVEINTEGER: (1, None),
    XSD_NEGATIVEINTEGER: (None, -1),
}

# A NaN is identical to itself (XSD 1.1 Part 2, 3.3.5, and PROV-CONSTRAINTS
# 2.3: a PROV instance is a set of statements) while a float NaN is never
# equal to itself, so this text stands in for it in a value key.
NAN_KEY = "NaN"


def key_slot(value: object) -> object:
    """``value`` as it sits in a value key: :data:`NAN_KEY` for a float NaN,
    so a NaN is one value with itself, else the value."""
    return NAN_KEY if isinstance(value, float) and math.isnan(value) else value


def _integer_value(datatype: QualifiedName, text: str) -> int | None:
    if not _XSD_INTEGER_RE.fullmatch(text):
        return None
    try:
        value = int(text)
    except ValueError:
        # Longer than sys.get_int_max_str_digits(): no value, compares as text.
        return None
    low, high = _XSD_INTEGER_BOUNDS[datatype]
    if (low is not None and value < low) or (high is not None and value > high):
        return None
    return value


def _decimal_value(text: str) -> decimal.Decimal | None:
    # Construction from a text the grammar admits is exact in every context
    # and signals nothing, so the caller's context cannot change the result
    # (#593, #595).
    return decimal.Decimal(text) if _XSD_DECIMAL_RE.fullmatch(text) else None


def _double_value(text: str) -> float | None:
    return float(text) if _XSD_DOUBLE_RE.fullmatch(text) else None


_XSD_VALUES: dict[QualifiedName, Callable[[str], object | None]] = {
    **{
        datatype: functools.partial(_integer_value, datatype)
        for datatype in _XSD_INTEGER_BOUNDS
    },
    XSD_DECIMAL: _decimal_value,
    XSD_DOUBLE: _double_value,
    XSD_FLOAT: _double_value,
    XSD_BOOLEAN: _XSD_BOOLEANS.get,
}


def xsd_value(datatype: QualifiedName | None, text: str) -> object | None:
    """The value ``text`` denotes in ``datatype``'s value space, or ``None``.

    Covers ``xsd:boolean``, ``xsd:decimal``, ``xsd:double``, ``xsd:float`` and
    ``xsd:integer`` with its twelve subtypes (XSD 1.1 Part 2). ``None`` for
    every other datatype and for a text outside the datatype's lexical space
    or the subtype's range; such a literal compares as text (#527, #593,
    #594, #595). A NaN is a ``float`` NaN; :func:`key_slot` gives it its key.
    """
    to_value = _XSD_VALUES.get(datatype) if datatype is not None else None
    return None if to_value is None else to_value(text)


_XSD_MAX_OFFSET = datetime.timedelta(hours=14)


def _offset_beyond_xsd_bound(value: datetime.datetime) -> bool:
    """Whether ``value``'s timezone offset lies outside xsd:dateTime's ±14:00."""
    offset = value.utcoffset()
    return offset is not None and abs(offset) > _XSD_MAX_OFFSET


def _decimal_text(value: decimal.Decimal) -> str | None:
    # xsd:decimal has no exponent, NaN or infinity. A plain form longer than
    # the interpreter's int digit limit is refused, as int() refuses one.
    if not value.is_finite():
        return None
    limit = sys.get_int_max_str_digits()
    if limit and max(abs(value.adjusted()), len(value.as_tuple().digits)) > limit:
        return None
    return format(value, "f")


def _time_text(value: datetime.time) -> str | None:
    # An xsd:time zone is a whole number of minutes within ±14:00.
    offset = value.utcoffset()
    if offset is not None and (
        offset.seconds % 60 or offset.microseconds or abs(offset) > _XSD_MAX_OFFSET
    ):
        return None
    return value.isoformat()


def _duration_text(value: datetime.timedelta) -> str:
    """``value`` as an xsd:duration, such as ``-P1DT2H3M4.5S``; zero is ``PT0S``."""
    sign = "-" if value < datetime.timedelta(0) else ""
    value = abs(value)
    hours, rest = divmod(value.seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    text = f"{value.days}D" if value.days else ""
    clock = ""
    if hours:
        clock += f"{hours}H"
    if minutes:
        clock += f"{minutes}M"
    if seconds or value.microseconds:
        clock += f"{seconds}.{value.microseconds:06d}".rstrip("0").rstrip(".") + "S"
    if clock:
        text += f"T{clock}"
    return f"{sign}P{text or 'T0S'}"


_INT32_MAX = 2**31 - 1
_INT64_MAX = 2**63 - 1


def canonical_xsd_datatype(value: object) -> QualifiedName | None:
    """Return the XSD datatype `prov` asserts for a plain Python value.

    A plain ``int`` gets ``xsd:int``, ``xsd:long`` or ``xsd:integer`` by
    magnitude, and a ``float`` gets ``xsd:double``, as :func:`python_value_form`
    gives them. Anything else returns ``None``.
    """
    if isinstance(value, bool):  # before int: bool is an int subtype
        return None
    if isinstance(value, int):
        if -_INT32_MAX - 1 <= value <= _INT32_MAX:
            return XSD_INT
        if -_INT64_MAX - 1 <= value <= _INT64_MAX:
            return XSD_LONG
        return XSD_INTEGER
    if isinstance(value, float):
        return XSD_DOUBLE
    return None


def _xsd_double_text(value: float) -> str:
    """The xsd:double lexical form of a float: INF, -INF and NaN for the
    non-finite values (XSD 1.1 Part 2, numericalSpecialRep), float's repr()
    otherwise."""
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "INF" if value > 0 else "-INF"
    return float.__repr__(value)


def _xsd_datetime_text(value: datetime.datetime) -> str:
    """ISO 8601 text with an xsd:dateTime-legal zone: an offset that is not a
    whole number of minutes (historical LMT offsets) is normalised to UTC."""
    offset = value.utcoffset()
    if offset is not None and (offset.total_seconds() % 60 or offset.microseconds):
        value = value.astimezone(datetime.UTC)
    return value.isoformat()


# How prov spells a Python value, in lookup order: the plain types first
# (bool before int, datetime before date, because each is a subtype of the
# next), then the types stored as a typed Literal (#482). Each row gives the
# datatype and the function that writes the lexical form, or None when this
# value has none. An int's datatype depends on its magnitude, which
# canonical_xsd_datatype gives; it returns None for every other row's type
# except a float's xsd:double, which equals the row.
_PROV_FORMS: tuple[
    tuple[type | tuple[type, ...], QualifiedName, Callable[[Any], str | None]], ...
] = (
    (str, XSD_STRING, str),
    (bool, XSD_BOOLEAN, lambda value: "true" if value else "false"),
    (int, XSD_INT, int.__repr__),
    (float, XSD_DOUBLE, _xsd_double_text),
    (datetime.datetime, XSD_DATETIME, _xsd_datetime_text),
    (decimal.Decimal, XSD_DECIMAL, _decimal_text),
    (datetime.date, XSD_DATE, datetime.date.isoformat),
    (datetime.time, XSD_TIME, _time_text),
    (datetime.timedelta, XSD["duration"], _duration_text),
    (uuid.UUID, XSD_ANYURI, lambda value: value.urn),
    (
        (bytes, bytearray, memoryview),
        XSD["base64Binary"],
        lambda value: base64.b64encode(bytes(value)).decode("ascii"),
    ),
)


# Bounds a message's copy of a value, which may be a large object.
_value_repr = reprlib.Repr()
_value_repr.maxother = _value_repr.maxstring = 80


def python_value_form(value: object) -> tuple[str | None, QualifiedName] | None:
    """The lexical text and XSD datatype prov spells ``value`` with.

    The five plain types spell as the writers write them: a ``str`` as given
    with ``xsd:string``, a ``bool`` as ``true`` or ``false``, an ``int`` as
    its digits with the datatype of :func:`canonical_xsd_datatype`, a
    ``float`` in xsd:double form, a ``datetime`` in ISO 8601 form. A type
    the model stores as a typed ``Literal`` (#482) spells in that datatype's
    lexical form. ``None`` when the type has no PROV form; the text is
    ``None`` when the type converts but this value has no lexical form, such
    as ``Decimal("NaN")``.
    """
    for types, datatype, text in _PROV_FORMS:
        if isinstance(value, types):
            return text(value), canonical_xsd_datatype(value) or datatype
    return None


def no_prov_form_detail(attr: QualifiedName, value: object) -> str:
    """Why ``value`` of ``attr``, whose type has no PROV form, is rejected (#482)."""
    cls = type(value)
    name = (
        cls.__qualname__
        if cls.__module__ == "builtins"
        else f"{cls.__module__}.{cls.__qualname__}"
    )
    return f"the value {_value_repr.repr(value)} of {attr} has type {name}, which has no PROV form"


def unresolved_name_detail(
    bundle: ProvBundle, text: str, *, attr: QualifiedName | None = None
) -> str | None:
    """Why the qualified name ``text`` does not resolve by its prefix in
    ``bundle``, or ``None`` when it does (#516, #551, #553).

    ``attr`` names the attribute after the text. The caller raises its own
    error with the sentence, adding the position where its format has one.
    """
    reason = bundle._unresolved_reason(text)
    if reason is None:
        return None
    of_attr = f" of {attr}" if attr is not None else ""
    return f"the qualified name {text!r}{of_attr} does not resolve, because {reason}"


def time_offset_detail(attr: QualifiedName, value: datetime.datetime) -> str | None:
    """Why the time ``value`` of ``attr`` is not an ``xsd:dateTime``, or ``None``.

    XSD 1.1 (section 3.3.7) bounds the timezone offset to ±14:00 (#513).
    """
    if _offset_beyond_xsd_bound(value):
        return f"{attr} {value.isoformat()} has a timezone offset beyond ±14:00"
    return None
