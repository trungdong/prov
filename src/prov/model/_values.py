"""Checks on attribute values at assertion, and the warnings they raise.

:mod:`prov.model.records` calls :func:`time_offset_detail` for a time value and
:func:`check_converted_value` for a value that is neither a time nor a formal
qualified name. This module imports nothing from :mod:`prov.model.records`,
so the caller passes in the plain value base types, and a literal is any
object with a ``datatype``.
"""

from __future__ import annotations

import datetime
import decimal
import re
import reprlib
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, ParamSpec, Protocol, TypeVar, cast

from prov._warnings import ProvFutureRejectionWarning, future_rejection_message, warn
from prov.constants import (
    PROV_QUALIFIEDNAME,
    XSD,
    XSD_ANYURI,
    XSD_DATE,
    XSD_DECIMAL,
    XSD_QNAME,
    XSD_TIME,
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


_XSD_MAX_OFFSET = datetime.timedelta(hours=14)


def _offset_beyond_xsd_bound(value: datetime.datetime) -> bool:
    """Whether ``value``'s timezone offset lies outside xsd:dateTime's ±14:00."""
    offset = value.utcoffset()
    return offset is not None and abs(offset) > _XSD_MAX_OFFSET


_P = ParamSpec("_P")
_R = TypeVar("_R")

# True while a record is rebuilt from one already asserted, so the 3.3.0
# warnings about its values fire once, when they are first asserted.
_rebuilding: ContextVar[bool] = ContextVar("prov_rebuilding", default=False)


def _rebuild(make: Callable[_P, _R], *args: _P.args, **kwargs: _P.kwargs) -> _R:
    """Return ``make(*args, **kwargs)``, which rebuilds records already asserted."""
    token = _rebuilding.set(True)
    try:
        return make(*args, **kwargs)
    finally:
        _rebuilding.reset(token)


# True while a reader that warns about unresolvable qualified-name values
# itself builds records, so the model does not warn about them again.
_reader_checks_names: ContextVar[bool] = ContextVar(
    "prov_reader_checks_names", default=False
)


@contextmanager
def _reader_checking_names() -> Iterator[None]:
    """Build records inside a reader that checks its qualified-name values."""
    token = _reader_checks_names.set(True)
    try:
        yield
    finally:
        _reader_checks_names.reset(token)


# The values prov 3.3.0 converts to a typed Literal (#482), in lookup order.
# datetime.datetime is a date, so it must be excluded before this table.
_PROV_FORMS: tuple[tuple[type | tuple[type, ...], QualifiedName], ...] = (
    (decimal.Decimal, XSD_DECIMAL),
    (datetime.date, XSD_DATE),
    (datetime.time, XSD_TIME),
    (datetime.timedelta, XSD["duration"]),
    (uuid.UUID, XSD_ANYURI),
    ((bytes, bytearray, memoryview), XSD["base64Binary"]),
)


# Bounds a warning's copy of a value, which may be a large bytes object.
_value_repr = reprlib.Repr()
_value_repr.maxother = _value_repr.maxstring = 80


def _warn_no_prov_form(attr: QualifiedName, value: object) -> None:
    """Warn that 3.3.0 converts or rejects ``value``, which has no PROV form."""
    if _rebuilding.get():
        return
    cls = type(value)
    name = (
        cls.__qualname__
        if cls.__module__ == "builtins"
        else f"{cls.__module__}.{cls.__qualname__}"
    )
    detail = f"the value {_value_repr.repr(value)} of {attr} has type {name}"
    for types, datatype in _PROV_FORMS:
        if isinstance(value, types):
            message = future_rejection_message(
                detail, f"store it as a Literal of type {datatype}", issue=482
            )
            break
    else:
        message = future_rejection_message(
            f"{detail}, which has no PROV form", issue=482
        )
    warn(message, ProvFutureRejectionWarning)


class _TypedText(Protocol):
    """The datatype and text of a ``Literal``."""

    @property
    def datatype(self) -> QualifiedName | None: ...

    @property
    def value(self) -> str: ...


def unresolved_name_detail(
    bundle: ProvBundle,
    text: str,
    resolved: QualifiedName | None,
    *,
    attr: QualifiedName | None = None,
    outcome: str = "it is kept as a Literal",
    compaction_issue: int = 553,
) -> tuple[str, int] | None:
    """Return the 3.3.0 message and issue for ``text`` when it does not resolve
    by its prefix in ``bundle``, or ``None`` when it does (#516, #551, #553).

    ``resolved`` is what prov reads the text as today by compacting an IRI,
    cited as ``compaction_issue``, or ``None`` when the text stays as it is,
    which ``outcome`` describes. ``attr`` names the attribute after the text.
    The caller emits the detail through its own channel, with its position.
    """
    reason = bundle._unresolved_reason(text)
    if reason is None:
        return None
    of_attr = f" of {attr}" if attr is not None else ""
    if resolved is not None:
        today, issue = f"it reads as {resolved}", compaction_issue
    else:
        today, issue = outcome, 516
    return (
        f"the qualified name {text!r}{of_attr} does not resolve, because {reason};"
        f" {today}",
        issue,
    )


def _warn_unresolved_name(
    bundle: ProvBundle, attr: QualifiedName, literal: _TypedText, value: object
) -> None:
    """Warn that ``literal``, typed as a qualified name, does not resolve by its
    prefix (#516, #553); ``value`` is what it converted to."""
    if (
        _reader_checks_names.get()
        or _rebuilding.get()
        or literal.datatype not in (PROV_QUALIFIEDNAME, XSD_QNAME)
    ):
        return
    found = unresolved_name_detail(
        bundle,
        literal.value,
        value if isinstance(value, QualifiedName) else None,
        attr=attr,
    )
    if found is not None:
        detail, issue = found
        warn(future_rejection_message(detail, issue=issue), ProvFutureRejectionWarning)


def time_offset_detail(attr: QualifiedName, value: datetime.datetime) -> str | None:
    """Why the time ``value`` of ``attr`` is not an ``xsd:dateTime``, or ``None``.

    XSD 1.1 (section 3.3.7) bounds the timezone offset to ±14:00 (#513).
    """
    if _offset_beyond_xsd_bound(value):
        return f"{attr} {value.isoformat()} has a timezone offset beyond ±14:00"
    return None


def check_converted_value(
    bundle: ProvBundle,
    attr: QualifiedName,
    original_value: object,
    value: object,
    plain_types: frozenset[type],
    plain_bases: tuple[type, ...],
) -> None:
    """Run the 3.3.0 checks on a non-formal attribute value.

    ``value`` is ``original_value`` after conversion. A value whose type is
    not in ``plain_types`` and not an instance of ``plain_bases`` has no PROV
    form. A value of a plain type converted from a typed literal checks that
    its qualified name resolves. A literal is an object with a ``datatype``.
    """
    if type(value) not in plain_types:
        if value is not None and not isinstance(value, plain_bases):
            _warn_no_prov_form(attr, value)
    elif hasattr(original_value, "datatype"):
        _warn_unresolved_name(bundle, attr, cast(_TypedText, original_value), value)
