"""Checks on attribute values at assertion, and the warnings they raise.

:class:`~prov.model.ProvRecord` asserts a value through
:meth:`~prov.model.ProvRecord._coerce_attribute_value`, which converts it
and then calls :func:`check_attribute_value` once. The checks here know
nothing of the record classes: :mod:`prov.model.records` imports this
module, never the reverse, and passes the value types that need no check as
arguments. The 3.3.0 rejections of sections 5.4 and 5.7 of the release
design land here.
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
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from prov._warnings import ProvFutureRejectionWarning, future_rejection_message, warn
from prov.constants import (
    PROV_ATTRIBUTE_LITERALS,
    PROV_ATTRIBUTE_QNAMES,
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
_LANGTAG = re.compile(LANGTAG_PATTERN)


_XSD_MAX_OFFSET = datetime.timedelta(hours=14)


def _offset_beyond_xsd_bound(value: datetime.datetime) -> bool:
    """Whether ``value``'s timezone offset lies outside xsd:dateTime's ±14:00."""
    offset = value.utcoffset()
    return offset is not None and abs(offset) > _XSD_MAX_OFFSET


#  Attribute value warnings and the rebuild guard
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


def _warn_offset_beyond_bound(detail: str, outcome: str = "reject this") -> None:
    """Warn that the time in ``detail`` has an offset beyond ±14:00 (#513)."""
    if not _rebuilding.get():
        warn(
            future_rejection_message(
                f"{detail} has a timezone offset beyond ±14:00", outcome, issue=513
            ),
            ProvFutureRejectionWarning,
        )


def _warn_about_value(
    attr: QualifiedName,
    original_value: object,
    value: object,
    plain_bases: tuple[type, ...],
    literal_type: type,
) -> None:
    """Warn about a converted non-formal attribute value 3.3.0 treats differently."""
    if isinstance(value, datetime.datetime):
        if isinstance(original_value, literal_type) and _offset_beyond_xsd_bound(value):
            _warn_offset_beyond_bound(
                f"{attr} {original_value}", "keep it as a Literal"
            )
    elif value is not None and not isinstance(value, plain_bases):
        _warn_no_prov_form(attr, value)


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


def _warn_unresolved_name(
    bundle: ProvBundle, attr: QualifiedName, literal: object, value: object
) -> None:
    """Warn that ``literal``, typed as a qualified name, does not resolve by its
    prefix (#516, #553); ``value`` is what it converted to."""
    datatype = getattr(literal, "datatype", None)
    text = getattr(literal, "value", "")
    if (
        _reader_checks_names.get()
        or _rebuilding.get()
        or datatype not in (PROV_QUALIFIEDNAME, XSD_QNAME)
    ):
        return
    reason = bundle._unresolved_reason(text)
    if reason is not None:
        today = (
            f"it reads as {value}"
            if isinstance(value, QualifiedName)
            else "it is kept as a Literal"
        )
        issue = 553 if isinstance(value, QualifiedName) else 516
        warn(
            future_rejection_message(
                f"the qualified name {text!r} of {attr} does not resolve,"
                f" because {reason}; {today}",
                issue=issue,
            ),
            ProvFutureRejectionWarning,
        )


def check_attribute_value(
    bundle: ProvBundle,
    attr: QualifiedName,
    original_value: object,
    value: object,
    *,
    plain_types: frozenset[type],
    plain_bases: tuple[type, ...],
    literal_type: type,
) -> None:
    """Run the 3.3.0 checks on a converted attribute value.

    A time position checks its offset. Any other non-formal position checks
    a value whose type is not in ``plain_types``, and a value converted from
    a ``literal_type`` typed as a qualified name. Formal qualified-name
    positions have nothing to check.
    """
    if attr in PROV_ATTRIBUTE_QNAMES:
        return
    if attr in PROV_ATTRIBUTE_LITERALS:
        if isinstance(value, datetime.datetime) and _offset_beyond_xsd_bound(value):
            _warn_offset_beyond_bound(f"{attr} {value.isoformat()}")
        return
    if type(value) not in plain_types:
        _warn_about_value(attr, original_value, value, plain_bases, literal_type)
    elif isinstance(original_value, literal_type):
        _warn_unresolved_name(bundle, attr, original_value, value)
