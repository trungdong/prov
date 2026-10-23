"""PROV-DM records: elements, relations, literals, and datatype helpers."""

from __future__ import annotations  # defer eval: TYPE_CHECKING names in signatures

import datetime
import decimal
import io
import logging
import math
import os
import re
import typing
import uuid
from collections import defaultdict
from collections.abc import (
    Callable,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    MutableSet,
    Sequence,
    Set as AbstractSet,
)
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Final,
    Protocol,
    Self,
    TypeVar,
    Union,
    cast,
)

from prov import Error
from prov._warnings import warn
from prov.constants import (
    _PROV_N_BARE_RELATIONS,
    PROV_ACTIVITY,
    PROV_AGENT,
    PROV_ALTERNATE,
    PROV_ASSOCIATION,
    PROV_ATTR_ACTIVITY,
    PROV_ATTR_AGENT,
    PROV_ATTR_ALTERNATE1,
    PROV_ATTR_ALTERNATE2,
    PROV_ATTR_BUNDLE,
    PROV_ATTR_COLLECTION,
    PROV_ATTR_DELEGATE,
    PROV_ATTR_ENDER,
    PROV_ATTR_ENDTIME,
    PROV_ATTR_ENTITY,
    PROV_ATTR_GENERAL_ENTITY,
    PROV_ATTR_GENERATED_ENTITY,
    PROV_ATTR_GENERATION,
    PROV_ATTR_INFLUENCEE,
    PROV_ATTR_INFLUENCER,
    PROV_ATTR_INFORMANT,
    PROV_ATTR_INFORMED,
    PROV_ATTR_PLAN,
    PROV_ATTR_RESPONSIBLE,
    PROV_ATTR_SPECIFIC_ENTITY,
    PROV_ATTR_STARTER,
    PROV_ATTR_STARTTIME,
    PROV_ATTR_TIME,
    PROV_ATTR_TRIGGER,
    PROV_ATTR_USAGE,
    PROV_ATTR_USED_ENTITY,
    PROV_ATTRIBUTE_LITERALS,
    PROV_ATTRIBUTE_QNAMES,
    PROV_ATTRIBUTES,
    PROV_ATTRIBUTION,
    PROV_COMMUNICATION,
    PROV_DELEGATION,
    PROV_DERIVATION,
    PROV_END,
    PROV_ENTITY,
    PROV_GENERATION,
    PROV_INFLUENCE,
    PROV_INTERNATIONALIZEDSTRING,
    PROV_INVALIDATION,
    PROV_LABEL,
    PROV_MEMBERSHIP,
    PROV_MENTION,
    PROV_N_MAP,
    PROV_QUALIFIEDNAME,
    PROV_SPECIALIZATION,
    PROV_START,
    PROV_TYPE,
    PROV_USAGE,
    PROV_VALUE,
    XSD_ANYURI,
    XSD_BOOLEAN,
    XSD_DATETIME,
    XSD_DOUBLE,
    XSD_INT,
    XSD_INTEGER,
    XSD_LONG,
    XSD_QNAME,
    XSD_STRING,
)
from prov.identifier import (
    Identifier,
    Namespace,
    QualifiedName,
    _provn_string_literal,
    _slot_state,
)
from prov.model._values import (
    _LANGTAG,
    NAN_KEY,
    XSD_DATETIME_PATTERN,
    _offset_beyond_xsd_bound,
    no_prov_form_detail,
    python_value_form,
    time_offset_detail,
    unresolved_name_detail,
    xsd_value,
)

if TYPE_CHECKING:
    from prov.model.bundle import ProvBundle

logger = logging.getLogger(__name__)


# Type aliases for convenience
QualifiedNameCandidate: typing.TypeAlias = QualifiedName | str | Identifier
OptionalID: typing.TypeAlias = QualifiedNameCandidate | None
EntityRef: typing.TypeAlias = Union["ProvEntity", QualifiedNameCandidate]
ActivityRef: typing.TypeAlias = Union["ProvActivity", QualifiedNameCandidate]
AgentRef: typing.TypeAlias = Union[
    "ProvAgent", "ProvEntity", "ProvActivity", QualifiedNameCandidate
]
InfluencerRef: typing.TypeAlias = EntityRef | ActivityRef | AgentRef
GenerationRef: typing.TypeAlias = Union["ProvGeneration", QualifiedNameCandidate]
UsageRef: typing.TypeAlias = Union["ProvUsage", QualifiedNameCandidate]
NameValuePair: typing.TypeAlias = tuple[QualifiedName, Any]
AttributePair: typing.TypeAlias = tuple[QualifiedNameCandidate, Any]
DatetimeOrStr: typing.TypeAlias = datetime.datetime | str
NSCollection: typing.TypeAlias = Mapping[str, str] | Iterable[Namespace]
PathLike: typing.TypeAlias = str | bytes | os.PathLike[str]
StreamOrPath: typing.TypeAlias = io.IOBase | IO[Any] | PathLike


# Data Types
_XSD_DATETIME_RE = re.compile(XSD_DATETIME_PATTERN)
_XSD_HOUR24_RE = re.compile(r"T24:00:00(\.0+)?(?=$|[Z+-])")


def _ensure_datetime(value: DatetimeOrStr | None) -> datetime.datetime | None:
    """Coerce a value to a :class:`datetime.datetime`.

    A string is parsed with :func:`parse_xsd_datetime`; a
    :class:`~datetime.datetime` or ``None`` is returned unchanged.

    Raises:
        ProvException: If a string value is not a valid ``xsd:dateTime``.
    """
    if isinstance(value, str):
        parsed = parse_xsd_datetime(value)
        if parsed is None:
            raise ProvException(f"Invalid xsd:dateTime value: {value!r}")
        return parsed
    return value


def parse_xsd_datetime(value: str) -> datetime.datetime | None:
    """Parse an ``xsd:dateTime`` string into a :class:`datetime.datetime`.

    Accepts the ``xsd:dateTime`` lexical space (XSD 1.1 section 3.3.7) and
    nothing else: a date, ``T``, a time with optional fractional seconds,
    and ``Z`` or an ``hh:mm`` offset. The hour-24 end-of-day form maps to
    00:00:00 of the following day, per the XSD value space. Text in another
    ISO 8601 form, such as ``2012-12-03T21:08Z`` or a week date, and a bare
    ``xsd:date`` are not accepted.

    Args:
        value: The date/time string to parse.

    Returns:
        The parsed :class:`~datetime.datetime`, or ``None`` if ``value``
        could not be parsed.
    """
    text = value.strip()
    if not _XSD_DATETIME_RE.fullmatch(text):
        return None
    end_of_day = _XSD_HOUR24_RE.search(text) is not None
    if end_of_day:
        text = _XSD_HOUR24_RE.sub("T00:00:00", text)
    try:
        parsed = datetime.datetime.fromisoformat(text)
        if end_of_day:
            parsed += datetime.timedelta(days=1)
    except (ValueError, OverflowError):
        return None
    return parsed


def parse_boolean(value: str) -> bool | None:
    """Parse an ``xsd:boolean`` string into a Python :class:`bool`.

    Args:
        value: The string to interpret; ``"false"``/``"0"`` map to ``False``
            and ``"true"``/``"1"`` map to ``True`` (case-insensitively).

    Returns:
        The parsed boolean, or ``None`` if ``value`` is not a recognised
        boolean literal.
    """
    if value.lower() in ("false", "0"):
        return False
    elif value.lower() in ("true", "1"):
        return True
    else:
        return None


DATATYPE_PARSERS = {
    datetime.datetime: parse_xsd_datetime,
}


# Mappings for XSD datatypes to Python standard types
SupportedXSDParsedTypes: typing.TypeAlias = (
    str | datetime.datetime | float | int | bool | None
)
XSD_DATATYPE_PARSERS: dict[QualifiedName, Callable[[str], SupportedXSDParsedTypes]] = {
    XSD_STRING: str,
    XSD_DOUBLE: float,
    XSD_LONG: int,
    XSD_INT: int,
    XSD_INTEGER: int,
    XSD_BOOLEAN: parse_boolean,
    XSD_DATETIME: parse_xsd_datetime,
}


_INT32_MAX = 2**31 - 1
_INT64_MAX = 2**63 - 1


def canonical_xsd_datatype(value: object) -> QualifiedName | None:
    """Return the XSD datatype `prov` asserts for a plain Python value.

    This is the single source of truth for the serializers' reverse maps:
    a typed ``Literal`` may be collapsed to a plain Python value only when
    the value's canonical datatype equals the asserted one (a lossless
    collapse), and serializers emit exactly this datatype for plain values.

    Returns ``None`` for values that serialize natively (str, bool,
    datetime — each format handles those itself).
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


def parse_xsd_types(value: str, datatype: QualifiedName) -> SupportedXSDParsedTypes:
    """Parse a string into a Python value according to its XSD datatype.

    Args:
        value: The lexical string value to parse.
        datatype: The qualified name of the XSD datatype (e.g. ``xsd:int``).

    Returns:
        The parsed value in the corresponding Python type, or ``None`` if
        ``datatype`` has no registered parser in :data:`XSD_DATATYPE_PARSERS`.
    """
    return (
        XSD_DATATYPE_PARSERS[datatype](value)
        if datatype in XSD_DATATYPE_PARSERS
        else None
    )


def first(a_set: Iterable[Any]) -> Any | None:
    """Return the first element of an iterable, or ``None`` if it is empty.

    Every in-package caller passes a per-attribute :class:`TypedValueSet`
    (dict-backed, insertion-ordered), so this deterministically returns the
    first-inserted value -- e.g. for ``args``/``formal_attributes``,
    :meth:`ProvActivity.get_startTime`/``get_endTime``, the single-value
    cardinality guard in :meth:`ProvRecord.add_attributes`, and the
    PROV-JSON encoder's single-value case. This is a change from 2.x, where
    the equivalent plain-``set`` storage made "first" an arbitrary
    hash-bucket-order element rather than an insertion-order one (#34).
    """
    return next(iter(a_set), None)


class TypedValueSet(MutableSet[Any]):
    """A set-like container that keeps one value per :func:`_value_key`.

    Backs each attribute's value collection on :class:`ProvRecord`; internal,
    not exported from :mod:`prov.model`. A plain :class:`set` keys on Python
    equality, so it cannot hold both ``2`` and ``2.0`` or both ``1`` and
    ``True`` (#34). This container keys on the value key, the datatype and
    the value in that datatype's value space: ``2`` and ``2.0`` are two
    values, while ``5`` and ``Literal("05", XSD_INT)``, two ``xsd:decimal``
    literals spelled differently (#77) and two tagged strings whose tags
    differ in case (#259) are one each. The first value added for a key is
    kept, as :meth:`ProvRecord.add_attributes`'s cardinality guard keeps the
    first value it sees.

    The retained values are observable through :attr:`ProvRecord.attributes`
    and :attr:`ProvRecord.extra_attributes` (plain ``(name, value)`` tuples),
    record equality and hashing, and serialization.
    :meth:`ProvRecord.get_attribute`, :meth:`ProvRecord.get_asserted_types`
    and :attr:`ProvRecord.value` return a fresh plain ``set`` (their 2.x
    type), so a pair this container keeps apart may collapse in that copy;
    see ``docs/upgrading-3.0.md``. Compares equal to a plain ``set`` or
    ``frozenset`` holding the same elements (the :class:`collections.abc.Set`
    mixin), is unhashable like a plain ``set``, and iterates in insertion
    order.
    """

    __slots__ = ("_index",)

    def __init__(self, iterable: Iterable[Any] = ()) -> None:
        self._index: dict[ValueKey, Any] = {}
        for value in iterable:
            self.add(value)

    def add(self, value: Any) -> None:
        # setdefault keeps the incumbent for a key already held.
        self._index.setdefault(_value_key(value), value)

    def discard(self, value: Any) -> None:
        self._index.pop(_value_key(value), None)

    def __contains__(self, value: object) -> bool:
        return _value_key(value) in self._index

    def keys(self) -> KeysView[ValueKey]:
        """The value keys held, one per retained value."""
        return self._index.keys()

    def __setstate__(self, state: Any) -> None:
        # A 3.2.x pickle keyed the index by (type, value); rebuild by value key.
        self._index = {}
        for value in _slot_state(state)["_index"].values():
            self.add(value)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._index.values())

    def __len__(self) -> int:
        return len(self._index)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self._index.values())!r})"


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


def encoding_provn_value(
    value: str | datetime.datetime | float | bool | int | QualifiedName,
) -> str:
    """Return the PROV-N literal representation of a Python value.

    Strings are quoted (triple-quoted when they span multiple lines); dates
    are rendered with their XSD datatype suffix and booleans as ``"true"``/``"false"``
    with theirs. Floats are rendered as full-precision ``xsd:double`` (#251). Plain ints are typed by
    magnitude: within +/-(2**31-1) they render as a bare ``INT_LITERAL`` (PROV-N
    [60] sugar for ``xsd:int``); beyond that they carry an explicit
    ``xsd:long``/``xsd:integer`` suffix (#249). Any other value is rendered
    via :func:`str`.
    """
    if isinstance(value, str):
        return _provn_string_literal(value)
    elif isinstance(value, datetime.datetime):
        return f'"{_xsd_datetime_text(value)}" %% xsd:dateTime'
    elif isinstance(value, float):
        return f'"{_xsd_double_text(value)}" %% xsd:double'
    elif isinstance(value, bool):
        # Before the int branch: bool is an int subtype. "true"/"false" is
        # the lexical form every other PROV-N producer writes.
        return f'"{"true" if value else "false"}" %% xsd:boolean'
    elif isinstance(value, int):
        datatype = canonical_xsd_datatype(value)
        if datatype == XSD_INT:
            return str(value)  # bare INT_LITERAL is xsd:int sugar (PROV-N [60])
        return f'"{value}" %% {datatype}'
    else:
        # TODO: QName export
        return str(value)


def _check_langtag(value: Any, langtag: Any) -> None:
    """Raise for a language tag that is empty or not shaped like a BCP 47 tag (#472).

    ``Literal.__init__`` and ``Literal.__setstate__`` both check.
    """
    if langtag is not None and not _LANGTAG.fullmatch(str(langtag)):
        raise ProvValueError(
            f"the language tag {langtag!r} of {value!r} is not a BCP 47 tag"
            if langtag
            else f"the language tag of {value!r} is empty"
        )


class Literal:
    """A typed (and optionally language-tagged) PROV literal value.

    A literal pairs a string value with an optional datatype and an optional
    language tag. Supplying a language tag forces the datatype to
    ``prov:InternationalizedString``: if no datatype was given one is assumed,
    and any other datatype is overridden (with a warning) to comply with the
    PROV-JSON/PROV-XML rules for language-tagged strings.
    """

    __slots__ = ("__weakref__", "_datatype", "_langtag", "_value")

    # These fields are assign-once. They take part in equality and hashing,
    # so reassigning one after the object has been used as a set member or
    # dict key corrupts that container. #444 tracks the runtime guard.
    _value: Final[str]
    _datatype: Final[QualifiedName | None]
    _langtag: Final[str | None]

    def __init__(
        self,
        value: Any,
        datatype: QualifiedName | None = None,
        langtag: str | None = None,
    ):
        """Initialise the literal.

        Args:
            value: The literal's value; it is stored as its string form.
            datatype: The qualified name of the value's datatype (default:
                ``None``).
            langtag: An optional language tag. When given, ``datatype`` is
                coerced to ``prov:InternationalizedString`` (default: ``None``).
                An empty tag, or a tag such as ``"en_US"`` that is not shaped
                like a BCP 47 tag, raises :class:`~prov.model.ProvValueError`.
        """
        self._value = str(value)  # value is always a string
        _check_langtag(self._value, langtag)
        if langtag:
            if datatype is None:
                logger.debug(
                    "Assuming prov:InternationalizedString as the type of "
                    f'"{value}"@{langtag}'
                )
                datatype = PROV_INTERNATIONALIZEDSTRING
            # PROV JSON states that the type field must not be set when
            # using the lang attribute and PROV XML requires it to be an
            # internationalized string.
            elif datatype != PROV_INTERNATIONALIZEDSTRING:
                logger.warning(
                    f'Invalid data type ({datatype}) for "{value}"@{langtag}, overridden as '
                    "prov:InternationalizedString."
                )
                datatype = PROV_INTERNATIONALIZEDSTRING
        self._datatype = datatype
        # langtag is always a string
        self._langtag = str(langtag) if langtag is not None else None

    def __str__(self) -> str:
        return self.provn_representation()

    def __repr__(self) -> str:
        return f"<Literal: {self.provn_representation()}>"

    def __getstate__(self) -> dict[str, Any]:
        return {
            "_value": self._value,
            "_datatype": self._datatype,
            "_langtag": self._langtag,
        }

    def __setstate__(self, state: Any) -> None:
        # Also accepts the __dict__ state of 3.1.1 pickles and the
        # (dict_state, slot_state) tuple of 3.2.0 pickles.
        state = _slot_state(state)
        object.__setattr__(self, "_value", state["_value"])
        object.__setattr__(self, "_datatype", state["_datatype"])
        object.__setattr__(self, "_langtag", state["_langtag"])
        _check_langtag(self._value, self._langtag)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Literal) and self._key() == other._key()

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        return hash(self._key())

    def _key(self) -> ValueKey:
        """The value key (#527): the datatype; the value in its value space
        when the datatype has one here and the text is in its lexical space,
        otherwise the text; and the case-folded language tag (#259, RDF 1.1
        tags are case-insensitive; the stored tag keeps its case)."""
        value = xsd_value(self._datatype, self._value)
        langtag = self._langtag.casefold() if self._langtag is not None else None
        return (self._datatype, self._value if value is None else value, langtag)

    @property
    def value(self) -> str:
        """The literal's value as a string."""
        return self._value

    @property
    def datatype(self) -> QualifiedName | None:
        """The literal's datatype, or ``None`` if it has none."""
        return self._datatype

    @property
    def langtag(self) -> str | None:
        """The literal's language tag, or ``None`` if it has none."""
        return self._langtag

    def has_no_langtag(self) -> bool:
        """Return ``True`` if the literal has no language tag."""
        return self._langtag is None

    def provn_representation(self) -> str:
        """Return the PROV-N representation of the literal."""
        quoted_value = _provn_string_literal(self._value)
        if self._langtag:
            # a language tag can only go with prov:InternationalizedString.
            return f"{quoted_value}@{self._langtag}"
        return f"{quoted_value} %% {self._datatype!s}"


# Depends on `Literal` and `SupportedXSDParsedTypes` above, so it cannot join
# the "Type aliases for convenience" block near the top of the module.
CoercedAttributeValue: typing.TypeAlias = (
    QualifiedName | datetime.datetime | Literal | SupportedXSDParsedTypes
)

_K_co = TypeVar("_K_co", covariant=True)
_V_co = TypeVar("_V_co", covariant=True)


class _SupportsItems(Protocol[_K_co, _V_co]):
    # `Mapping` is invariant in its key type, so `dict[QualifiedName, str]` is
    # no `Mapping[QualifiedNameCandidate, ...]`. This protocol is covariant in
    # both parameters.

    def items(self) -> AbstractSet[tuple[_K_co, _V_co]]: ...


AttributeValue: typing.TypeAlias = Union[
    "ProvRecord",
    QualifiedName,
    Identifier,
    datetime.datetime,
    Literal,
    SupportedXSDParsedTypes,
    decimal.Decimal,
    datetime.date,
    datetime.time,
    datetime.timedelta,
    uuid.UUID,
    bytes,
    bytearray,
    memoryview,
]
"""A value accepted for a record attribute, before coercion. An ``Identifier``
is stored as an ``xsd:anyURI`` ``Literal``, and a ``Decimal``, ``date``,
``time``, ``timedelta``, ``UUID``, ``bytes``, ``bytearray`` or ``memoryview``
as a ``Literal`` of its XSD datatype (#482)."""

# `Iterable` is absent on purpose. A dict is itself an iterable, so an `Iterable`
# member makes a dict literal's target ambiguous to mypy and breaks its
# inference (#474). Pair values are `Any` because mypy joins the mixed values
# of a prebuilt list to `object`, which no precise type accepts.
RecordAttributesArg: typing.TypeAlias = (
    _SupportsItems[QualifiedNameCandidate, AttributeValue]
    | Sequence[AttributePair]
    | AbstractSet[AttributePair]
    | Iterator[AttributePair]
)


def _attribute_pairs(attributes: RecordAttributesArg) -> Iterable[AttributePair]:
    # `dict` is tested first because it is the common case on the
    # record-construction hot path.
    if isinstance(attributes, dict):
        return attributes.items()
    items = getattr(attributes, "items", None)
    if callable(items):
        return cast("Iterable[AttributePair]", items())
    return cast("Iterable[AttributePair]", attributes)


# Exceptions and warnings
class ProvException(Error):
    """Base class for PROV model exceptions."""


class ProvValueError(ProvException, ValueError):
    """A value a :class:`Literal` or an attribute cannot hold.

    Raised at assertion for a time whose offset is beyond ±14:00 (#513) and
    for a language tag that is empty or not shaped like a BCP 47 tag (#472).
    A subclass of both :class:`ProvException` and :class:`ValueError`, so a
    caller can catch either.
    """


# The key two attribute values share when they are the same value: the
# datatype (or the Python type of a value with no XSD form), the value in its
# value space or the text when it has none, and the case-folded language tag.
ValueKey: typing.TypeAlias = tuple[QualifiedName | type | None, object, str | None]


def _value_key(value: Any) -> ValueKey:
    """The key of an attribute value for equality, hashing and the
    per-attribute value set (#527, #34).

    A plain Python value takes the datatype the writers give it, so ``5`` and
    ``Literal("05", XSD_INT)`` share a key, ``5`` and ``Literal("5",
    XSD_LONG)`` do not (#235), and ``2`` and ``2.0`` do not (#34).
    """
    if isinstance(value, Literal):
        return value._key()
    if isinstance(value, str):
        return (XSD_STRING, value, None)
    if isinstance(value, bool):
        return (XSD_BOOLEAN, value, None)
    if isinstance(value, int):
        return (canonical_xsd_datatype(value), value, None)
    if isinstance(value, float):
        return (XSD_DOUBLE, NAN_KEY if math.isnan(value) else value, None)
    return (type(value), value, None)


class ProvExceptionInvalidQualifiedName(ProvException):
    """Exception for an invalid qualified identifier name."""

    qname = None
    """The invalid qualified name that triggered the exception."""
    detail: str | None = None
    """What is wrong with it, when the name itself does not say."""

    def __init__(self, qname: Any, detail: str | None = None):
        """Initialise the exception.

        Args:
            qname: The invalid qualified name.
            detail: What is wrong with it, such as a local part PROV-N
                cannot write (#524).
        """
        self.qname = qname
        self.detail = detail

    def __str__(self) -> str:
        message = f"Invalid Qualified Name: {self.qname}"
        return message if self.detail is None else f"{message}, {self.detail}"


class ProvUnificationError(ProvException):
    """Raised by :meth:`ProvBundle.unified` when records sharing an
    identifier cannot be merged under PROV-CONSTRAINTS term unification
    (two different concrete values for the same formal attribute, an absent
    value in a non-expandable position against a present one, or records of
    incompatible types).
    """


class ProvElementIdentifierRequired(ProvException):
    """Exception for a missing element identifier."""

    def __str__(self) -> str:
        return "An identifier is missing. All PROV elements require a valid identifier."


# The types of a converted non-formal attribute value that need no check.
# bool is an int, so isinstance() needs only the tuple.
_PLAIN_VALUE_TYPES = frozenset(
    {str, int, bool, float, datetime.datetime, QualifiedName, Literal}
)
_PLAIN_VALUE_BASES = (str, int, float, datetime.datetime, QualifiedName, Literal)


#  PROV records
class ProvRecord:
    """Base class for PROV records."""

    FORMAL_ATTRIBUTES: tuple[QualifiedName, ...] = ()
    """Formal attributes names of this record type, in the expected order."""

    _prov_type: QualifiedName | None = None
    """PROV type of record."""

    def __init__(
        self,
        bundle: ProvBundle,
        identifier: QualifiedName | None,
        attributes: RecordAttributesArg | None = None,
    ):
        """Initialise the record.

        Args:
            bundle: The bundle owning this PROV record.
            identifier: The (unique) identifier of the record.
            attributes: Attributes to associate with the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).
        """
        self._bundle = bundle
        self._identifier = identifier
        self._attributes: dict[QualifiedName, TypedValueSet] = defaultdict(
            TypedValueSet
        )
        if attributes:
            self.add_attributes(attributes)

    def _typed_attributes(self) -> frozenset[tuple[QualifiedName, ValueKey]]:
        """``(name, value key)`` pairs for equality and hashing (#527, #34).

        Two records hold the same attributes when every name carries the same
        values under :func:`_value_key`'s rule: the same datatype and the same
        value in that datatype's value space, so ``5`` and ``Literal("05",
        XSD_INT)`` match and ``2`` and ``2.0`` do not.
        """
        return frozenset(
            (attr_name, key)
            for attr_name, values in self._attributes.items()
            for key in values.keys()  # noqa: SIM118 (the set iterates values)
        )

    def __hash__(self) -> int:
        return hash((self.get_type(), self._identifier, self._typed_attributes()))

    def copy(self) -> ProvRecord:
        """Return an exact copy of this record."""
        return PROV_REC_CLS[self.get_type()](
            self._bundle, self.identifier, self.attributes
        )

    def get_type(self) -> QualifiedName:
        """Return the PROV type of the record.

        Raises:
            NotImplementedError: If the record type is undefined (i.e. on the
                abstract base classes).
        """
        if self._prov_type is not None:
            return self._prov_type
        else:
            raise NotImplementedError("Type not defined for this record.")

    def get_asserted_types(self) -> set[QualifiedName]:
        """Return the set of all asserted PROV types of this record.

        Returns a fresh, plain ``set`` copy (2.x-compatible: mutating it does
        not affect the record). Since ``prov:type`` values are always
        :class:`~prov.identifier.QualifiedName`\\ s -- which never collapse
        under Python equality -- this copy never loses information: unlike
        :meth:`get_attribute`/:attr:`value`, there is no lossy case here.
        """
        return set(self._attributes[PROV_TYPE])

    def add_asserted_type(self, type_identifier: QualifiedName) -> None:
        """Add a PROV type assertion to the record.

        Args:
            type_identifier: The qualified name of the type to assert.
        """
        self._attributes[PROV_TYPE].add(type_identifier)

    def get_attribute(self, attr_name: QualifiedNameCandidate) -> set[Any]:
        """Return the values (if any) for the named attribute.

        Args:
            attr_name: The name of the attribute.

        Returns:
            A fresh, plain ``set`` copy of the values held for the attribute
            (empty if none); mutating it does not affect the record. This
            keeps the 2.x return type: a Python-equal-but-differently-typed
            pair retained on the record (e.g. ``2`` and ``2.0``, #34) still
            collapses to whichever was asserted first in *this copy*, even
            though the record's own storage, :attr:`attributes`/
            :attr:`extra_attributes`, equality/hashing and serialization all
            retain both -- see ``docs/upgrading-3.0.md``.

        Raises:
            ProvExceptionInvalidQualifiedName: If ``attr_name`` cannot be
                resolved to a valid qualified name.
        """
        attr_name_qn = self._bundle.mandatory_valid_qname(attr_name)
        return set(self._attributes[attr_name_qn])

    @property
    def identifier(self) -> QualifiedName | None:
        """The record's identifier, or ``None`` if it has none."""
        return self._identifier

    @property
    def attributes(self) -> list[tuple[QualifiedName, Any]]:
        """All of the record's attributes as a list of ``(name, value)`` pairs.

        Attributes with multiple values appear once per value, so the same name
        may occur more than once.
        """
        return [
            (attr_name, value)
            for attr_name, values in self._attributes.items()
            for value in values
        ]

    @property
    def args(self) -> tuple[Any, ...]:
        """The values of the record's formal attributes, in declaration order.

        Missing formal attributes are represented by ``None``.
        """
        return tuple(
            first(self._attributes[attr_name]) for attr_name in self.FORMAL_ATTRIBUTES
        )

    @property
    def formal_attributes(self) -> tuple[tuple[QualifiedName, Any], ...]:
        """The record's formal attributes as ``(name, value)`` pairs.

        Pairs are in declaration order; a missing attribute has a value of
        ``None``.
        """
        return tuple(
            (attr_name, first(self._attributes[attr_name]))
            for attr_name in self.FORMAL_ATTRIBUTES
        )

    @property
    def extra_attributes(self) -> tuple[tuple[QualifiedName, Any], ...]:
        """The record's non-formal attributes as ``(name, value)`` pairs."""
        return tuple(
            (attr_name, attr_value)
            for attr_name, attr_value in self.attributes
            if attr_name not in self.FORMAL_ATTRIBUTES
        )

    @property
    def bundle(self) -> ProvBundle:
        """The bundle that owns this record."""
        return self._bundle

    @property
    def label(self) -> str:
        """The record's identifying label.

        This is the record's ``prov:label`` attribute if set, otherwise its
        identifier.
        """
        return str(
            first(self._attributes[PROV_LABEL])
            if self._attributes[PROV_LABEL]
            else self._identifier
        )

    @property
    def value(self) -> set[Any]:
        """The set of the record's ``prov:value`` attribute values.

        Returns a fresh, plain ``set`` copy (2.x-compatible); see
        :meth:`get_attribute` for what that means for a Python-equal-but-
        differently-typed pair of ``prov:value`` values (#34).
        """
        return set(self._attributes[PROV_VALUE])

    # Handling attributes
    def _auto_literal_conversion(self, literal: Any, attr: QualifiedName) -> Any:
        # The form a non-formal attribute value of `attr` takes at assertion.

        if isinstance(literal, ProvRecord):
            # Use the QName of the record as the literal
            literal = literal.identifier

        if isinstance(literal, str):
            return str(literal)
        elif isinstance(literal, QualifiedName):
            return self._bundle.valid_qualified_name(literal)
        elif isinstance(literal, Literal) and literal.has_no_langtag():
            if literal.datatype in (PROV_QUALIFIEDNAME, XSD_QNAME):
                # A qualified-name literal resolves by its prefix in this
                # record's bundle, never by compacting an IRI (#516, #553).
                detail = unresolved_name_detail(self._bundle, literal.value, attr=attr)
                if detail is not None:
                    raise ProvExceptionInvalidQualifiedName(literal.value, detail)
                return self._bundle.mandatory_valid_qname(literal.value)
            if literal.datatype:
                return self._convert_typed_literal(literal, literal.datatype)
            # A literal with no datatype nor langtag defined
            # try auto-converting the value
            value = self._auto_literal_conversion(literal.value, attr)
            if value is not None:
                return value
        elif isinstance(literal, Identifier):
            # An IRI value is an xsd:anyURI literal, the form every writer
            # emits for it.
            return Literal(literal.uri, XSD_ANYURI)

        # No conversion possible, return the original value
        return literal

    @staticmethod
    def _convert_typed_literal(literal: Literal, datatype: QualifiedName) -> Any:
        """The Python value of a typed literal, or the literal where it keeps
        its asserted form."""
        # Match the JSON decoding's literal conversion. #522: a lexical form
        # outside the datatype's lexical space keeps the Literal.
        try:
            value = parse_xsd_types(literal.value, datatype)
        except (ValueError, OverflowError):
            return literal
        if value is None:
            return literal
        # #235: only collapse the integer family when it is lossless, i.e.
        # the asserted datatype is the one `prov` would itself infer for the
        # parsed value. Otherwise, keep the Literal so its asserted datatype
        # survives serialization (e.g. Literal("42", XSD_LONG)).
        if (
            datatype in (XSD_LONG, XSD_INT, XSD_INTEGER)
            and canonical_xsd_datatype(value) != datatype
        ):
            return literal
        # No xsd:dateTime has an offset beyond ±14:00, so the text has no
        # datetime value and stays as written (#513).
        if isinstance(value, datetime.datetime) and _offset_beyond_xsd_bound(value):
            return literal
        return value

    @staticmethod
    def _literal_for_python_value(attr: QualifiedName, value: Any) -> Literal:
        """The ``Literal`` prov stores a Python value of ``attr`` as, or
        ``ProvValueError`` when the value has no PROV form (#482)."""
        form = python_value_form(value)
        if form is None:
            raise ProvValueError(no_prov_form_detail(attr, value))
        text, datatype = form
        if text is None:
            raise ProvValueError(
                f"the value {value!r} of {attr} has no {datatype} form"
            )
        return Literal(text, datatype)

    def _coerce_attribute_value(
        self, attr: QualifiedName, original_value: Any
    ) -> CoercedAttributeValue:
        # Normalise `original_value` to the datatype expected for `attr`.
        #
        # Raises:
        #     ProvException: If the value is invalid for `attr`.

        # the branches below bind `value` to different types
        value: CoercedAttributeValue

        if attr in PROV_ATTRIBUTE_QNAMES:
            # Expecting a qualified name
            if isinstance(original_value, ProvRecord):
                # Use the identifier of the record, which must exist, as the value for this attribute
                qname = original_value.identifier
                if qname is None:
                    raise ProvException(
                        f"Invalid value for attribute {attr}: {original_value}."
                        f" The record has no identifier."
                    )
            else:
                qname = original_value
            value = self._bundle.mandatory_valid_qname(qname)
        elif attr in PROV_ATTRIBUTE_LITERALS:
            value = self._coerce_time(attr, original_value)
        else:
            value = self._auto_literal_conversion(original_value, attr)
            if (
                type(value) not in _PLAIN_VALUE_TYPES
                and value is not None
                and not isinstance(value, _PLAIN_VALUE_BASES)
            ):
                value = self._literal_for_python_value(attr, value)

        if isinstance(value, datetime.datetime):
            # In any position, because no writer could emit it as an
            # xsd:dateTime; a typed Literal beyond the bound stayed a Literal.
            detail = time_offset_detail(attr, value)
            if detail is not None:
                raise ProvValueError(detail)
        if value is None:
            raise ProvException(f"Invalid value for attribute {attr}: {original_value}")

        return value

    def _coerce_time(
        self, attr: QualifiedName, original_value: Any
    ) -> datetime.datetime:
        # A time of the statement: a datetime, or a string or xsd:dateTime
        # Literal that parses as one.
        if isinstance(original_value, str):
            value = parse_xsd_datetime(original_value)
        elif (
            isinstance(original_value, Literal)
            and original_value.datatype == XSD_DATETIME
        ):
            value = parse_xsd_datetime(original_value.value)
        else:
            value = original_value
        if not isinstance(value, datetime.datetime):
            raise ProvException(
                f"Invalid value for attribute {attr}: {original_value}. "
                f"Expected a datetime, or a string or xsd:dateTime Literal"
                f" that parses as one."
            )
        return value

    def _store_attribute_value(
        self,
        attr: QualifiedName,
        value: CoercedAttributeValue,
        is_collection: bool,
    ) -> None:
        # Add `value` for `attr`, enforcing single-valued (non-collection)
        # attributes have at most one (distinct) value.
        #
        # Raises:
        #     ProvException: If a second, different value is supplied for a
        #         single-valued (non-collection) attribute.
        #
        # `_attributes` is a defaultdict(TypedValueSet): every code path below
        # ends up subscripting `self._attributes[attr]` at least once (the
        # early-return and raise paths via the guard/`first()`, the fall-through
        # path via `.add()`), so binding it once up front auto-vivifies the
        # entry no earlier than it would have been created anyway.
        existing_values = self._attributes[attr]
        if not is_collection and attr in PROV_ATTRIBUTES and existing_values:
            existing_value = first(existing_values)
            is_not_same_value = True
            # This duplicate-value branch runs at scale in
            # _unified_records()'s merge loop (unified()/flattened() on
            # large documents), where contextlib.suppress()'s per-call
            # context-manager overhead adds up — the plain try/except
            # stays here.
            try:  # noqa: SIM105
                is_not_same_value = value != existing_value
            except TypeError:
                # Cannot compare them
                pass  # consider them different values

            if is_not_same_value:
                raise ProvException(
                    f"Cannot have more than one value for attribute {attr}"
                )
            else:
                # Same value, ignore it
                return

        existing_values.add(value)

    def add_attributes(self, attributes: RecordAttributesArg) -> None:
        """Add attributes to the record.

        Attribute names are resolved to qualified names, and values are
        normalised to the datatype expected for the attribute. ``None`` values
        are skipped.

        Args:
            attributes: The attributes to add, as a mapping keyed by
                qualified-name identifiers, or as a sequence, set or iterator
                of ``(name, value)`` pairs whose names satisfy the same
                condition.

        Raises:
            ProvExceptionInvalidQualifiedName: If an attribute name cannot be
                resolved to a valid qualified name, or a value typed as a
                qualified name does not resolve by its prefix (#516).
            ProvException: If a value is invalid for its attribute, or a
                second, different value is supplied for a single-valued
                (non-collection) attribute.
        """
        if attributes:
            # Two passes follow, so a one-shot iterator is copied first.
            pairs = list(_attribute_pairs(attributes))

            # Check if one of the attributes specifies that the current type
            # is a collection. In that case multiple attributes of the same
            # type are allowed.
            is_collection = any(
                attr_name == PROV_ATTR_COLLECTION for attr_name, _ in pairs
            )

            for attr_name, original_value in pairs:
                if original_value is None:
                    continue

                # make sure the attribute name is valid
                attr = self._bundle.mandatory_valid_qname(attr_name)

                value = self._coerce_attribute_value(attr, original_value)

                self._store_attribute_value(attr, value, is_collection)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ProvRecord):
            return False
        if self.get_type() != other.get_type():
            return False
        if self._identifier and not (self._identifier == other._identifier):
            return False

        return self._typed_attributes() == other._typed_attributes()

    def __str__(self) -> str:
        return self.get_provn()

    def get_provn(self, strict: bool = False) -> str:
        """Return the PROV-N representation of the record.

        Args:
            strict: Write output that parses under the strict PROV-N
                profile. Mention is written ``prov:mentionOf`` instead of
                the bare ``mentionOf`` keyword, and ``alternateOf``,
                ``specializationOf`` and ``hadMember`` are written without
                the identifier or attribute block PROV-N does not give them,
                each dropped with a :class:`~prov.model.ProvWarning` that
                names the record.
        """
        keyword = PROV_N_MAP[self.get_type()]
        identifier = ""
        items: list[str] = []
        if self._identifier:
            bare = self._identifier.provn_bare_representation()
            if self.is_element():
                items.append(bare)
            else:
                identifier = bare
        items.extend(self._provn_formal_items())
        block = self._provn_attribute_block()
        if strict and self.get_type() == PROV_MENTION:
            # The Recommendation grammar has no Mention; PROV-Links writes it
            # as prov:mentionOf. The default keeps the bare keyword ProvToolbox
            # reads (#248).
            keyword = "prov:mentionOf"
        elif strict and self.get_type() in _PROV_N_BARE_RELATIONS:
            # A strict read rejects an identifier or attribute block here, so neither
            # is written (#569).
            written = f"{keyword}({', '.join(items)})"
            if identifier:
                warn(
                    f"strict=True drops the identifier {identifier} of {written},"
                    f" because PROV-N gives {keyword} no identifier"
                )
                identifier = ""
            if block:
                warn(
                    f"strict=True drops the attribute block {block} of {written},"
                    f" because PROV-N gives {keyword} no attribute block"
                )
                block = ""
        if block:
            items.append(block)
        relation_id = f"{identifier}; " if identifier else ""
        return f"{keyword}({relation_id}{', '.join(items)})"

    def _provn_formal_items(self) -> list[str]:
        """The formal attributes in production order, ``-`` where absent."""
        items = []
        for attr in self.FORMAL_ATTRIBUTES:
            values = self._attributes.get(attr)
            if not values:
                items.append("-")
                continue
            value = first(values)  # a formal attribute holds one value
            if isinstance(value, datetime.datetime):
                items.append(_xsd_datetime_text(value))
            elif isinstance(value, QualifiedName):
                items.append(value.provn_bare_representation())
            else:
                items.append(str(value))
        return items

    def _provn_attribute_block(self) -> str:
        """The ``[name=value, ...]`` block of the other attributes, or ``""``."""
        pairs = []
        for attr in self._attributes:
            if attr in self.FORMAL_ATTRIBUTES:
                continue
            for value in self._attributes[attr]:
                try:
                    text = value.provn_representation()
                except AttributeError:
                    text = encoding_provn_value(value)
                pairs.append(f"{attr.provn_bare_representation()}={text}")
        return f"[{', '.join(pairs)}]" if pairs else ""

    def is_element(self) -> bool:
        """Return ``True`` if the record is an element, ``False`` otherwise."""
        return False

    def is_relation(self) -> bool:
        """Return ``True`` if the record is a relation, ``False`` otherwise."""
        return False


#  Abstract classes for elements and relations
class ProvElement(ProvRecord):
    """Provenance Element (nodes in the provenance graph)."""

    _identifier: QualifiedName

    def __init__(
        self,
        bundle: ProvBundle,
        identifier: QualifiedName | None,
        attributes: RecordAttributesArg | None = None,
    ):
        if identifier is None:
            # All types of PROV elements require a valid identifier
            raise ProvElementIdentifierRequired()

        super().__init__(bundle, identifier, attributes)

    @property
    def identifier(self) -> QualifiedName:
        """The element's identifier. Every element has one."""
        return self._identifier

    def is_element(self) -> bool:
        """Return ``True`` if the record is an element, ``False`` otherwise."""
        return True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self._identifier}>"


class ProvRelation(ProvRecord):
    """Provenance Relationship (edge between nodes)."""

    def is_relation(self) -> bool:
        """Return ``True`` if the record is a relation, ``False`` otherwise."""
        return True

    def __repr__(self) -> str:
        identifier = f" {self._identifier}" if self._identifier else ""
        element_1, element_2 = [qname for _, qname in self.formal_attributes[:2]]
        return f"<{self.__class__.__name__}:{identifier} ({element_1}, {element_2})>"


# Component 1: Entities and Activities
class ProvEntity(ProvElement):
    """Provenance Entity element"""

    _prov_type = PROV_ENTITY

    # Convenient assertions that take the current ProvEntity as the first
    # (formal) argument
    def wasGeneratedBy(
        self,
        activity: ActivityRef | None = None,
        time: DatetimeOrStr | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new generation record to this entity.

        Args:
            activity: The activity (or its string identifier) involved in the
                generation (default: ``None``).
            time: Optional time of the generation, as a
                :class:`datetime.datetime` or an ``xsd:dateTime`` string accepted by
                :func:`~prov.model.parse_xsd_datetime` (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.generation(self, activity, time, other_attributes=attributes)
        return self

    def wasInvalidatedBy(
        self,
        activity: ActivityRef | None,
        time: DatetimeOrStr | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new invalidation record for this entity.

        Args:
            activity: The activity (or its string identifier) involved in the
                invalidation; may be ``None``.
            time: Optional time of the invalidation, as a
                :class:`datetime.datetime` or an ``xsd:dateTime`` string accepted by
                :func:`~prov.model.parse_xsd_datetime` (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.invalidation(self, activity, time, other_attributes=attributes)
        return self

    def wasDerivedFrom(
        self,
        usedEntity: EntityRef,
        activity: ActivityRef | None = None,
        generation: GenerationRef | None = None,
        usage: UsageRef | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new derivation record for this entity from a used entity.

        Args:
            usedEntity: The used entity (or its string identifier).
            activity: The activity (or its string identifier) involved in the
                derivation (default: ``None``).
            generation: Optional generation record qualifying the derivation
                through an internal generation (default: ``None``).
            usage: Optional usage record qualifying the derivation through an
                internal usage (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.derivation(
            self, usedEntity, activity, generation, usage, other_attributes=attributes
        )
        return self

    def wasAttributedTo(
        self, agent: AgentRef, attributes: RecordAttributesArg | None = None
    ) -> Self:
        """Create a new attribution record between this entity and an agent.

        Args:
            agent: The agent (or its string identifier) involved in the
                attribution.
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.attribution(self, agent, other_attributes=attributes)
        return self

    def alternateOf(self, alternate2: EntityRef) -> Self:
        """Create a new alternate record between this and another entity.

        Args:
            alternate2: The other entity (or its string identifier).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.alternate(self, alternate2)
        return self

    def specializationOf(self, generalEntity: EntityRef) -> Self:
        """Create a new specialisation record for this from a general entity.

        Args:
            generalEntity: The general entity (or its string identifier).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.specialization(self, generalEntity)
        return self

    def hadMember(self, entity: EntityRef) -> Self:
        """Create a new membership record adding an entity to this collection.

        Args:
            entity: The entity (or its string identifier) to add to the
                collection.

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.membership(self, entity)
        return self

    def wasRevisionOf(
        self,
        usedEntity: EntityRef,
        activity: ActivityRef | None = None,
        generation: GenerationRef | None = None,
        usage: UsageRef | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new revision record for this entity from a used entity.

        Args:
            usedEntity: The original entity (or its string identifier).
            activity: The activity (or its string identifier) involved in the
                revision (default: ``None``).
            generation: Optional generation record qualifying the derivation
                (default: ``None``).
            usage: Optional usage record qualifying the derivation
                (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.revision(
            self, usedEntity, activity, generation, usage, other_attributes=attributes
        )
        return self

    def wasQuotedFrom(
        self,
        usedEntity: EntityRef,
        activity: ActivityRef | None = None,
        generation: GenerationRef | None = None,
        usage: UsageRef | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new quotation record for this entity from a quoted entity.

        Args:
            usedEntity: The quoted entity (or its string identifier).
            activity: The activity (or its string identifier) involved in the
                quotation (default: ``None``).
            generation: Optional generation record qualifying the derivation
                (default: ``None``).
            usage: Optional usage record qualifying the derivation
                (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.quotation(
            self, usedEntity, activity, generation, usage, other_attributes=attributes
        )
        return self

    def hadPrimarySource(
        self,
        usedEntity: EntityRef,
        activity: ActivityRef | None = None,
        generation: GenerationRef | None = None,
        usage: UsageRef | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new primary-source record for this entity.

        Args:
            usedEntity: The primary-source entity (or its string identifier).
            activity: The activity (or its string identifier) involved
                (default: ``None``).
            generation: Optional generation record qualifying the derivation
                (default: ``None``).
            usage: Optional usage record qualifying the derivation
                (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.primary_source(
            self, usedEntity, activity, generation, usage, other_attributes=attributes
        )
        return self

    def mentionOf(self, generalEntity: EntityRef, bundle: EntityRef) -> Self:
        """Create a new mention record of this entity from a general entity.

        Args:
            generalEntity: The general entity (or its string identifier), the
                relationship destination.
            bundle: The bundle (or its string identifier) that the general
                entity is described in.

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.mention(self, generalEntity, bundle)
        return self

    def wasInfluencedBy(
        self,
        influencer: InfluencerRef,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new influence record on this entity by an influencer.

        Args:
            influencer: The influencing entity, activity or agent (or its
                string identifier).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.influence(self, influencer, other_attributes=attributes)
        return self


class ProvActivity(ProvElement):
    """Provenance Activity element."""

    FORMAL_ATTRIBUTES = (PROV_ATTR_STARTTIME, PROV_ATTR_ENDTIME)

    _prov_type = PROV_ACTIVITY

    #  Convenient methods
    def set_time(
        self,
        startTime: datetime.datetime | None = None,
        endTime: datetime.datetime | None = None,
    ) -> None:
        """Set the start and/or end time of this activity.

        Only non-``None`` arguments are applied; the values are stored as
        given (no string parsing is performed here).

        Args:
            startTime: The start time as a :class:`datetime.datetime`
                (default: ``None``).
            endTime: The end time as a :class:`datetime.datetime`
                (default: ``None``).
        """
        if startTime is not None:
            self._attributes[PROV_ATTR_STARTTIME] = TypedValueSet([startTime])
        if endTime is not None:
            self._attributes[PROV_ATTR_ENDTIME] = TypedValueSet([endTime])

    def get_startTime(self) -> datetime.datetime | None:
        """Return the activity's start time, or ``None`` if unset."""
        values = self._attributes[PROV_ATTR_STARTTIME]
        return first(values) if values else None

    def get_endTime(self) -> datetime.datetime | None:
        """Return the activity's end time, or ``None`` if unset."""
        values = self._attributes[PROV_ATTR_ENDTIME]
        return first(values) if values else None

    # Convenient assertions that take the current ProvActivity as the first
    # (formal) argument
    def used(
        self,
        entity: EntityRef,
        time: DatetimeOrStr | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new usage record for this activity.

        Args:
            entity: The entity (or its string identifier) involved in the
                usage relationship.
            time: Optional time of the usage, as a :class:`datetime.datetime`
                or an ``xsd:dateTime`` string accepted by
                :func:`~prov.model.parse_xsd_datetime`
                (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This activity (to allow chaining).
        """
        self._bundle.usage(self, entity, time, other_attributes=attributes)
        return self

    def wasInformedBy(
        self, informant: ActivityRef, attributes: RecordAttributesArg | None = None
    ) -> Self:
        """Create a new communication record for this activity.

        Args:
            informant: The informing activity (relationship source).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This activity (to allow chaining).
        """
        self._bundle.communication(self, informant, other_attributes=attributes)
        return self

    def wasStartedBy(
        self,
        trigger: EntityRef | None,
        starter: ActivityRef | None = None,
        time: DatetimeOrStr | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new start record for this activity.

        The activity did not exist before being started by the trigger.

        Args:
            trigger: The entity triggering the start of this activity; may be
                ``None``.
            starter: Optional activity qualifying the start, through which the
                trigger entity is generated (default: ``None``).
            time: Optional time of the start, as a :class:`datetime.datetime`
                or an ``xsd:dateTime`` string accepted by
                :func:`~prov.model.parse_xsd_datetime`
                (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This activity (to allow chaining).
        """
        self._bundle.start(self, trigger, starter, time, other_attributes=attributes)
        return self

    def wasEndedBy(
        self,
        trigger: EntityRef | None,
        ender: ActivityRef | None = None,
        time: DatetimeOrStr | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new end record for this activity.

        Args:
            trigger: The entity triggering the end of this activity; may be
                ``None``.
            ender: Optional activity qualifying the end, through which the
                trigger entity is generated (default: ``None``).
            time: Optional time of the end, as a :class:`datetime.datetime` or
                an ``xsd:dateTime`` string accepted by
                :func:`~prov.model.parse_xsd_datetime`
                (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This activity (to allow chaining).
        """
        self._bundle.end(self, trigger, ender, time, other_attributes=attributes)
        return self

    def wasAssociatedWith(
        self,
        agent: AgentRef,
        plan: EntityRef | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new association record for this activity.

        Args:
            agent: The agent (or its string identifier) involved in the
                association.
            plan: Optional entity qualifying the association through an
                internal plan (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This activity (to allow chaining).
        """
        self._bundle.association(self, agent, plan, other_attributes=attributes)
        return self

    def wasInfluencedBy(
        self,
        influencer: InfluencerRef,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new influence record on this activity by an influencer.

        Args:
            influencer: The influencing entity, activity or agent (or its
                string identifier).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This activity (to allow chaining).
        """
        self._bundle.influence(self, influencer, other_attributes=attributes)
        return self


class ProvGeneration(ProvRelation):
    """Provenance Generation relationship."""

    FORMAL_ATTRIBUTES = (PROV_ATTR_ENTITY, PROV_ATTR_ACTIVITY, PROV_ATTR_TIME)

    _prov_type = PROV_GENERATION


class ProvUsage(ProvRelation):
    """Provenance Usage relationship."""

    FORMAL_ATTRIBUTES = (PROV_ATTR_ACTIVITY, PROV_ATTR_ENTITY, PROV_ATTR_TIME)

    _prov_type = PROV_USAGE


class ProvCommunication(ProvRelation):
    """Provenance Communication relationship."""

    FORMAL_ATTRIBUTES = (PROV_ATTR_INFORMED, PROV_ATTR_INFORMANT)

    _prov_type = PROV_COMMUNICATION


class ProvStart(ProvRelation):
    """Provenance Start relationship."""

    FORMAL_ATTRIBUTES = (
        PROV_ATTR_ACTIVITY,
        PROV_ATTR_TRIGGER,
        PROV_ATTR_STARTER,
        PROV_ATTR_TIME,
    )

    _prov_type = PROV_START


class ProvEnd(ProvRelation):
    """Provenance End relationship."""

    FORMAL_ATTRIBUTES = (
        PROV_ATTR_ACTIVITY,
        PROV_ATTR_TRIGGER,
        PROV_ATTR_ENDER,
        PROV_ATTR_TIME,
    )

    _prov_type = PROV_END


class ProvInvalidation(ProvRelation):
    """Provenance Invalidation relationship."""

    FORMAL_ATTRIBUTES = (PROV_ATTR_ENTITY, PROV_ATTR_ACTIVITY, PROV_ATTR_TIME)

    _prov_type = PROV_INVALIDATION


# Component 2: Derivations
class ProvDerivation(ProvRelation):
    """Provenance Derivation relationship."""

    FORMAL_ATTRIBUTES = (
        PROV_ATTR_GENERATED_ENTITY,
        PROV_ATTR_USED_ENTITY,
        PROV_ATTR_ACTIVITY,
        PROV_ATTR_GENERATION,
        PROV_ATTR_USAGE,
    )

    _prov_type = PROV_DERIVATION


# Component 3: Agents, Responsibility, and Influence
class ProvAgent(ProvElement):
    """Provenance Agent element."""

    _prov_type = PROV_AGENT

    # Convenient assertions that take the current ProvAgent as the first
    # (formal) argument
    def actedOnBehalfOf(
        self,
        responsible: AgentRef,
        activity: ActivityRef | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new delegation record on behalf of this agent.

        Args:
            responsible: The agent (or its string identifier) that the
                responsibility is delegated to.
            activity: Optional activity qualifying the delegation
                (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This agent (to allow chaining).
        """
        self._bundle.delegation(
            self, responsible, activity, other_attributes=attributes
        )
        return self

    def wasInfluencedBy(
        self,
        influencer: InfluencerRef,
        attributes: RecordAttributesArg | None = None,
    ) -> Self:
        """Create a new influence record on this agent by an influencer.

        Args:
            influencer: The influencing entity, activity or agent (or its
                string identifier).
            attributes: Optional extra attributes for the record, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This agent (to allow chaining).
        """
        self._bundle.influence(self, influencer, other_attributes=attributes)
        return self


class ProvAttribution(ProvRelation):
    """Provenance Attribution relationship."""

    FORMAL_ATTRIBUTES = (PROV_ATTR_ENTITY, PROV_ATTR_AGENT)

    _prov_type = PROV_ATTRIBUTION


class ProvAssociation(ProvRelation):
    """Provenance Association relationship."""

    FORMAL_ATTRIBUTES = (PROV_ATTR_ACTIVITY, PROV_ATTR_AGENT, PROV_ATTR_PLAN)

    _prov_type = PROV_ASSOCIATION


class ProvDelegation(ProvRelation):
    """Provenance Delegation relationship."""

    FORMAL_ATTRIBUTES = (PROV_ATTR_DELEGATE, PROV_ATTR_RESPONSIBLE, PROV_ATTR_ACTIVITY)

    _prov_type = PROV_DELEGATION


class ProvInfluence(ProvRelation):
    """Provenance Influence relationship."""

    FORMAL_ATTRIBUTES = (PROV_ATTR_INFLUENCEE, PROV_ATTR_INFLUENCER)

    _prov_type = PROV_INFLUENCE


# Component 5: Alternate Entities
class ProvSpecialization(ProvRelation):
    """Provenance Specialization relationship."""

    FORMAL_ATTRIBUTES: tuple[QualifiedName, ...] = (
        PROV_ATTR_SPECIFIC_ENTITY,
        PROV_ATTR_GENERAL_ENTITY,
    )

    _prov_type = PROV_SPECIALIZATION


class ProvAlternate(ProvRelation):
    """Provenance Alternate relationship."""

    FORMAL_ATTRIBUTES = (PROV_ATTR_ALTERNATE1, PROV_ATTR_ALTERNATE2)

    _prov_type = PROV_ALTERNATE


class ProvMention(ProvSpecialization):
    """Provenance Mention relationship (specific Specialization)."""

    FORMAL_ATTRIBUTES = (
        PROV_ATTR_SPECIFIC_ENTITY,
        PROV_ATTR_GENERAL_ENTITY,
        PROV_ATTR_BUNDLE,
    )

    _prov_type = PROV_MENTION


# Component 6: Collections
class ProvMembership(ProvRelation):
    """Provenance Membership relationship."""

    FORMAL_ATTRIBUTES = (PROV_ATTR_COLLECTION, PROV_ATTR_ENTITY)

    _prov_type = PROV_MEMBERSHIP


#  Class mappings from PROV record type
PROV_REC_CLS = {
    PROV_ENTITY: ProvEntity,
    PROV_ACTIVITY: ProvActivity,
    PROV_GENERATION: ProvGeneration,
    PROV_USAGE: ProvUsage,
    PROV_COMMUNICATION: ProvCommunication,
    PROV_START: ProvStart,
    PROV_END: ProvEnd,
    PROV_INVALIDATION: ProvInvalidation,
    PROV_DERIVATION: ProvDerivation,
    PROV_AGENT: ProvAgent,
    PROV_ATTRIBUTION: ProvAttribution,
    PROV_ASSOCIATION: ProvAssociation,
    PROV_DELEGATION: ProvDelegation,
    PROV_INFLUENCE: ProvInfluence,
    PROV_SPECIALIZATION: ProvSpecialization,
    PROV_ALTERNATE: ProvAlternate,
    PROV_MENTION: ProvMention,
    PROV_MEMBERSHIP: ProvMembership,
}
