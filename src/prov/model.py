"""Python implementation of the W3C Provenance Data Model (PROV-DM), including
support for PROV-JSON import/export

References:

PROV-DM: http://www.w3.org/TR/prov-dm/
PROV-JSON: https://openprovenance.org/prov-json/
"""

from __future__ import annotations  # needed for | type annotations in Python < 3.10

import datetime
import io
import itertools
import logging
import os
import shutil
import tempfile
import typing  # noqa: F401 -- used by `# type: typing.TypeAlias` comments below
from collections import defaultdict
from collections.abc import Callable, Iterable
from io import IOBase
from typing import (
    Any,
    Union,
)
from urllib.parse import urlparse

import dateutil.parser

from prov import Error, serializers
from prov.constants import *
from prov.identifier import (
    Identifier as Identifier,
    Namespace as Namespace,
    QualifiedName as QualifiedName,
)

__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"


logger = logging.getLogger(__name__)


# Type aliases for convenience
QualifiedNameCandidate = QualifiedName | str | Identifier  # type: typing.TypeAlias
OptionalID = QualifiedNameCandidate | None  # type: typing.TypeAlias
EntityRef = Union["ProvEntity", QualifiedNameCandidate]  # type: typing.TypeAlias
ActivityRef = Union["ProvActivity", QualifiedNameCandidate]  # type: typing.TypeAlias
AgentRef = Union["ProvAgent", "ProvEntity", "ProvActivity", QualifiedNameCandidate]  # type: typing.TypeAlias
GenrationRef = Union["ProvGeneration", QualifiedNameCandidate]  # type: typing.TypeAlias
UsageRef = Union["ProvUsage", QualifiedNameCandidate]  # type: typing.TypeAlias
RecordAttributesArg = (
    dict[QualifiedNameCandidate, Any] | Iterable[tuple[QualifiedNameCandidate, Any]]
)  # type: typing.TypeAlias
NameValuePair = tuple[QualifiedName, Any]  # type: typing.TypeAlias
DatetimeOrStr = datetime.datetime | str  # type: typing.TypeAlias
NSCollection = dict[str, str] | Iterable[Namespace]  # type: typing.TypeAlias
PathLike = str | bytes | os.PathLike[str]  # type: typing.TypeAlias


# Data Types
def _ensure_datetime(value: DatetimeOrStr | None) -> datetime.datetime | None:
    """Coerce a value to a :class:`datetime.datetime`.

    A string is parsed with :func:`dateutil.parser.parse`; a
    :class:`~datetime.datetime` or ``None`` is returned unchanged.
    """
    if isinstance(value, str):
        return dateutil.parser.parse(value)
    else:
        return value


def parse_xsd_datetime(value: str) -> datetime.datetime | None:
    """Parse an ``xsd:dateTime`` string into a :class:`datetime.datetime`.

    Args:
        value: The date/time string to parse.

    Returns:
        The parsed :class:`~datetime.datetime`, or ``None`` if ``value`` could
        not be parsed.
    """
    try:
        return dateutil.parser.parse(value)
    except ValueError:
        pass
    return None


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
SupportedXSDParsedTypes = (
    str | datetime.datetime | float | int | bool | Identifier | None
)  # type: typing.TypeAlias
XSD_DATATYPE_PARSERS: dict[QualifiedName, Callable[[str], SupportedXSDParsedTypes]] = {
    XSD_STRING: str,
    XSD_DOUBLE: float,
    XSD_LONG: int,
    XSD_INT: int,
    XSD_BOOLEAN: parse_boolean,
    XSD_DATETIME: parse_xsd_datetime,
    XSD_ANYURI: Identifier,
}


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


def first(a_set: set[Any]) -> Any | None:
    """Return an arbitrary element from a set, or ``None`` if it is empty."""
    return next(iter(a_set), None)


def _ensure_multiline_string_triple_quoted(value: str) -> str:
    # converting the value to a string
    s = str(value)
    # Escaping any double quote
    s = s.replace('"', '\\"')
    if "\n" in s:
        return f'"""{s}"""'
    else:
        return f'"{s}"'


def encoding_provn_value(
    value: str | datetime.datetime | float | bool | QualifiedName,
) -> str:
    """Return the PROV-N literal representation of a Python value.

    Strings are quoted (triple-quoted when they span multiple lines); dates,
    floats and booleans are rendered with their XSD datatype suffix. Any other
    value is rendered via :func:`str`.
    """
    if isinstance(value, str):
        return _ensure_multiline_string_triple_quoted(value)
    elif isinstance(value, datetime.datetime):
        return f'"{value.isoformat()}" %% xsd:dateTime'
    elif isinstance(value, float):
        return f'"{value:g}" %% xsd:float'
    elif isinstance(value, bool):
        # bool is an int subtype, so :d renders "1"/"0" (not "True"/"False")
        return f'"{value:d}" %% xsd:boolean'
    else:
        # TODO: QName export
        return str(value)


class Literal:
    """A typed (and optionally language-tagged) PROV literal value.

    A literal pairs a string value with an optional datatype and an optional
    language tag. Supplying a language tag forces the datatype to
    ``prov:InternationalizedString``: if no datatype was given one is assumed,
    and any other datatype is overridden (with a warning) to comply with the
    PROV-JSON/PROV-XML rules for language-tagged strings.
    """

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
        """
        self._value: str = str(value)  # value is always a string
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
        self._datatype: QualifiedName | None = datatype
        # langtag is always a string
        self._langtag: str | None = str(langtag) if langtag is not None else None

    def __str__(self) -> str:
        return self.provn_representation()

    def __repr__(self) -> str:
        return f"<Literal: {self.provn_representation()}>"

    def __eq__(self, other: Any) -> bool:
        return (
            (
                self._value == other.value
                and self._datatype == other.datatype
                and self._langtag == other.langtag
            )
            if isinstance(other, Literal)
            else False
        )

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        return hash((self._value, self._datatype, self._langtag))

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
        quoted_value = _ensure_multiline_string_triple_quoted(self._value)
        if self._langtag:
            # a language tag can only go with prov:InternationalizedString
            return f"{quoted_value}@{self._langtag!s}"
        else:
            return f"{quoted_value} %% {self._datatype!s}"


# Exceptions and warnings
class ProvException(Error):
    """Base class for PROV model exceptions."""

    pass


class ProvWarning(Warning):
    """Base class for PROV model warnings."""

    pass


class ProvExceptionInvalidQualifiedName(ProvException):
    """Exception for an invalid qualified identifier name."""

    qname = None
    """The invalid qualified name that triggered the exception."""

    def __init__(self, qname: Any):
        """Initialise the exception.

        Args:
            qname: The invalid qualified name.
        """
        self.qname = qname

    def __str__(self) -> str:
        return f"Invalid Qualified Name: {self.qname}"


class ProvElementIdentifierRequired(ProvException):
    """Exception for a missing element identifier."""

    def __str__(self) -> str:
        return "An identifier is missing. All PROV elements require a valid identifier."


#  PROV records
class ProvRecord:
    """Base class for PROV records."""

    FORMAL_ATTRIBUTES = ()  # type: tuple[QualifiedName, ...]
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
                an iterable of ``(name, value)`` pairs (default: ``None``).
        """
        self._bundle = bundle
        self._identifier = identifier
        self._attributes: dict[QualifiedName, set[Any]] = defaultdict(set)
        if attributes:
            self.add_attributes(attributes)

    def __hash__(self) -> int:
        return hash((self.get_type(), self._identifier, frozenset(self.attributes)))

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
        """Return the set of all asserted PROV types of this record."""
        return self._attributes[PROV_TYPE]

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
            The set of values held for the attribute (empty if none).

        Raises:
            ProvExceptionInvalidQualifiedName: If ``attr_name`` cannot be
                resolved to a valid qualified name.
        """
        attr_name_qn = self._bundle.mandatory_valid_qname(attr_name)
        return self._attributes[attr_name_qn]

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
    def value(self) -> Any:
        """The set of the record's ``prov:value`` attribute values."""
        return self._attributes[PROV_VALUE]

    # Handling attributes
    def _auto_literal_conversion(self, literal: Any) -> Any:
        # This method normalise datatype for literals

        if isinstance(literal, ProvRecord):
            # Use the QName of the record as the literal
            literal = literal.identifier

        if isinstance(literal, str):
            return str(literal)
        elif isinstance(literal, QualifiedName):
            return self._bundle.valid_qualified_name(literal)
        elif isinstance(literal, Literal) and literal.has_no_langtag():
            if literal.datatype:
                # try to convert a generic Literal object to Python standard type
                # to match the JSON decoding's literal conversion
                value = parse_xsd_types(literal.value, literal.datatype)
            else:
                # A literal with no datatype nor langtag defined
                # try auto-converting the value
                value = self._auto_literal_conversion(literal.value)
            if value is not None:
                return value

        # No conversion possible, return the original value
        return literal

    def add_attributes(self, attributes: RecordAttributesArg) -> None:
        """Add attributes to the record.

        Attribute names are resolved to qualified names, and values are
        normalised to the datatype expected for the attribute. ``None`` values
        are skipped.

        Args:
            attributes: The attributes to add, either as a dict keyed by
                qualified-name identifiers or an iterable of ``(name, value)``
                pairs whose names satisfy the same condition.

        Raises:
            ProvExceptionInvalidQualifiedName: If an attribute name cannot be
                resolved to a valid qualified name.
            ProvException: If a value is invalid for its attribute, or a
                second, different value is supplied for a single-valued
                (non-collection) attribute.
        """
        if attributes:
            if isinstance(attributes, dict):
                # Converting the dictionary into a list of tuples
                # (i.e. attribute-value pairs)
                attributes = attributes.items()

            # Check if one of the attributes specifies that the current type
            # is a collection. In that case multiple attributes of the same
            # type are allowed.
            is_collection = any(
                attr_name == PROV_ATTR_COLLECTION for attr_name, _ in attributes
            )

            for attr_name, original_value in attributes:
                if original_value is None:
                    continue

                # make sure the attribute name is valid
                attr = self._bundle.mandatory_valid_qname(attr_name)

                # the branches below bind `value` to different types
                value: (
                    QualifiedName
                    | datetime.datetime
                    | Literal
                    | SupportedXSDParsedTypes
                )

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
                    # Expecting a datetime object or a string that can be parsed as a datetime
                    if isinstance(original_value, str):
                        value = parse_xsd_datetime(original_value)
                    else:
                        value = original_value
                    if not isinstance(value, datetime.datetime):
                        raise ProvException(
                            f"Invalid value for attribute {attr}: {original_value}. "
                            f"Expected a datetime object or a string that can be parsed"
                            f" as a datetime."
                        )
                else:
                    value = self._auto_literal_conversion(original_value)

                if value is None:
                    raise ProvException(
                        f"Invalid value for attribute {attr}: {original_value}"
                    )

                if (
                    not is_collection
                    and attr in PROV_ATTRIBUTES
                    and self._attributes[attr]
                ):
                    existing_value = first(self._attributes[attr])
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
                        continue

                self._attributes[attr].add(value)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ProvRecord):
            return False
        if self.get_type() != other.get_type():
            return False
        if self._identifier and not (self._identifier == other._identifier):
            return False

        return set(self.attributes) == set(other.attributes)

    def __str__(self) -> str:
        return self.get_provn()

    def get_provn(self) -> str:
        """Return the PROV-N representation of the record."""
        items = []

        # Generating identifier
        relation_id = ""  # default blank
        if self._identifier:
            identifier = str(self._identifier)  # TODO: QName export
            if self.is_element():
                items.append(identifier)
            else:
                # this is a relation, which relation uses a semicolon to separate identifiers
                relation_id = identifier + "; "

        # Writing out the formal attributes
        for attr in self.FORMAL_ATTRIBUTES:
            values = self._attributes.get(attr)
            if values:
                # Formal attributes always have single values
                value = first(values)
                # TODO: QName export
                items.append(
                    value.isoformat()
                    if isinstance(value, datetime.datetime)
                    else str(value)
                )
            else:
                items.append("-")

        # Writing out the remaining attributes
        extra = []
        for attr in self._attributes:
            if attr not in self.FORMAL_ATTRIBUTES:
                for value in self._attributes[attr]:
                    try:
                        # try if there is a prov-n representation defined
                        provn_represenation = value.provn_representation()
                    except AttributeError:
                        provn_represenation = encoding_provn_value(value)
                    # TODO: QName export
                    extra.append(f"{attr!s}={provn_represenation}")

        if extra:
            # .format(), not an f-string: the nested string literals reuse the
            # same quote character, which f-strings only allow from py3.12 (PEP 701)
            items.append("[{}]".format(", ".join(extra)))
        prov_n = "{}({}{})".format(
            PROV_N_MAP[self.get_type()],
            relation_id,
            ", ".join(items),
        )
        return prov_n

    def is_element(self) -> bool:
        """Return ``True`` if the record is an element, ``False`` otherwise."""
        return False

    def is_relation(self) -> bool:
        """Return ``True`` if the record is a relation, ``False`` otherwise."""
        return False


#  Abstract classes for elements and relations
class ProvElement(ProvRecord):
    """Provenance Element (nodes in the provenance graph)."""

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
    ) -> ProvEntity:
        """Create a new generation record to this entity.

        Args:
            activity: The activity (or its string identifier) involved in the
                generation (default: ``None``).
            time: Optional time of the generation, as a
                :class:`datetime.datetime` or a string parseable by
                :func:`dateutil.parser.parse` (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

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
    ) -> ProvEntity:
        """Create a new invalidation record for this entity.

        Args:
            activity: The activity (or its string identifier) involved in the
                invalidation; may be ``None``.
            time: Optional time of the invalidation, as a
                :class:`datetime.datetime` or a string parseable by
                :func:`dateutil.parser.parse` (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.invalidation(self, activity, time, other_attributes=attributes)
        return self

    def wasDerivedFrom(
        self,
        usedEntity: EntityRef,
        activity: ActivityRef | None = None,
        generation: GenrationRef | None = None,
        usage: UsageRef | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> ProvEntity:
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
                an iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.derivation(
            self, usedEntity, activity, generation, usage, other_attributes=attributes
        )
        return self

    def wasAttributedTo(
        self, agent: AgentRef, attributes: RecordAttributesArg | None = None
    ) -> ProvEntity:
        """Create a new attribution record between this entity and an agent.

        Args:
            agent: The agent (or its string identifier) involved in the
                attribution.
            attributes: Optional extra attributes for the record, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.attribution(self, agent, other_attributes=attributes)
        return self

    def alternateOf(self, alternate2: EntityRef) -> ProvEntity:
        """Create a new alternate record between this and another entity.

        Args:
            alternate2: The other entity (or its string identifier).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.alternate(self, alternate2)
        return self

    def specializationOf(self, generalEntity: EntityRef) -> ProvEntity:
        """Create a new specialisation record for this from a general entity.

        Args:
            generalEntity: The general entity (or its string identifier).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.specialization(self, generalEntity)
        return self

    def hadMember(self, entity: EntityRef) -> ProvEntity:
        """Create a new membership record adding an entity to this collection.

        Args:
            entity: The entity (or its string identifier) to add to the
                collection.

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.membership(self, entity)
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
            self._attributes[PROV_ATTR_STARTTIME] = {startTime}
        if endTime is not None:
            self._attributes[PROV_ATTR_ENDTIME] = {endTime}

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
    ) -> ProvActivity:
        """Create a new usage record for this activity.

        Args:
            entity: The entity (or its string identifier) involved in the
                usage relationship.
            time: Optional time of the usage, as a :class:`datetime.datetime`
                or a string parseable by :func:`dateutil.parser.parse`
                (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This activity (to allow chaining).
        """
        self._bundle.usage(self, entity, time, other_attributes=attributes)
        return self

    def wasInformedBy(
        self, informant: ActivityRef, attributes: RecordAttributesArg | None = None
    ) -> ProvActivity:
        """Create a new communication record for this activity.

        Args:
            informant: The informing activity (relationship source).
            attributes: Optional extra attributes for the record, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

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
    ) -> ProvActivity:
        """Create a new start record for this activity.

        The activity did not exist before being started by the trigger.

        Args:
            trigger: The entity triggering the start of this activity; may be
                ``None``.
            starter: Optional activity qualifying the start, through which the
                trigger entity is generated (default: ``None``).
            time: Optional time of the start, as a :class:`datetime.datetime`
                or a string parseable by :func:`dateutil.parser.parse`
                (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

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
    ) -> ProvActivity:
        """Create a new end record for this activity.

        Args:
            trigger: The entity triggering the end of this activity; may be
                ``None``.
            ender: Optional activity qualifying the end, through which the
                trigger entity is generated (default: ``None``).
            time: Optional time of the end, as a :class:`datetime.datetime` or
                a string parseable by :func:`dateutil.parser.parse`
                (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

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
    ) -> ProvActivity:
        """Create a new association record for this activity.

        Args:
            agent: The agent (or its string identifier) involved in the
                association.
            plan: Optional entity qualifying the association through an
                internal plan (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This activity (to allow chaining).
        """
        self._bundle.association(self, agent, plan, other_attributes=attributes)
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
    ) -> ProvAgent:
        """Create a new delegation record on behalf of this agent.

        Args:
            responsible: The agent (or its string identifier) that the
                responsibility is delegated to.
            activity: Optional activity qualifying the delegation
                (default: ``None``).
            attributes: Optional extra attributes for the record, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This agent (to allow chaining).
        """
        self._bundle.delegation(
            self, responsible, activity, other_attributes=attributes
        )
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

    FORMAL_ATTRIBUTES = (
        PROV_ATTR_SPECIFIC_ENTITY,
        PROV_ATTR_GENERAL_ENTITY,
    )  # type: tuple[QualifiedName, ...]

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


DEFAULT_NAMESPACES = {"prov": PROV, "xsd": XSD, "xsi": XSI}


#  Bundle
class NamespaceManager(dict[str, Namespace]):
    """Manages namespaces for PROV documents and bundles."""

    parent = None  # type: NamespaceManager | None
    """Parent :class:`NamespaceManager` this manager is a child of, if any."""

    def __init__(
        self,
        namespaces: NSCollection | None = None,
        default: str | None = None,
        parent: NamespaceManager | None = None,
    ):
        """Initialise the namespace manager.

        Args:
            namespaces: Optional namespaces to add, as a ``{prefix: uri}`` dict
                or an iterable of :class:`~prov.identifier.Namespace`
                (default: ``None``).
            default: Optional default namespace URI (default: ``None``).
            parent: Optional parent :class:`NamespaceManager` to make this one a
                child of (default: ``None``).
        """
        dict.__init__(self)
        self._default_namespaces = DEFAULT_NAMESPACES
        self.update(self._default_namespaces)
        self._namespaces = {}  # type: dict[str, Namespace]

        if default is not None:
            self.set_default_namespace(default)
        else:
            self._default = None  # type: Namespace | None
        self.parent = parent
        #  TODO check if default is in the default namespaces
        self._anon_id_count = 0
        self._uri_map = {}  # type: dict[str, Namespace]
        self._rename_map = {}  # type: dict[Namespace, Namespace]
        self._prefix_renamed_map = {}  # type: dict[str, Namespace]
        if namespaces is not None:
            self.add_namespaces(namespaces)

    def get_namespace(self, uri: str) -> Namespace | None:
        """Return the known namespace with the given URI.

        Args:
            uri: The namespace URI to look up.

        Returns:
            The matching :class:`~prov.identifier.Namespace`, or ``None`` if no
            known namespace has that URI.
        """
        for namespace in self.values():
            if uri == namespace._uri:
                return namespace
        return None

    def get_registered_namespaces(self) -> Iterable[Namespace]:
        """Return all explicitly registered namespaces.

        Returns:
            An iterable of :class:`~prov.identifier.Namespace`. This excludes
            the default namespaces (``prov``, ``xsd``, ``xsi``).
        """
        return self._namespaces.values()

    def set_default_namespace(self, uri: str) -> None:
        """Set the default namespace to one with the given URI.

        Args:
            uri: The URI of the default namespace.
        """
        self._default = Namespace("", uri)
        self[""] = self._default

    def get_default_namespace(self) -> Namespace | None:
        """Return the default namespace, or ``None`` if none is set."""
        return self._default

    def add_namespace(self, namespace: Namespace) -> Namespace:
        """Add a namespace, unless an equivalent one is already registered.

        If a namespace with the same URI already exists, that existing
        namespace is returned. If the prefix conflicts with a different
        namespace, the added namespace is renamed to an unused prefix.

        Args:
            namespace: The :class:`~prov.identifier.Namespace` to add.

        Returns:
            The registered namespace, which may be the existing or renamed one
            rather than the argument.
        """
        if namespace in self.values():
            #  no need to do anything
            return namespace
        if namespace in self._rename_map:
            #  already renamed and added
            return self._rename_map[namespace]

        # Checking if the URI has been defined and use the existing namespace
        # instead
        uri = namespace.uri
        prefix = namespace.prefix

        if uri in self._uri_map:
            existing_ns = self._uri_map[uri]
            self._rename_map[namespace] = existing_ns
            self._prefix_renamed_map[prefix] = existing_ns
            return existing_ns

        if prefix in self:
            #  Conflicting prefix
            new_prefix = self._get_unused_prefix(prefix)
            new_namespace = Namespace(new_prefix, namespace.uri)
            self._rename_map[namespace] = new_namespace
            # TODO: What if the prefix is already in the map and point to a
            # different Namespace? Raise an exception?
            self._prefix_renamed_map[prefix] = new_namespace
            prefix = new_prefix
            namespace = new_namespace

        # Only now add the namespace to the registry
        self._namespaces[prefix] = namespace
        self[prefix] = namespace
        self._uri_map[uri] = namespace

        return namespace

    def add_namespaces(self, namespaces: NSCollection) -> None:
        """Add multiple namespaces into this manager.

        Args:
            namespaces: The namespaces to add, as a ``{prefix: uri}`` dict or an
                iterable of :class:`~prov.identifier.Namespace`.
        """
        if isinstance(namespaces, dict):
            # expecting a dictionary of {prefix: uri},
            # convert it to a list of Namespace
            namespaces = [Namespace(prefix, uri) for prefix, uri in namespaces.items()]
        if namespaces:
            for ns in namespaces:
                self.add_namespace(ns)

    def valid_qualified_name(
        self, qname: QualifiedNameCandidate
    ) -> QualifiedName | None:
        """Resolve an identifier to a valid qualified name.

        Registers the namespace of the resolved name if it was not registered
        already. Where the identifier is a string or :class:`Identifier`, an
        attempt is made to expand a known prefix or compact a known namespace
        URI, delegating to the parent manager if all local attempts fail.

        Args:
            qname: The candidate to resolve, as a
                :class:`~prov.identifier.QualifiedName`,
                :class:`~prov.identifier.Identifier`, or string.

        Returns:
            The resolved :class:`~prov.identifier.QualifiedName`, or ``None`` if
            it could not be resolved.
        """
        if not qname:
            return None

        if isinstance(qname, QualifiedName):
            #  Register the namespace if it has not been registered before
            namespace = qname.namespace
            prefix = namespace.prefix
            local_part = qname.localpart
            if not prefix:
                # the namespace is a default namespace
                if self._default == namespace:
                    # the same default namespace is defined
                    new_qname = self._default[local_part]
                elif self._default is None:
                    # no default namespace is defined, reused the one given
                    self._default = namespace
                    return qname  # no change, return the original
                else:
                    # different default namespace,
                    # use the 'dn' prefix for the new namespace
                    dn_namespace = Namespace("dn", namespace.uri)
                    dn_namespace = self.add_namespace(dn_namespace)
                    new_qname = dn_namespace[local_part]
            elif prefix in self and self[prefix] == namespace:
                # No need to add the namespace
                existing_ns = self[prefix]
                if existing_ns is namespace:
                    return qname
                else:
                    # reuse the existing namespace
                    new_qname = existing_ns[local_part]
            else:
                # Do not reuse the namespace object, making an identical copy
                ns = self.add_namespace(Namespace(namespace.prefix, namespace.uri))
                # minting the same Qualified Name from the namespace's copy
                new_qname = ns[qname.localpart]
            # returning the new qname
            return new_qname

        # Trying to generate a valid qualified name from here
        if not isinstance(qname, (str, Identifier)):
            # Only proceed with a string or URI value
            return None
        # Extract the URI string value if it is an identifier
        str_value = qname.uri if isinstance(qname, Identifier) else qname
        if str_value.startswith("_:"):
            # this is a blank node ID
            return None
        elif ":" in str_value:
            #  check if the identifier contains a registered prefix
            prefix, local_part = str_value.split(":", 1)
            if prefix in self:
                #  return a new QualifiedName
                return self[prefix][local_part]
            if prefix in self._prefix_renamed_map:
                #  return a new QualifiedName
                return self._prefix_renamed_map[prefix][local_part]
            else:
                #  assuming it is a URI (with the first part as its scheme)
                #  check if the URI can be compacted by any of the registered namespaces
                for namespace in self.values():
                    if str_value.startswith(namespace.uri):
                        #  create a QName with the namespace
                        return namespace[str_value.replace(namespace.uri, "")]
        elif self._default and isinstance(qname, str):
            # no colon in the identifier and a default namespace is defined,
            # create and return a qualified name in the default namespace
            return self._default[qname]

        if self.parent:
            # all attempts have failed so far
            # now delegate this to the parent NamespaceManager
            return self.parent.valid_qualified_name(qname)

        # Default to FAIL
        return None

    def get_anonymous_identifier(self, local_prefix: str = "id") -> Identifier:
        """Return a fresh anonymous (blank-node) identifier.

        Each call increments an internal counter, so successive calls return
        distinct identifiers.

        Args:
            local_prefix: Prefix for the local part of the identifier
                (default: ``"id"``).

        Returns:
            A new :class:`~prov.identifier.Identifier` of the form
            ``_:<local_prefix><n>``.
        """
        self._anon_id_count += 1
        return Identifier(f"_:{local_prefix}{self._anon_id_count}")

    def _get_unused_prefix(self, original_prefix: str) -> str:
        if original_prefix not in self:
            return original_prefix
        count = 1
        while True:
            new_prefix = "_".join((original_prefix, str(count)))
            if new_prefix in self:
                count += 1
            else:
                return new_prefix


class ProvBundle:
    """PROV Bundle"""

    def __init__(
        self,
        records: Iterable[ProvRecord] | None = None,
        identifier: QualifiedName | None = None,
        namespaces: NSCollection | None = None,
        document: ProvDocument | None = None,
    ):
        """Initialise the bundle.

        Args:
            records: Optional iterable of records to add to the bundle
                (default: ``None``).
            identifier: Optional identifier of the bundle (default: ``None``).
            namespaces: Optional namespaces to register, as a ``{prefix: uri}``
                dict or an iterable of :class:`~prov.identifier.Namespace`
                (default: ``None``).
            document: Optional parent document for the bundle (default:
                ``None``).
        """
        #  Initializing bundle-specific attributes
        self._identifier = identifier
        self._records = []  # type: list[ProvRecord]
        self._id_map = defaultdict(list)  # type: dict[QualifiedName, list[ProvRecord]]
        self._document = document
        self._namespaces = NamespaceManager(
            namespaces, parent=(document._namespaces if document is not None else None)
        )  # type: NamespaceManager
        if records:
            for record in records:
                self.add_record(record)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self._identifier}>"

    @property
    def namespaces(self) -> set[Namespace]:
        """The set of the bundle's registered namespaces."""
        return set(self._namespaces.get_registered_namespaces())

    @property
    def default_ns_uri(self) -> str | None:
        """The bundle's default namespace URI, or ``None`` if none is set."""
        default_ns = self._namespaces.get_default_namespace()
        return default_ns.uri if default_ns else None

    @property
    def document(self) -> ProvDocument | None:
        """The parent document of this bundle, or ``None`` if it has none."""
        return self._document

    @property
    def identifier(self) -> QualifiedName | None:
        """The bundle's identifier, or ``None`` if it has none."""
        return self._identifier

    @property
    def records(self) -> list[ProvRecord]:
        """A copy of the list of all records in this bundle."""
        return list(self._records)

    #  Bundle configurations
    def set_default_namespace(self, uri: str) -> None:
        """Set the bundle's default namespace to one with the given URI.

        Args:
            uri: The URI of the default namespace.
        """
        self._namespaces.set_default_namespace(uri)

    def get_default_namespace(self) -> Namespace | None:
        """Return the default namespace, or ``None`` if none is set."""
        return self._namespaces.get_default_namespace()

    def add_namespace(
        self, namespace_or_prefix: Namespace | str, uri: str | None = None
    ) -> Namespace:
        """Add a namespace to the bundle, unless an equivalent one exists.

        Args:
            namespace_or_prefix: A :class:`~prov.identifier.Namespace` to add,
                or a prefix string (in which case ``uri`` is required).
            uri: The namespace URI; required when ``namespace_or_prefix`` is a
                prefix string (default: ``None``).

        Returns:
            The registered namespace (which may be an existing or renamed one).

        Raises:
            ProvException: If a prefix string is given without a ``uri``.
        """
        if isinstance(namespace_or_prefix, Namespace):
            return self._namespaces.add_namespace(namespace_or_prefix)
        else:
            if uri is not None:
                return self._namespaces.add_namespace(
                    Namespace(namespace_or_prefix, uri)
                )
            else:
                raise ProvException("Cannot add a namespace without a URI")

    def get_registered_namespaces(self) -> Iterable[Namespace]:
        """Return all namespaces registered on the bundle.

        Returns:
            An iterable of :class:`~prov.identifier.Namespace`.
        """
        return self._namespaces.get_registered_namespaces()

    def valid_qualified_name(
        self, identifier: QualifiedNameCandidate
    ) -> QualifiedName | None:
        """Resolve an identifier to a qualified name using this bundle.

        Args:
            identifier: The candidate to resolve.

        Returns:
            The resolved :class:`~prov.identifier.QualifiedName`, or ``None`` if
            it could not be resolved.
        """
        return self._namespaces.valid_qualified_name(identifier)

    def mandatory_valid_qname(
        self, identifier: QualifiedNameCandidate
    ) -> QualifiedName:
        """Resolve an identifier to a qualified name, requiring success.

        Args:
            identifier: The candidate to resolve.

        Returns:
            The resolved :class:`~prov.identifier.QualifiedName`.

        Raises:
            ProvExceptionInvalidQualifiedName: If the identifier cannot be
                resolved to a valid qualified name.
        """
        valid_qname = self.valid_qualified_name(identifier)
        if valid_qname is not None:
            return valid_qname
        else:
            raise ProvExceptionInvalidQualifiedName(identifier)

    def get_records(
        self, class_or_type_or_tuple: type | tuple[type] | None = None
    ) -> Iterable[ProvRecord]:
        """Return the bundle's records, optionally filtered by type.

        Args:
            class_or_type_or_tuple: An optional class or tuple of classes; only
                records passing ``isinstance()`` against it are returned
                (default: ``None``, meaning all records).

        Returns:
            The matching :class:`ProvRecord` objects (a list when unfiltered,
            otherwise a filter iterator).
        """
        results = list(self._records)  # make a (shallow) copy of the record list
        if class_or_type_or_tuple:
            return filter(lambda rec: isinstance(rec, class_or_type_or_tuple), results)
        else:
            return results

    def get_record(self, identifier: QualifiedNameCandidate) -> list[ProvRecord]:
        """Return all records matching a given identifier.

        Args:
            identifier: The record identifier to look up.

        Returns:
            The matching :class:`ProvRecord` objects, or an empty list if the
            identifier is invalid or unknown.
        """
        valid_id = self.valid_qualified_name(identifier)
        return list(self._id_map[valid_id]) if valid_id is not None else []

    # Miscellaneous functions
    def is_document(self) -> bool:
        """Return ``True`` if this is a document, ``False`` otherwise."""
        return False

    def is_bundle(self) -> bool:
        """Return ``True`` if this is a (named) bundle, ``False`` otherwise."""
        return True

    def has_bundles(self) -> bool:
        """Return ``True`` if this object contains bundles, ``False`` otherwise."""
        return False

    @property
    def bundles(self) -> Iterable[ProvBundle]:
        """The bundles contained in this object.

        Raises:
            ProvException: Always, since a plain bundle cannot contain
                sub-bundles. Only :class:`ProvDocument` overrides this.
        """
        raise ProvException("A PROV bundle does not contain sub-bundles")

    def get_provn(self, _indent_level: int = 0) -> str:
        """Return the PROV-N representation of the bundle."""
        indentation = "" + ("  " * _indent_level)
        newline = "\n" + ("  " * (_indent_level + 1))

        #  if this is the document, start the document;
        # otherwise, start the bundle
        lines = ["document"] if self.is_document() else [f"bundle {self._identifier}"]

        default_namespace = self._namespaces.get_default_namespace()
        if default_namespace:
            lines.append(f"default <{default_namespace.uri}>")

        registered_namespaces = self._namespaces.get_registered_namespaces()
        if registered_namespaces:
            lines.extend(
                [
                    f"prefix {namespace.prefix} <{namespace.uri}>"
                    for namespace in registered_namespaces
                ]
            )

        if default_namespace or registered_namespaces:
            #  a blank line between the prefixes and the assertions
            lines.append("")

        #  adding all the records
        lines.extend([record.get_provn() for record in self._records])
        if self.is_document():
            # Print out bundles
            lines.extend(bundle.get_provn(_indent_level + 1) for bundle in self.bundles)
        provn_str = newline.join(lines) + "\n"

        #  closing the structure
        provn_str += indentation + (
            "endDocument" if self.is_document() else "endBundle"
        )
        return provn_str

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ProvBundle):
            return False
        other_records = set(other.get_records())
        this_records = set(self.get_records())
        if len(this_records) != len(other_records):
            return False
        #  check if all records for equality
        for record_a in this_records:
            #  Manually look for the record
            found = False
            for record_b in other_records:
                if record_a == record_b:
                    other_records.remove(record_b)
                    found = True
                    break
            if not found:
                logger.debug(
                    "Equality (ProvBundle): Could not find this record: %s",
                    str(record_a),
                )
                return False
        return True

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    __hash__ = None  # type: ignore[assignment]

    # Transformations
    def _unified_records(self) -> list[ProvRecord]:
        """Returns a list of unified records."""
        # TODO: Check unification rules in the PROV-CONSTRAINTS document
        # This method simply merges the records having the same name
        merged_records = {}
        for _identifier, records in self._id_map.items():
            if len(records) > 1:
                # more than one record having the same identifier
                # merge the records
                merged = records[0].copy()
                for record in records[1:]:
                    merged.add_attributes(record.attributes)
                # map all of them to the merged record
                for record in records:
                    merged_records[record] = merged
        if not merged_records:
            # No merging done, just return the list of original records
            return list(self._records)

        added_merged_records = set()
        unified_records = []
        for record in self._records:
            if record in merged_records:
                merged = merged_records[record]
                if merged not in added_merged_records:
                    unified_records.append(merged)
                    added_merged_records.add(merged)
            else:
                # add the original record
                unified_records.append(record)
        return unified_records

    def unified(self) -> ProvBundle:
        """Return a new bundle with records sharing an identifier merged.

        For each identifier carried by more than one record, a single merged
        record is produced by unioning the attributes of all records with that
        identifier onto a copy of the first. Records with a unique identifier,
        or no identifier, pass through unchanged. This is a simple
        identifier-keyed attribute union, not the full PROV-CONSTRAINTS
        unification: no type/attribute conflicts are detected and no inference
        is performed. The original bundle is left untouched.

        Returns:
            The new, unified :class:`ProvBundle`.
        """
        unified_records = self._unified_records()
        bundle = ProvBundle(records=unified_records, identifier=self.identifier)
        return bundle

    def update(self, other: ProvBundle) -> None:
        """Append all records of another bundle into this bundle.

        Args:
            other: The :class:`ProvBundle` whose records are appended.

        Raises:
            ProvException: If ``other`` is not a :class:`ProvBundle`, or is a
                document that itself contains sub-bundles.
        """
        if isinstance(other, ProvBundle):
            if other.is_document() and other.has_bundles():
                # Cannot add bundles to a bundle
                raise ProvException(
                    "ProvBundle.update(): The other bundle is a document with "
                    "sub-bundle(s)."
                )
            for record in other.get_records():
                self.add_record(record)
        else:
            raise ProvException(
                "ProvBundle.update(): The other bundle is not a ProvBundle "
                f"instance ({type(other)})"
            )

    # Provenance statements
    def _add_record(self, record: ProvRecord) -> None:
        # IMPORTANT: All records need to be added to a bundle/document via this
        # method. Otherwise, the _id_map dict will not be correctly updated
        identifier = record.identifier
        if identifier is not None:
            self._id_map[identifier].append(record)
        self._records.append(record)

    def new_record(
        self,
        record_type: QualifiedName,
        identifier: OptionalID,
        attributes: RecordAttributesArg | None = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvRecord:
        """Create a new record, add it to the bundle, and return it.

        Args:
            record_type: The record type, one of the keys of
                :data:`PROV_REC_CLS`.
            identifier: The identifier for the new record (may be ``None`` for
                relations).
            attributes: Formal attributes of the record, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).
            other_attributes: Additional (non-formal) attributes, in the same
                forms (default: ``None``).

        Returns:
            The newly created and added :class:`ProvRecord`.
        """
        attr_list = []  # type: list[tuple[QualifiedNameCandidate, Any]]
        if attributes:
            if isinstance(attributes, dict):
                attr_list.extend((attr, value) for attr, value in attributes.items())
            else:
                # expecting a list of attributes here
                attr_list.extend(attributes)
        if other_attributes:
            attr_list.extend(
                other_attributes.items()
                if isinstance(other_attributes, dict)
                else other_attributes
            )
        record_identifier = (
            self.valid_qualified_name(identifier) if identifier else None
        )
        new_record = PROV_REC_CLS[record_type](self, record_identifier, attr_list)
        self._add_record(new_record)
        return new_record

    def add_record(self, record: ProvRecord) -> ProvRecord:
        """Add a copy of a record to this bundle.

        The record is re-created within this bundle (resolving its identifier
        and attributes against this bundle's namespaces), so the returned
        record is a new object, not ``record`` itself.

        Args:
            record: The :class:`ProvRecord` to copy into the bundle.

        Returns:
            The newly created :class:`ProvRecord` belonging to this bundle.
        """
        return self.new_record(
            record.get_type(),
            record.identifier,
            record.formal_attributes,
            record.extra_attributes,
        )

    def entity(
        self,
        identifier: QualifiedNameCandidate,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvEntity:
        """Create a new entity and add it to the bundle.

        Args:
            identifier: The identifier for the new entity.
            other_attributes: Optional attributes for the entity, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvEntity`.
        """
        return self.new_record(PROV_ENTITY, identifier, None, other_attributes)  # type: ignore

    def activity(
        self,
        identifier: QualifiedNameCandidate,
        startTime: DatetimeOrStr | None = None,
        endTime: DatetimeOrStr | None = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvActivity:
        """Create a new activity and add it to the bundle.

        Args:
            identifier: The identifier for the new activity.
            startTime: Optional start time, as a :class:`datetime.datetime` or a
                string parseable by :func:`dateutil.parser.parse`
                (default: ``None``).
            endTime: Optional end time, in the same forms (default: ``None``).
            other_attributes: Optional attributes for the activity, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvActivity`.
        """
        attributes = {
            PROV_ATTR_STARTTIME: _ensure_datetime(startTime),
            PROV_ATTR_ENDTIME: _ensure_datetime(endTime),
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_ACTIVITY,
            identifier,
            attributes,
            other_attributes,
        )  # type: ignore

    def generation(
        self,
        entity: EntityRef,
        activity: ActivityRef | None = None,
        time: DatetimeOrStr | None = None,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvRecord:
        """Create a new generation record for an entity.

        Args:
            entity: The generated entity (or its string identifier).
            activity: The activity (or its string identifier) involved in the
                generation (default: ``None``).
            time: Optional time of the generation, as a
                :class:`datetime.datetime` or a string parseable by
                :func:`dateutil.parser.parse` (default: ``None``).
            identifier: Optional identifier for the generation record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new generation record.
        """
        attributes = {
            PROV_ATTR_ENTITY: entity,
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_TIME: _ensure_datetime(time),
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_GENERATION,
            identifier,
            attributes,
            other_attributes,
        )

    def usage(
        self,
        activity: ActivityRef,
        entity: EntityRef | None = None,
        time: DatetimeOrStr | None = None,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvUsage:
        """Create a new usage record for an activity.

        Args:
            activity: The using activity (or its string identifier).
            entity: The entity (or its string identifier) involved in the usage
                relationship (default: ``None``).
            time: Optional time of the usage, as a :class:`datetime.datetime` or
                a string parseable by :func:`dateutil.parser.parse`
                (default: ``None``).
            identifier: Optional identifier for the usage record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvUsage` record.
        """
        attributes = {
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_ENTITY: entity,
            PROV_ATTR_TIME: _ensure_datetime(time),
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_USAGE,
            identifier,
            attributes,
            other_attributes,
        )  # type: ignore

    def start(
        self,
        activity: ActivityRef,
        trigger: EntityRef | None = None,
        starter: ActivityRef | None = None,
        time: DatetimeOrStr | None = None,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvStart:
        """Create a new start record for an activity.

        Args:
            activity: The started activity (or its string identifier).
            trigger: The entity (or its string identifier) triggering the start
                (default: ``None``).
            starter: Optional activity qualifying the start, through which the
                trigger entity is generated (default: ``None``).
            time: Optional time of the start, as a :class:`datetime.datetime` or
                a string parseable by :func:`dateutil.parser.parse`
                (default: ``None``).
            identifier: Optional identifier for the start record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvStart` record.
        """
        attributes = {
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_TRIGGER: trigger,
            PROV_ATTR_STARTER: starter,
            PROV_ATTR_TIME: _ensure_datetime(time),
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_START,
            identifier,
            attributes,
            other_attributes,
        )  # type: ignore

    def end(
        self,
        activity: ActivityRef,
        trigger: EntityRef | None = None,
        ender: ActivityRef | None = None,
        time: DatetimeOrStr | None = None,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvEnd:
        """Create a new end record for an activity.

        Args:
            activity: The ended activity (or its string identifier).
            trigger: The entity (or its string identifier) triggering the end
                (default: ``None``).
            ender: Optional activity qualifying the end, through which the
                trigger entity is generated (default: ``None``).
            time: Optional time of the end, as a :class:`datetime.datetime` or a
                string parseable by :func:`dateutil.parser.parse`
                (default: ``None``).
            identifier: Optional identifier for the end record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvEnd` record.
        """
        attributes = {
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_TRIGGER: trigger,
            PROV_ATTR_ENDER: ender,
            PROV_ATTR_TIME: _ensure_datetime(time),
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_END,
            identifier,
            attributes,
            other_attributes,
        )  # type: ignore

    def invalidation(
        self,
        entity: EntityRef,
        activity: ActivityRef | None = None,
        time: DatetimeOrStr | None = None,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvInvalidation:
        """Create a new invalidation record for an entity.

        Args:
            entity: The invalidated entity (or its string identifier).
            activity: The activity (or its string identifier) involved in the
                invalidation (default: ``None``).
            time: Optional time of the invalidation, as a
                :class:`datetime.datetime` or a string parseable by
                :func:`dateutil.parser.parse` (default: ``None``).
            identifier: Optional identifier for the invalidation record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvInvalidation` record.
        """
        attributes = {
            PROV_ATTR_ENTITY: entity,
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_TIME: _ensure_datetime(time),
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_INVALIDATION,
            identifier,
            attributes,
            other_attributes,
        )  # type: ignore

    def communication(
        self,
        informed: ActivityRef,
        informant: ActivityRef,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvCommunication:
        """Create a new communication record between two activities.

        Args:
            informed: The informed activity (relationship destination).
            informant: The informing activity (relationship source).
            identifier: Optional identifier for the communication record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvCommunication` record.
        """
        attributes = {
            PROV_ATTR_INFORMED: informed,
            PROV_ATTR_INFORMANT: informant,
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_COMMUNICATION,
            identifier,
            attributes,
            other_attributes,
        )  # type: ignore

    def agent(
        self,
        identifier: QualifiedNameCandidate,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvAgent:
        """Create a new agent and add it to the bundle.

        Args:
            identifier: The identifier for the new agent.
            other_attributes: Optional attributes for the agent, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvAgent`.
        """
        return self.new_record(PROV_AGENT, identifier, None, other_attributes)  # type: ignore

    def attribution(
        self,
        entity: EntityRef,
        agent: AgentRef,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvAttribution:
        """Create a new attribution record between an entity and an agent.

        Args:
            entity: The entity (or its string identifier) being attributed
                (relationship source).
            agent: The agent (or its string identifier) the entity is attributed
                to (relationship destination).
            identifier: Optional identifier for the attribution record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvAttribution` record.
        """
        attributes = {
            PROV_ATTR_ENTITY: entity,
            PROV_ATTR_AGENT: agent,
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_ATTRIBUTION,
            identifier,
            attributes,
            other_attributes,
        )  # type: ignore

    def association(
        self,
        activity: ActivityRef,
        agent: AgentRef | None = None,
        plan: EntityRef | None = None,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvAssociation:
        """Create a new association record for an activity.

        Args:
            activity: The activity (or its string identifier).
            agent: The agent (or its string identifier) associated with the
                activity (default: ``None``).
            plan: Optional entity qualifying the association through an internal
                plan (default: ``None``).
            identifier: Optional identifier for the association record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvAssociation` record.
        """
        attributes = {
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_AGENT: agent,
            PROV_ATTR_PLAN: plan,
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_ASSOCIATION,
            identifier,
            attributes,
            other_attributes,
        )  # type: ignore

    def delegation(
        self,
        delegate: AgentRef,
        responsible: AgentRef,
        activity: ActivityRef | None = None,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvDelegation:
        """Create a new delegation record between two agents.

        Args:
            delegate: The agent (or its string identifier) delegating the
                responsibility (relationship source).
            responsible: The agent (or its string identifier) the responsibility
                is delegated to (relationship destination).
            activity: Optional activity qualifying the delegation
                (default: ``None``).
            identifier: Optional identifier for the delegation record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvDelegation` record.
        """
        attributes = {
            PROV_ATTR_DELEGATE: delegate,
            PROV_ATTR_RESPONSIBLE: responsible,
            PROV_ATTR_ACTIVITY: activity,
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_DELEGATION,
            identifier,
            attributes,
            other_attributes,
        )  # type: ignore

    def influence(
        self,
        influencee: EntityRef | ActivityRef | AgentRef,
        influencer: EntityRef | ActivityRef | AgentRef,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvInfluence:
        """Create a new influence record between two entities, activities or agents.

        Args:
            influencee: The influenced entity, activity or agent (relationship
                source).
            influencer: The influencing entity, activity or agent (relationship
                destination).
            identifier: Optional identifier for the influence record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvInfluence` record.
        """
        attributes = {
            PROV_ATTR_INFLUENCEE: influencee,
            PROV_ATTR_INFLUENCER: influencer,
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_INFLUENCE,
            identifier,
            attributes,
            other_attributes,
        )  # type: ignore

    def derivation(
        self,
        generatedEntity: EntityRef,
        usedEntity: EntityRef,
        activity: ActivityRef | None = None,
        generation: GenrationRef | None = None,
        usage: UsageRef | None = None,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvDerivation:
        """Create a new derivation record for a generated entity from a used entity.

        Args:
            generatedEntity: The generated entity (or its string identifier),
                the relationship source.
            usedEntity: The used entity (or its string identifier), the
                relationship destination.
            activity: The activity (or its string identifier) involved in the
                derivation (default: ``None``).
            generation: Optional generation record qualifying the derivation
                through the activity's generation of the generated entity
                (default: ``None``).
            usage: Optional usage record qualifying the derivation through the
                activity's use of the used entity (default: ``None``).
            identifier: Optional identifier for the derivation record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvDerivation` record.
        """
        attributes = {
            PROV_ATTR_GENERATED_ENTITY: generatedEntity,
            PROV_ATTR_USED_ENTITY: usedEntity,
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_GENERATION: generation,
            PROV_ATTR_USAGE: usage,
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_DERIVATION, identifier, attributes, other_attributes
        )  # type: ignore

    def revision(
        self,
        generatedEntity: EntityRef,
        usedEntity: EntityRef,
        activity: ActivityRef | None = None,
        generation: GenrationRef | None = None,
        usage: UsageRef | None = None,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvDerivation:
        """Create a new revision record for a generated entity from a used entity.

        A revision is a derivation with an additional ``prov:Revision`` type.

        Args:
            generatedEntity: The generated (revised) entity (or its string
                identifier), the relationship source.
            usedEntity: The used (original) entity (or its string identifier),
                the relationship destination.
            activity: The activity (or its string identifier) involved in the
                revision (default: ``None``).
            generation: Optional generation record qualifying the derivation
                (default: ``None``).
            usage: Optional usage record qualifying the derivation
                (default: ``None``).
            identifier: Optional identifier for the revision record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvDerivation` record, typed as a revision.
        """
        record = self.derivation(
            generatedEntity,
            usedEntity,
            activity,
            generation,
            usage,
            identifier,
            other_attributes,
        )
        record.add_asserted_type(PROV["Revision"])
        return record

    def quotation(
        self,
        generatedEntity: EntityRef,
        usedEntity: EntityRef,
        activity: ActivityRef | None = None,
        generation: GenrationRef | None = None,
        usage: UsageRef | None = None,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvDerivation:
        """Create a new quotation record for a generated entity from a used entity.

        A quotation is a derivation with an additional ``prov:Quotation`` type.

        Args:
            generatedEntity: The quoting entity (or its string identifier), the
                relationship source.
            usedEntity: The quoted entity (or its string identifier), the
                relationship destination.
            activity: The activity (or its string identifier) involved in the
                quotation (default: ``None``).
            generation: Optional generation record qualifying the derivation
                (default: ``None``).
            usage: Optional usage record qualifying the derivation
                (default: ``None``).
            identifier: Optional identifier for the quotation record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvDerivation` record, typed as a quotation.
        """
        record = self.derivation(
            generatedEntity,
            usedEntity,
            activity,
            generation,
            usage,
            identifier,
            other_attributes,
        )
        record.add_asserted_type(PROV["Quotation"])
        return record

    def primary_source(
        self,
        generatedEntity: EntityRef,
        usedEntity: EntityRef,
        activity: ActivityRef | None = None,
        generation: GenrationRef | None = None,
        usage: UsageRef | None = None,
        identifier: OptionalID = None,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvDerivation:
        """Create a new primary-source record for a generated entity from a used
        entity.

        A primary source is a derivation with an additional
        ``prov:PrimarySource`` type.

        Args:
            generatedEntity: The derived entity (or its string identifier), the
                relationship source.
            usedEntity: The primary-source entity (or its string identifier),
                the relationship destination.
            activity: The activity (or its string identifier) involved
                (default: ``None``).
            generation: Optional generation record qualifying the derivation
                (default: ``None``).
            usage: Optional usage record qualifying the derivation
                (default: ``None``).
            identifier: Optional identifier for the primary-source record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or an
                iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvDerivation` record, typed as a primary source.
        """
        record = self.derivation(
            generatedEntity,
            usedEntity,
            activity,
            generation,
            usage,
            identifier,
            other_attributes,
        )
        record.add_asserted_type(PROV["PrimarySource"])
        return record

    def specialization(
        self, specificEntity: EntityRef, generalEntity: EntityRef
    ) -> ProvSpecialization:
        """Create a new specialisation record from a general entity.

        Args:
            specificEntity: The specific entity (or its string identifier), the
                relationship source.
            generalEntity: The general entity (or its string identifier), the
                relationship destination.

        Returns:
            The new :class:`ProvSpecialization` record.
        """
        attributes = {
            PROV_ATTR_SPECIFIC_ENTITY: specificEntity,
            PROV_ATTR_GENERAL_ENTITY: generalEntity,
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_SPECIALIZATION,
            None,
            attributes,
        )  # type: ignore

    def alternate(self, alternate1: EntityRef, alternate2: EntityRef) -> ProvAlternate:
        """Create a new alternate record between two entities.

        Args:
            alternate1: The first entity (or its string identifier), the
                relationship source.
            alternate2: The second entity (or its string identifier), the
                relationship destination.

        Returns:
            The new :class:`ProvAlternate` record.
        """
        attributes = {
            PROV_ATTR_ALTERNATE1: alternate1,
            PROV_ATTR_ALTERNATE2: alternate2,
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_ALTERNATE,
            None,
            attributes,
        )  # type: ignore

    def mention(
        self, specificEntity: EntityRef, generalEntity: EntityRef, bundle: EntityRef
    ) -> ProvMention:
        """Create a new mention record from a general entity in a bundle.

        Args:
            specificEntity: The specific entity (or its string identifier), the
                relationship source.
            generalEntity: The general entity (or its string identifier), the
                relationship destination.
            bundle: The bundle (or its string identifier) that the general
                entity is described in.

        Returns:
            The new :class:`ProvMention` record.
        """
        attributes = {
            PROV_ATTR_SPECIFIC_ENTITY: specificEntity,
            PROV_ATTR_GENERAL_ENTITY: generalEntity,
            PROV_ATTR_BUNDLE: bundle,
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_MENTION,
            None,
            attributes,
        )  # type: ignore

    def collection(
        self,
        identifier: QualifiedNameCandidate,
        other_attributes: RecordAttributesArg | None = None,
    ) -> ProvEntity:
        """Create a new collection entity and add it to the bundle.

        A collection is an entity with an additional ``prov:Collection`` type.

        Args:
            identifier: The identifier for the new collection.
            other_attributes: Optional attributes for the collection, as a dict
                or an iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvEntity`, typed as a collection.
        """
        record = self.new_record(PROV_ENTITY, identifier, None, other_attributes)
        record.add_asserted_type(PROV["Collection"])
        return record  # type: ignore

    def membership(self, collection: EntityRef, entity: EntityRef) -> ProvMembership:
        """Create a new membership record adding an entity to a collection.

        Args:
            collection: The collection (or its string identifier) the entity is
                added to.
            entity: The entity (or its string identifier) added to the
                collection.

        Returns:
            The new :class:`ProvMembership` record.
        """
        attributes = {
            PROV_ATTR_COLLECTION: collection,
            PROV_ATTR_ENTITY: entity,
        }  # type: dict[QualifiedNameCandidate, Any]
        return self.new_record(
            PROV_MEMBERSHIP,
            None,
            attributes,
        )  # type: ignore

    def plot(
        self,
        filename: PathLike | None = None,
        show_nary: bool = True,
        use_labels: bool = False,
        show_element_attributes: bool = True,
        show_relation_attributes: bool = True,
    ) -> None:
        """Plot the bundle as a graph, saving to a file or displaying it.

        Args:
            filename: The path to save the plot to; the image format is derived
                from its extension. If not given, the plot is shown in an
                interactive matplotlib window (default: ``None``).
            show_nary: Whether to show all elements in n-ary relations
                (default: ``True``).
            use_labels: Whether to label elements by their ``prov:label``
                property instead of their identifier (default: ``False``).
            show_element_attributes: Whether to show element attributes
                (default: ``True``).
            show_relation_attributes: Whether to show relation attributes
                (default: ``True``).

        Raises:
            ValueError: If the format implied by ``filename`` cannot be saved.
            ImportError: If no ``filename`` is given but matplotlib is not
                installed.
        """
        # Lazy imports to have soft dependencies on pydot and matplotlib
        # (imported even later).
        from prov import dot

        if filename:
            format = str(os.path.splitext(filename)[-1]).lower().strip(os.path.extsep)
        else:
            format = "png"
        format = format.lower()
        d = dot.prov_to_dot(
            self,
            show_nary=show_nary,
            use_labels=use_labels,
            show_element_attributes=show_element_attributes,
            show_relation_attributes=show_relation_attributes,
        )
        method = f"create_{format}"
        if not hasattr(d, method):
            raise ValueError(f"Format '{format}' cannot be saved.")
        with io.BytesIO() as buf:
            buf.write(getattr(d, method)())

            buf.seek(0, 0)
            if filename:
                with open(filename, "wb") as fh:
                    fh.write(buf.read())
            else:
                # Use matplotlib to show the image as it likely is more
                # widespread than PIL and works nicely in the ipython notebook.
                try:
                    import matplotlib.image as mpimg  # type: ignore
                    import matplotlib.pylab as plt  # type: ignore
                except ImportError as e:
                    raise ImportError(
                        "The plot() method requires matplotlib when no filename"
                        ' is provided. Install it with: pip install "prov[plot]"'
                    ) from e

                max_size = 30

                img = mpimg.imread(buf)
                # pydot makes a border around the image. remove it.
                img = img[1:-1, 1:-1]
                size = (img.shape[1] / 100.0, img.shape[0] / 100.0)
                scale = max_size / max(size) if max(size) > max_size else 1.0
                size = (scale * size[0], scale * size[1])

                plt.figure(figsize=size)
                plt.subplots_adjust(bottom=0, top=1, left=0, right=1)
                plt.xticks([])
                plt.yticks([])
                plt.imshow(img)
                plt.axis("off")
                plt.show()

    #  Aliases
    wasGeneratedBy = generation
    used = usage
    wasStartedBy = start
    wasEndedBy = end
    wasInvalidatedBy = invalidation
    wasInformedBy = communication
    wasAttributedTo = attribution
    wasAssociatedWith = association
    actedOnBehalfOf = delegation
    wasInfluencedBy = influence
    wasDerivedFrom = derivation
    wasRevisionOf = revision
    wasQuotedFrom = quotation
    hadPrimarySource = primary_source
    alternateOf = alternate
    specializationOf = specialization
    mentionOf = mention
    hadMember = membership


class ProvDocument(ProvBundle):
    """Provenance Document."""

    def __init__(
        self,
        records: Iterable[ProvRecord] | None = None,
        namespaces: NSCollection | None = None,
    ):
        """Initialise the document.

        Args:
            records: Optional iterable of records to add to the document
                (default: ``None``).
            namespaces: Optional namespaces to register, as a ``{prefix: uri}``
                dict or an iterable of :class:`~prov.identifier.Namespace`
                (default: ``None``).
        """
        ProvBundle.__init__(
            self, records=records, identifier=None, namespaces=namespaces
        )
        self._bundles = {}  # type: dict[QualifiedName, ProvBundle]

    def __repr__(self) -> str:
        return "<ProvDocument>"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ProvDocument):
            return False
        # Comparing the documents' content
        if not super().__eq__(other):
            return False

        # Comparing the documents' bundles
        for b_id, bundle in self._bundles.items():
            if b_id not in other._bundles:
                return False
            other_bundle = other._bundles[b_id]
            if bundle != other_bundle:
                return False

        # Everything is the same
        return True

    def is_document(self) -> bool:
        """Return ``True`` if this is a document, ``False`` otherwise."""
        return True

    def is_bundle(self) -> bool:
        """Return ``True`` if this is a (named) bundle, ``False`` otherwise."""
        return False

    def has_bundles(self) -> bool:
        """Return ``True`` if the document contains bundles, ``False`` otherwise."""
        return len(self._bundles) > 0

    @property
    def bundles(self) -> Iterable[ProvBundle]:
        """The bundles contained in this document."""
        return self._bundles.values()

    # Transformations
    def flattened(self) -> ProvDocument:
        """Return a new document with all bundle records lifted to the top level.

        Every record from every bundle is moved up alongside the document's own
        records and the bundle structure is discarded; this is purely
        structural (nothing is merged or deduplicated). If the document has no
        bundles, it is returned unchanged. The original document is left
        untouched.

        Returns:
            The (new) flattened :class:`ProvDocument`, or this document itself
            if it has no bundles.
        """
        if self._bundles:
            # Creating a new document for all the records
            new_doc = ProvDocument()
            bundled_records = itertools.chain(
                *[b.get_records() for b in self._bundles.values()]
            )
            for record in itertools.chain(self._records, bundled_records):
                new_doc.add_record(record)
            return new_doc
        else:
            # returning the same document
            return self

    def unified(self) -> ProvDocument:
        """Return a new document with records sharing an identifier merged.

        The identifier-keyed attribute union (see :meth:`ProvBundle.unified`) is
        applied to the document's top-level records and, recursively, to each
        contained bundle, preserving the bundle structure. The original
        document is left untouched.

        Returns:
            The new, unified :class:`ProvDocument`.
        """
        document = ProvDocument(self._unified_records())
        document._namespaces = self._namespaces
        for bundle in self.bundles:
            unified_bundle = bundle.unified()
            document.add_bundle(unified_bundle)
        return document

    def update(self, other: ProvBundle) -> None:
        """Append all records of another document or bundle into this document.

        Any bundles of ``other`` are also merged in: a bundle whose identifier
        already exists in this document is updated in place, otherwise a new
        bundle is created.

        Args:
            other: The :class:`ProvDocument` or :class:`ProvBundle` whose
                records are appended.

        Raises:
            ProvException: If ``other`` is not a :class:`ProvBundle` (or
                subclass).
        """
        if isinstance(other, ProvBundle):
            for record in other.get_records():
                self.add_record(record)
            if other.has_bundles():
                for bundle in other.bundles:
                    bundle_id = bundle.identifier
                    assert bundle_id is not None
                    if bundle.identifier in self._bundles:
                        self._bundles[bundle.identifier].update(bundle)
                    else:
                        new_bundle = self.bundle(bundle_id)
                        new_bundle.update(bundle)
        else:
            raise ProvException(
                "ProvDocument.update(): The other is not a ProvDocument or "
                f"ProvBundle instance ({type(other)})"
            )

    # Bundle operations
    def add_bundle(
        self, bundle: ProvBundle, identifier: QualifiedName | None = None
    ) -> None:
        """Add a bundle to this document.

        If a document (with no nested bundles) is passed, its records are copied
        into a fresh bundle. The bundle's identifier is normalised against this
        document's namespaces.

        Args:
            bundle: The :class:`ProvBundle` to add.
            identifier: Optional identifier to use for the bundle; if not given,
                the bundle's own identifier is used (default: ``None``).

        Raises:
            ProvException: If ``bundle`` is not a :class:`ProvBundle`, is a
                document with nested bundles, has no usable identifier, or an
                identifier collides with an existing bundle.
        """
        if not isinstance(bundle, ProvBundle):
            raise ProvException(
                "Only a ProvBundle instance can be added as a bundle in a ProvDocument."
            )

        if bundle.is_document():
            if bundle.has_bundles():
                raise ProvException(
                    "Cannot add a document with nested bundles as a bundle."
                )
            # Make it a new ProvBundle
            new_bundle = ProvBundle(namespaces=bundle.namespaces)
            new_bundle.update(bundle)
            bundle = new_bundle

        if identifier is None:
            identifier = bundle.identifier

        if not identifier:
            raise ProvException("The provided bundle has no identifier")

        # Link the bundle namespace manager to the document's
        bundle._namespaces.parent = self._namespaces

        valid_id = bundle.mandatory_valid_qname(identifier)
        # IMPORTANT: Rewriting the bundle identifier for consistency
        bundle._identifier = valid_id

        if valid_id in self._bundles:
            raise ProvException("A bundle with that identifier already exists")

        self._bundles[valid_id] = bundle
        bundle._document = self

    def bundle(self, identifier: QualifiedNameCandidate) -> ProvBundle:
        """Create a new, empty named bundle in this document.

        Args:
            identifier: The identifier to use for the bundle.

        Returns:
            The newly created :class:`ProvBundle`.

        Raises:
            ProvException: If ``identifier`` is ``None`` or invalid, or a bundle
                with that identifier already exists.
        """
        if identifier is None:
            raise ProvException(
                "An identifier is required. Cannot create an unnamed bundle."
            )
        valid_id = self.valid_qualified_name(identifier)
        if valid_id is None:
            raise ProvException(f'The provided identifier "{identifier}" is not valid')
        if valid_id in self._bundles:
            raise ProvException("A bundle with that identifier already exists")
        b = ProvBundle(identifier=valid_id, document=self)
        self._bundles[valid_id] = b
        return b

    # Serializing and deserializing
    def serialize(
        self,
        destination: io.IOBase | PathLike | None = None,
        format: str = "json",
        **args: Any,
    ) -> str | None:
        """Serialize this document to a destination or return it as a string.

        The available serialization formats are ``"json"``, ``"rdf"``, ``"xml"``
        and ``"provn"`` (see :func:`prov.serializers.get`).

        Args:
            destination: A writable stream or a local file path to write to. If
                ``None``, the serialization is returned as a string
                (default: ``None``). A non-local (network) location is not
                written and yields ``None``.
            format: The serialization format (default: ``"json"``, i.e.
                PROV-JSON).
            **args: Extra keyword arguments passed to the underlying serializer.

        Returns:
            The serialization as a string if no ``destination`` was given,
            otherwise ``None``.
        """
        serializer = serializers.get(format)(self)
        if destination is None:
            buffer = io.StringIO()
            serializer.serialize(buffer, **args)
            return buffer.getvalue()

        if isinstance(destination, IOBase):
            stream = destination
            serializer.serialize(stream, **args)
        else:
            location = str(destination)
            _scheme, netloc, path, _params, _query, _fragment = urlparse(location)
            if netloc != "":
                print(
                    "WARNING: not saving as location " + "is not a local file reference"
                )
                return None
            fd, name = tempfile.mkstemp()
            stream = os.fdopen(fd, "wb")
            serializer.serialize(stream, **args)
            stream.close()
            if hasattr(shutil, "move"):
                shutil.move(name, path)
            else:
                shutil.copy(name, path)
                os.remove(name)
        return None

    @staticmethod
    def deserialize(
        source: io.IOBase | PathLike | None = None,
        content: str | bytes | None = None,
        format: str = "json",
        **args: Any,
    ) -> ProvDocument:
        """Deserialize a document from a source stream/file or a string.

        Exactly one of ``source`` or ``content`` should be given; ``content``
        takes precedence if both are. Note that not all formats support
        deserialization (PROV-N is write-only).

        Args:
            source: A readable stream or a file path to read from
                (default: ``None``).
            content: The document as a ``str`` or ``bytes`` to read from
                (default: ``None``).
            format: The serialization format (default: ``"json"``, i.e.
                PROV-JSON).
            **args: Extra keyword arguments passed to the underlying
                deserializer.

        Returns:
            The deserialized :class:`ProvDocument`.

        Raises:
            TypeError: If neither ``source`` nor ``content`` is provided.
        """
        serializer = serializers.get(format)()

        if content is not None:
            # io.StringIO only accepts unicode strings
            stream = io.StringIO(
                content if isinstance(content, str) else content.decode()
            )
            return serializer.deserialize(stream, **args)

        if source is not None:
            if isinstance(source, io.IOBase):
                return serializer.deserialize(source, **args)
            else:
                with open(source) as f:
                    return serializer.deserialize(f, **args)

        raise TypeError("Either source or content must be provided")


def sorted_attributes(
    element: QualifiedName, attributes: Iterable[NameValuePair]
) -> list[NameValuePair]:
    """Sort attributes into the order required by PROV-XML.

    Args:
        element: The PROV record type used to derive the formal-attribute order.
        attributes: The ``(name, value)`` attribute pairs to sort.

    Returns:
        The attributes ordered by formal-attribute position, then the universal
        label/location/role/type/value attributes, then any remaining
        attributes alphabetically.
    """
    attributes = list(attributes)
    order = list(PROV_REC_CLS[element].FORMAL_ATTRIBUTES)

    # Append label, location, role, type, and value attributes. This is
    # universal amongst all elements.
    order.extend([PROV_LABEL, PROV_LOCATION, PROV_ROLE, PROV_TYPE, PROV_VALUE])

    # Sort function. The PROV XML specification talks about alphabetical
    # sorting. We now interpret it as sorting by tag including the prefix
    # first and then sorting by the text, also including the namespace
    # prefix if given.
    def sort_fct(x: NameValuePair) -> tuple[str, str]:
        return str(x[0]), str(x[1].value if hasattr(x[1], "value") else x[1])

    sorted_elements = []
    for item in order:
        this_type_list = []
        for e in list(attributes):
            if e[0] != item:
                continue
            this_type_list.append(e)
            attributes.remove(e)
        this_type_list.sort(key=sort_fct)
        sorted_elements.extend(this_type_list)
    # Add remaining attributes. According to the spec, the other attributes
    # have a fixed alphabetical order.
    attributes.sort(key=sort_fct)
    sorted_elements.extend(attributes)

    return sorted_elements
