"""PROV-DM records: elements, relations, literals, and datatype helpers."""

from __future__ import annotations  # needed for | type annotations in Python < 3.10

import datetime
import logging
import os
import typing  # noqa: F401 -- used by `# type: typing.TypeAlias` comments below
from collections import defaultdict
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, Union

import dateutil.parser

from prov import Error
from prov.constants import (
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
    XSD_LONG,
    XSD_STRING,
)
from prov.identifier import Identifier, Namespace, QualifiedName

if TYPE_CHECKING:
    from prov.model.bundle import ProvBundle

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

    def wasRevisionOf(
        self,
        usedEntity: EntityRef,
        activity: ActivityRef | None = None,
        generation: GenrationRef | None = None,
        usage: UsageRef | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> ProvEntity:
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
                an iterable of ``(name, value)`` pairs (default: ``None``).

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
        generation: GenrationRef | None = None,
        usage: UsageRef | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> ProvEntity:
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
                an iterable of ``(name, value)`` pairs (default: ``None``).

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
        generation: GenrationRef | None = None,
        usage: UsageRef | None = None,
        attributes: RecordAttributesArg | None = None,
    ) -> ProvEntity:
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
                an iterable of ``(name, value)`` pairs (default: ``None``).

        Returns:
            This entity (to allow chaining).
        """
        self._bundle.primary_source(
            self, usedEntity, activity, generation, usage, other_attributes=attributes
        )
        return self

    def mentionOf(self, generalEntity: EntityRef, bundle: EntityRef) -> ProvEntity:
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
        influencer: EntityRef | ActivityRef | AgentRef,
        attributes: RecordAttributesArg | None = None,
    ) -> ProvEntity:
        """Create a new influence record on this entity by an influencer.

        Args:
            influencer: The influencing entity, activity or agent (or its
                string identifier).
            attributes: Optional extra attributes for the record, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

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

    def wasInfluencedBy(
        self,
        influencer: EntityRef | ActivityRef | AgentRef,
        attributes: RecordAttributesArg | None = None,
    ) -> ProvActivity:
        """Create a new influence record on this activity by an influencer.

        Args:
            influencer: The influencing entity, activity or agent (or its
                string identifier).
            attributes: Optional extra attributes for the record, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

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

    def wasInfluencedBy(
        self,
        influencer: EntityRef | ActivityRef | AgentRef,
        attributes: RecordAttributesArg | None = None,
    ) -> ProvAgent:
        """Create a new influence record on this agent by an influencer.

        Args:
            influencer: The influencing entity, activity or agent (or its
                string identifier).
            attributes: Optional extra attributes for the record, as a dict or
                an iterable of ``(name, value)`` pairs (default: ``None``).

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
