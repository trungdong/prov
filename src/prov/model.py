"""Python implementation of the W3C Provenance Data Model (PROV-DM), including
support for PROV-JSON import/export

References:

PROV-DM: http://www.w3.org/TR/prov-dm/
PROV-JSON: https://openprovenance.org/prov-json/
"""

from __future__ import annotations  # needed for | type annotations in Python < 3.10

from collections import defaultdict
import datetime
import io
import itertools
import logging
import os
import shutil
import tempfile
from io import IOBase
from typing import (
    Any,
    Callable,
    Iterable,
    Optional,
    Union,
)
import typing  # to use typing.TypeAlias in comments for compatibility with Python 3.9
from urllib.parse import urlparse

import dateutil.parser
from prov import Error, serializers
from prov.constants import *
from prov.identifier import Identifier, QualifiedName, Namespace


__author__ = "Trung Dong Huynh"
__email__ = "trungdong@donggiang.com"


logger = logging.getLogger(__name__)


# Type aliases for convenience
QualifiedNameCandidate = Union[QualifiedName, str, Identifier]  # type: typing.TypeAlias
OptionalID = Optional[QualifiedNameCandidate]  # type: typing.TypeAlias
EntityRef = Union["ProvEntity", QualifiedNameCandidate]  # type: typing.TypeAlias
ActivityRef = Union["ProvActivity", QualifiedNameCandidate]  # type: typing.TypeAlias
AgentRef = Union[
    "ProvAgent", "ProvEntity", "ProvActivity", QualifiedNameCandidate
]  # type: typing.TypeAlias
GenrationRef = Union["ProvGeneration", QualifiedNameCandidate]  # type: typing.TypeAlias
UsageRef = Union["ProvUsage", QualifiedNameCandidate]  # type: typing.TypeAlias
RecordAttributesArg = Union[
    dict[QualifiedNameCandidate, Any],
    Iterable[tuple[QualifiedNameCandidate, Any]],
]  # type: typing.TypeAlias
NameValuePair = tuple[QualifiedName, Any]  # type: typing.TypeAlias
DatetimeOrStr = Union[datetime.datetime, str]  # type: typing.TypeAlias
NSCollection = Union[dict[str, str], Iterable[Namespace]]  # type: typing.TypeAlias
PathLike = Union[str, bytes, os.PathLike]  # type: typing.TypeAlias


# Data Types
def _ensure_datetime(value: Optional[DatetimeOrStr]) -> Optional[datetime.datetime]:
    if isinstance(value, str):
        return dateutil.parser.parse(value)
    else:
        return value


def parse_xsd_datetime(value: str) -> Optional[datetime.datetime]:
    try:
        return dateutil.parser.parse(value)
    except ValueError:
        pass
    return None


def parse_boolean(value: str) -> Optional[bool]:
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
SupportedXSDParsedTypes = Union[
    str, datetime.datetime, float, int, bool, Identifier, None
]  # type: typing.TypeAlias
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
    return (
        XSD_DATATYPE_PARSERS[datatype](value)
        if datatype in XSD_DATATYPE_PARSERS
        else None
    )


def first(a_set: set[Any]) -> Any | None:
    return next(iter(a_set), None)


def _ensure_multiline_string_triple_quoted(value: str) -> str:
    # converting the value to a string
    s = str(value)
    # Escaping any double quote
    s = s.replace('"', '\\"')
    if "\n" in s:
        return '"""%s"""' % s
    else:
        return '"%s"' % s


def encoding_provn_value(
    value: str | datetime.datetime | float | bool | QualifiedName,
) -> str:
    if isinstance(value, str):
        return _ensure_multiline_string_triple_quoted(value)
    elif isinstance(value, datetime.datetime):
        return '"{0}" %% xsd:dateTime'.format(value.isoformat())
    elif isinstance(value, float):
        return '"%g" %%%% xsd:float' % value
    elif isinstance(value, bool):
        return '"%i" %%%% xsd:boolean' % value
    else:
        # TODO: QName export
        return str(value)


class Literal(object):
    def __init__(
        self,
        value: Any,
        datatype: Optional[QualifiedName] = None,
        langtag: Optional[str] = None,
    ):
        self._value: str = str(value)  # value is always a string
        if langtag:
            if datatype is None:
                logger.debug(
                    "Assuming prov:InternationalizedString as the type of "
                    '"%s"@%s' % (value, langtag)
                )
                datatype = PROV_INTERNATIONALIZEDSTRING
            # PROV JSON states that the type field must not be set when
            # using the lang attribute and PROV XML requires it to be an
            # internationalized string.
            elif datatype != PROV_INTERNATIONALIZEDSTRING:
                logger.warning(
                    'Invalid data type (%s) for "%s"@%s, overridden as '
                    "prov:InternationalizedString." % (datatype, value, langtag)
                )
                datatype = PROV_INTERNATIONALIZEDSTRING
        self._datatype: Optional[QualifiedName] = datatype
        # langtag is always a string
        self._langtag: Optional[str] = str(langtag) if langtag is not None else None

    def __str__(self) -> str:
        return self.provn_representation()

    def __repr__(self) -> str:
        return "<Literal: %s>" % self.provn_representation()

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
        return self._value

    @property
    def datatype(self) -> QualifiedName | None:
        return self._datatype

    @property
    def langtag(self) -> str | None:
        return self._langtag

    def has_no_langtag(self) -> bool:
        return self._langtag is None

    def provn_representation(self) -> str:
        if self._langtag:
            # a language tag can only go with prov:InternationalizedString
            return "%s@%s" % (
                _ensure_multiline_string_triple_quoted(self._value),
                str(self._langtag),
            )
        else:
            return "%s %%%% %s" % (
                _ensure_multiline_string_triple_quoted(self._value),
                str(self._datatype),
            )


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
    """Intended qualified name."""

    def __init__(self, qname: Any):
        """
        Constructor.

        :param qname: Invalid qualified name.
        """
        self.qname = qname

    def __str__(self) -> str:
        return "Invalid Qualified Name: %s" % self.qname


class ProvElementIdentifierRequired(ProvException):
    """Exception for a missing element identifier."""

    def __str__(self) -> str:
        return (
            "An identifier is missing. All PROV elements require a valid " "identifier."
        )


#  PROV records
class ProvRecord(object):
    """Base class for PROV records."""

    FORMAL_ATTRIBUTES = ()  # type: tuple[QualifiedName, ...]
    """Formal attributes names of this record type, in the expected order."""

    _prov_type: Optional[QualifiedName] = None
    """PROV type of record."""

    def __init__(
        self,
        bundle: ProvBundle,
        identifier: Optional[QualifiedName],
        attributes: Optional[RecordAttributesArg] = None,
    ):
        """
        Constructor.

        :param bundle: Bundle for the PROV record.
        :param identifier: (Unique) identifier of the record.
        :param attributes: Attributes to associate with the record (default: None).
        """
        self._bundle = bundle
        self._identifier = identifier
        self._attributes: dict[QualifiedName, set] = defaultdict(set)
        if attributes:
            self.add_attributes(attributes)

    def __hash__(self) -> int:
        return hash((self.get_type(), self._identifier, frozenset(self.attributes)))

    def copy(self) -> "ProvRecord":
        """
        Return an exact copy of this record.
        """
        return PROV_REC_CLS[self.get_type()](
            self._bundle, self.identifier, self.attributes
        )

    def get_type(self) -> QualifiedName:
        """Returns the PROV type of the record."""
        if self._prov_type is not None:
            return self._prov_type
        else:
            raise NotImplementedError("Type not defined for this record.")

    def get_asserted_types(self) -> set[QualifiedName]:
        """Returns the set of all asserted PROV types of this record."""
        return self._attributes[PROV_TYPE]

    def add_asserted_type(self, type_identifier: QualifiedName) -> None:
        """
        Adds a PROV type assertion to the record.

        :param type_identifier: PROV namespace identifier to add.
        """
        self._attributes[PROV_TYPE].add(type_identifier)

    def get_attribute(self, attr_name: QualifiedNameCandidate) -> set:
        """
        Returns the attribute values (if any) for the specified attribute name).

        :param attr_name: Name of the attribute.
        :return: Set of value(s) of the specified attribute.
        :rtype: set
        """
        attr_name_qn = self._bundle.mandatory_valid_qname(attr_name)
        return self._attributes[attr_name_qn]

    @property
    def identifier(self) -> QualifiedName | None:
        """Record's identifier."""
        return self._identifier

    @property
    def attributes(self) -> list[tuple[QualifiedName, Any]]:
        """
        All record attributes.

        :return: List of tuples (name, value)
        """
        return [
            (attr_name, value)
            for attr_name, values in self._attributes.items()
            for value in values
        ]

    @property
    def args(self) -> tuple:
        """
        All values of the record's formal attributes.

        :return: Tuple
        """
        return tuple(
            first(self._attributes[attr_name]) for attr_name in self.FORMAL_ATTRIBUTES
        )

    @property
    def formal_attributes(self) -> tuple[tuple[QualifiedName, Any], ...]:
        """
        All names and values of the record's formal attributes.

        :return: Tuple of tuples (name, value)
        """
        return tuple(
            (attr_name, first(self._attributes[attr_name]))
            for attr_name in self.FORMAL_ATTRIBUTES
        )

    @property
    def extra_attributes(self) -> tuple[tuple[QualifiedName, Any], ...]:
        """
        All names and values of the record's attributes that are not formal
        attributes.

        :return: Tuple of tuples (name, value)
        """
        return tuple(
            (attr_name, attr_value)
            for attr_name, attr_value in self.attributes
            if attr_name not in self.FORMAL_ATTRIBUTES
        )

    @property
    def bundle(self) -> ProvBundle:
        """
        Bundle of the record.

        :return: :py:class:`ProvBundle`
        """
        return self._bundle

    @property
    def label(self) -> str:
        """Identifying label of the record."""
        return str(
            first(self._attributes[PROV_LABEL])
            if self._attributes[PROV_LABEL]
            else self._identifier
        )

    @property
    def value(self) -> Any:
        """Value of the record."""
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
        """
        Add attributes to the record.

        :param attributes: Dictionary of attributes, with keys being qualified
            identifiers. Alternatively, an iterable of tuples (key, value) with the
            keys satisfying the same condition.
        """
        if attributes:
            if isinstance(attributes, dict):
                # Converting the dictionary into a list of tuples
                # (i.e. attribute-value pairs)
                attributes = attributes.items()

            # Check if one of the attributes specifies that the current type
            # is a collection. In that case multiple attributes of the same
            # type are allowed.
            if PROV_ATTR_COLLECTION in [_i[0] for _i in attributes]:
                is_collection = True
            else:
                is_collection = False

            for attr_name, original_value in attributes:
                if original_value is None:
                    continue

                # make sure the attribute name is valid
                attr = self._bundle.mandatory_valid_qname(attr_name)

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
                    value = self._bundle.mandatory_valid_qname(qname)  # type: Any
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
                        "Invalid value for attribute %s: %s" % (attr, original_value)
                    )

                if (
                    not is_collection
                    and attr in PROV_ATTRIBUTES
                    and self._attributes[attr]
                ):
                    existing_value = first(self._attributes[attr])
                    is_not_same_value = True
                    try:
                        is_not_same_value = value != existing_value
                    except TypeError:
                        # Cannot compare them
                        pass  # consider them different values

                    if is_not_same_value:
                        raise ProvException(
                            "Cannot have more than one value for attribute %s" % attr
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
        """
        Returns the PROV-N representation of the record.

        :return: String
        """
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
            if attr in self._attributes and self._attributes[attr]:
                # Formal attributes always have single values
                value = first(self._attributes[attr])
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
                    extra.append("%s=%s" % (str(attr), provn_represenation))

        if extra:
            items.append("[%s]" % ", ".join(extra))
        prov_n = "%s(%s%s)" % (
            PROV_N_MAP[self.get_type()],
            relation_id,
            ", ".join(items),
        )
        return prov_n

    def is_element(self) -> bool:
        """
        True, if the record is an element, False otherwise.

        :return: bool
        """
        return False

    def is_relation(self) -> bool:
        """
        True, if the record is a relation, False otherwise.

        :return: bool
        """
        return False


#  Abstract classes for elements and relations
class ProvElement(ProvRecord):
    """Provenance Element (nodes in the provenance graph)."""

    def __init__(
        self,
        bundle: ProvBundle,
        identifier: Optional[QualifiedName],
        attributes: Optional[RecordAttributesArg] = None,
    ):
        if identifier is None:
            # All types of PROV elements require a valid identifier
            raise ProvElementIdentifierRequired()

        super(ProvElement, self).__init__(bundle, identifier, attributes)

    def is_element(self) -> bool:
        """
        True, if the record is an element, False otherwise.

        :return: bool
        """
        return True

    def __repr__(self) -> str:
        return "<%s: %s>" % (self.__class__.__name__, self._identifier)


class ProvRelation(ProvRecord):
    """Provenance Relationship (edge between nodes)."""

    def is_relation(self) -> bool:
        """
        True, if the record is a relation, False otherwise.

        :return: bool
        """
        return True

    def __repr__(self) -> str:
        identifier = " %s" % self._identifier if self._identifier else ""
        element_1, element_2 = [qname for _, qname in self.formal_attributes[:2]]
        return "<%s:%s (%s, %s)>" % (
            self.__class__.__name__,
            identifier,
            element_1,
            element_2,
        )


# Component 1: Entities and Activities
class ProvEntity(ProvElement):
    """Provenance Entity element"""

    _prov_type = PROV_ENTITY

    # Convenient assertions that take the current ProvEntity as the first
    # (formal) argument
    def wasGeneratedBy(
        self,
        activity: Optional[ActivityRef] = None,
        time: Optional[DatetimeOrStr] = None,
        attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvEntity:
        """
        Creates a new generation record to this entity.

        :param activity: Activity or string identifier of the activity involved in
            the generation (default: None).
        :param time: Optional time for the generation (default: None).
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        :param attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
        """
        self._bundle.generation(self, activity, time, other_attributes=attributes)
        return self

    def wasInvalidatedBy(
        self,
        activity: Optional[ActivityRef],
        time: Optional[DatetimeOrStr] = None,
        attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvEntity:
        """
        Creates a new invalidation record for this entity.

        :param activity: Activity or string identifier of the activity involved in
            the invalidation (default: None).
        :param time: Optional time for the invalidation (default: None).
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        :param attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
        """
        self._bundle.invalidation(self, activity, time, other_attributes=attributes)
        return self

    def wasDerivedFrom(
        self,
        usedEntity: EntityRef,
        activity: Optional[ActivityRef] = None,
        generation: Optional[GenrationRef] = None,
        usage: Optional[UsageRef] = None,
        attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvEntity:
        """
        Creates a new derivation record for this entity from a used entity.

        :param usedEntity: Entity or a string identifier for the used entity.
        :param activity: Activity or string identifier of the activity involved in
            the derivation (default: None).
        :param generation: Optional generation record to state qualified derivation
            through an internal generation (default: None).
        :param usage: Optional usage record to state qualified derivation through
            an internal usage (default: None).
        :param attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
        """
        self._bundle.derivation(
            self, usedEntity, activity, generation, usage, other_attributes=attributes
        )
        return self

    def wasAttributedTo(
        self, agent: AgentRef, attributes: Optional[RecordAttributesArg] = None
    ) -> ProvEntity:
        """
        Creates a new attribution record between this entity and an agent.

        :param agent: Agent or string identifier of the agent involved in the
            attribution.
        :param attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
        """
        self._bundle.attribution(self, agent, other_attributes=attributes)
        return self

    def alternateOf(self, alternate2: EntityRef) -> ProvEntity:
        """
        Creates a new alternate record between this and another entity.

        :param alternate2: Entity or a string identifier for the second entity.
        """
        self._bundle.alternate(self, alternate2)
        return self

    def specializationOf(self, generalEntity: EntityRef) -> ProvEntity:
        """
        Creates a new specialisation record for this from a general entity.

        :param generalEntity: Entity or a string identifier for the general entity.
        """
        self._bundle.specialization(self, generalEntity)
        return self

    def hadMember(self, entity: EntityRef) -> ProvEntity:
        """
        Creates a new membership record to an entity for a collection.

        :param entity: Entity to be added to the collection.
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
        startTime: Optional[datetime.datetime] = None,
        endTime: Optional[datetime.datetime] = None,
    ) -> None:
        """
        Sets the time this activity took place.

        :param startTime: Start time for the activity.
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        :param endTime: Start time for the activity.
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        """
        if startTime is not None:
            self._attributes[PROV_ATTR_STARTTIME] = {startTime}
        if endTime is not None:
            self._attributes[PROV_ATTR_ENDTIME] = {endTime}

    def get_startTime(self) -> datetime.datetime | None:
        """
        Returns the time the activity started.

        :return: :py:class:`datetime.datetime`
        """
        values = self._attributes[PROV_ATTR_STARTTIME]
        return first(values) if values else None

    def get_endTime(self) -> datetime.datetime | None:
        """
        Returns the time the activity ended.

        :return: :py:class:`datetime.datetime`
        """
        values = self._attributes[PROV_ATTR_ENDTIME]
        return first(values) if values else None

    # Convenient assertions that take the current ProvActivity as the first
    # (formal) argument
    def used(
        self,
        entity: EntityRef,
        time: Optional[DatetimeOrStr] = None,
        attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvActivity:
        """
        Creates a new usage record for this activity.

        :param entity: Entity or string identifier of the entity involved in
            the usage relationship (default: None).
        :param time: Optional time for the usage (default: None).
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        :param attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
        """
        self._bundle.usage(self, entity, time, other_attributes=attributes)
        return self

    def wasInformedBy(
        self, informant: ActivityRef, attributes: Optional[RecordAttributesArg] = None
    ) -> ProvActivity:
        """
        Creates a new communication record for this activity.

        :param informant: The informing activity (relationship source).
        :param attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
        """
        self._bundle.communication(self, informant, other_attributes=attributes)
        return self

    def wasStartedBy(
        self,
        trigger: Optional[EntityRef],
        starter: Optional[ActivityRef] = None,
        time: Optional[DatetimeOrStr] = None,
        attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvActivity:
        """
        Creates a new start record for this activity. The activity did not exist
        before the start by the trigger.

        :param trigger: Entity triggering the start of this activity.
        :param starter: Optional extra activity to state a qualified start
            through which the trigger entity for the start is generated
            (default: None).
        :param time: Optional time for the start (default: None).
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        :param attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
        """
        self._bundle.start(self, trigger, starter, time, other_attributes=attributes)
        return self

    def wasEndedBy(
        self,
        trigger: Optional[EntityRef],
        ender: Optional[ActivityRef] = None,
        time: Optional[DatetimeOrStr] = None,
        attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvActivity:
        """
        Creates a new end record for this activity.

        :param trigger: Entity triggering the end of this activity.
        :param ender: Optionally extra activity to state a qualified end through
            which the trigger entity for the end is generated (default: None).
        :param time: Optional time for the end (default: None).
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        :param attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
        """
        self._bundle.end(self, trigger, ender, time, other_attributes=attributes)
        return self

    def wasAssociatedWith(
        self,
        agent: AgentRef,
        plan: Optional[EntityRef] = None,
        attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvActivity:
        """
        Creates a new association record for this activity.

        :param agent: Agent or string identifier of the agent involved in the
            association (default: None).
        :param plan: Optionally extra entity to state qualified association through
            an internal plan (default: None).
        :param attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        activity: Optional[ActivityRef] = None,
        attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvAgent:
        """
        Creates a new delegation record on behalf of this agent.

        :param responsible: Agent the responsibility is delegated to.
        :param activity: Optionally extra activity to state qualified delegation
            internally (default: None).
        :param attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
class NamespaceManager(dict):
    """Manages namespaces for PROV documents and bundles."""

    parent = None  # type: Optional[NamespaceManager]
    """Parent :py:class:`NamespaceManager` this manager one is a child of."""

    def __init__(
        self,
        namespaces: Optional[NSCollection] = None,
        default: Optional[str] = None,
        parent: Optional[NamespaceManager] = None,
    ):
        """
        Constructor.

        :param namespaces: Optional namespaces to add to the manager
            (default: None).
        :param default: Optional default namespace to use (default: None).
        :param parent: Optional parent :py:class:`NamespaceManager` to make this
            namespace manager a child of (default: None).
        """
        dict.__init__(self)
        self._default_namespaces = DEFAULT_NAMESPACES
        self.update(self._default_namespaces)
        self._namespaces = {}  # type: dict[str, Namespace]

        if default is not None:
            self.set_default_namespace(default)
        else:
            self._default = None  # type: Optional[Namespace]
        self.parent = parent
        #  TODO check if default is in the default namespaces
        self._anon_id_count = 0
        self._uri_map = dict()  # type: dict[str, Namespace]
        self._rename_map = dict()  # type: dict[Namespace, Namespace]
        self._prefix_renamed_map = dict()  # type: dict[str, Namespace]
        if namespaces is not None:
            self.add_namespaces(namespaces)

    def get_namespace(self, uri: str) -> Namespace | None:
        """
        Returns the namespace prefix for the given URI.

        :param uri: Namespace URI.
        :return: :py:class:`~prov.identifier.Namespace`.
        """
        for namespace in self.values():
            if uri == namespace._uri:
                return namespace
        return None

    def get_registered_namespaces(self) -> Iterable[Namespace]:
        """
        Returns all registered namespaces.

        :return: Iterable of :py:class:`~prov.identifier.Namespace`.
        """
        return self._namespaces.values()

    def set_default_namespace(self, uri: str) -> None:
        """
        Sets the default namespace to the one of a given URI.

        :param uri: Namespace URI.
        """
        self._default = Namespace("", uri)
        self[""] = self._default

    def get_default_namespace(self) -> Namespace | None:
        """
        Returns the default namespace.

        :return: :py:class:`~prov.identifier.Namespace`
        """
        return self._default

    def add_namespace(self, namespace: Namespace) -> Namespace:
        """
        Adds a namespace (if not available, yet).

        :param namespace: :py:class:`~prov.identifier.Namespace` to add.
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
        """
        Add multiple namespaces into this manager.

        :param namespaces: A collection of namespace(s) to add.
        :type namespaces: List of :py:class:`~prov.identifier.Namespace` or
            dict of {prefix: uri}.
        :returns: None
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
        """
        Resolves an identifier to a valid qualified name.

        :param qname: Qualified name as :py:class:`~prov.identifier.QualifiedName`
            or a tuple (namespace, identifier).
        :return: :py:class:`~prov.identifier.QualifiedName` or None in case of
            failure.
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
        """
        Returns an anonymous identifier (without a namespace prefix).

        :param local_prefix: Optional local namespace prefix as a string
            (default: 'id').
        :return: :py:class:`~prov.identifier.Identifier`
        """
        self._anon_id_count += 1
        return Identifier("_:%s%d" % (local_prefix, self._anon_id_count))

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


class ProvBundle(object):
    """PROV Bundle"""

    def __init__(
        self,
        records: Optional[Iterable[ProvRecord]] = None,
        identifier: Optional[QualifiedName] = None,
        namespaces: Optional[NSCollection] = None,
        document: Optional["ProvDocument"] = None,
    ):
        """
        Constructor.

        :param records: Optional iterable of records to add to the bundle
            (default: None).
        :param identifier: Optional identifier of the bundle (default: None).
        :param namespaces: Optional iterable of :py:class:`~prov.identifier.Namespace`s
            to set the document up with (default: None).
        :param document: Optional document to add to the bundle (default: None).
        """
        #  Initializing bundle-specific attributes
        self._identifier = identifier
        self._records = list()  # type: list[ProvRecord]
        self._id_map = defaultdict(list)  # type: dict[QualifiedName, list[ProvRecord]]
        self._document = document
        self._namespaces = NamespaceManager(
            namespaces, parent=(document._namespaces if document is not None else None)
        )  # type: NamespaceManager
        if records:
            for record in records:
                self.add_record(record)

    def __repr__(self) -> str:
        return "<%s: %s>" % (self.__class__.__name__, self._identifier)

    @property
    def namespaces(self) -> set[Namespace]:
        """
        Returns the set of registered namespaces.

        :return: Set of :py:class:`~prov.identifier.Namespace`.
        """
        return set(self._namespaces.get_registered_namespaces())

    @property
    def default_ns_uri(self) -> str | None:
        """
        Returns the default namespace's URI, if any.

        :return: URI as string.
        """
        default_ns = self._namespaces.get_default_namespace()
        return default_ns.uri if default_ns else None

    @property
    def document(self) -> ProvDocument | None:
        """
        Returns the parent document, if any.

        :return: :py:class:`ProvDocument`.
        """
        return self._document

    @property
    def identifier(self) -> QualifiedName | None:
        """
        Returns the bundle's identifier
        """
        return self._identifier

    @property
    def records(self) -> list[ProvRecord]:
        """
        Returns the list of all records in the current bundle
        """
        return list(self._records)

    #  Bundle configurations
    def set_default_namespace(self, uri: str) -> None:
        """
        Sets the default namespace through a given URI.

        :param uri: Namespace URI.
        """
        self._namespaces.set_default_namespace(uri)

    def get_default_namespace(self) -> Namespace | None:
        """
        Returns the default namespace.

        :return: :py:class:`~prov.identifier.Namespace`
        """
        return self._namespaces.get_default_namespace()

    def add_namespace(
        self, namespace_or_prefix: Namespace | str, uri: Optional[str] = None
    ) -> Namespace:
        """
        Adds a namespace (if not available, yet).

        :param namespace_or_prefix: :py:class:`~prov.identifier.Namespace` or its
            prefix as a string to add.
        :param uri: Namespace URI (default: None). Must be present if only a
            prefix is given in the previous parameter.
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
        """
        Returns all registered namespaces.

        :return: Iterable of :py:class:`~prov.identifier.Namespace`.
        """
        return self._namespaces.get_registered_namespaces()

    def valid_qualified_name(
        self, identifier: QualifiedNameCandidate
    ) -> Optional[QualifiedName]:
        return self._namespaces.valid_qualified_name(identifier)

    def mandatory_valid_qname(
        self, identifier: QualifiedNameCandidate
    ) -> QualifiedName:
        """
        Determines if the given identifier is a valid qualified name and returns it.
        If the provided identifier is not valid, an exception is raised.
        """
        valid_qname = self.valid_qualified_name(identifier)
        if valid_qname is not None:
            return valid_qname
        else:
            raise ProvExceptionInvalidQualifiedName(identifier)

    def get_records(
        self, class_or_type_or_tuple: Optional[type | tuple[type]] = None
    ) -> Iterable[ProvRecord]:
        """
        Returns all records. Returned records may be filtered by the optional
        argument.

        :param class_or_type_or_tuple: A filter on the type for which records are
            to be returned (default: None). The filter checks by the type of the
            record using the `isinstance` check on the record.
        :return: List of :py:class:`ProvRecord` objects.
        """
        results = list(self._records)  # make a (shallow) copy of the record list
        if class_or_type_or_tuple:
            return filter(lambda rec: isinstance(rec, class_or_type_or_tuple), results)
        else:
            return results

    def get_record(self, identifier: QualifiedNameCandidate) -> list[ProvRecord]:
        """
        Returns one or more records matching a given identifier.

        :param identifier: Record identifier.
        :return: List of :py:class:`ProvRecord`
        """
        valid_id = self.valid_qualified_name(identifier)
        return list(self._id_map[valid_id]) if valid_id is not None else []

    # Miscellaneous functions
    def is_document(self) -> bool:
        """
        `True` if the object is a document, `False` otherwise.

        :return: bool
        """
        return False

    def is_bundle(self) -> bool:
        """
        `True` if the object is a bundle, `False` otherwise.

        :return: bool
        """
        return True

    def has_bundles(self) -> bool:
        """
        `True` if the object has at least one bundle, `False` otherwise.

        :return: bool
        """
        return False

    @property
    def bundles(self) -> Iterable[ProvBundle]:
        """
        Returns bundles contained in the document

        :return: Iterable of :py:class:`ProvBundle`.
        """
        raise ProvException("A PROV bundle does not contain sub-bundles")

    def get_provn(self, _indent_level: int = 0) -> str:
        """
        Returns the PROV-N representation of the bundle.

        :return: String
        """
        indentation = "" + ("  " * _indent_level)
        newline = "\n" + ("  " * (_indent_level + 1))

        #  if this is the document, start the document;
        # otherwise, start the bundle
        lines = ["document"] if self.is_document() else ["bundle %s" % self._identifier]

        default_namespace = self._namespaces.get_default_namespace()
        if default_namespace:
            lines.append("default <%s>" % default_namespace.uri)

        registered_namespaces = self._namespaces.get_registered_namespaces()
        if registered_namespaces:
            lines.extend(
                [
                    "prefix %s <%s>" % (namespace.prefix, namespace.uri)
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

    __hash__ = None  # type: ignore

    # type: ignore # type: ignore # Transformations
    def _unified_records(self) -> list[ProvRecord]:
        """Returns a list of unified records."""
        # TODO: Check unification rules in the PROV-CONSTRAINTS document
        # This method simply merges the records having the same name
        merged_records = dict()
        for identifier, records in self._id_map.items():
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
        unified_records = list()
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
        """
        Unifies all records in the bundle that haves same identifiers

        :returns: :py:class:`ProvBundle` -- the new unified bundle.
        """
        unified_records = self._unified_records()
        bundle = ProvBundle(records=unified_records, identifier=self.identifier)
        return bundle

    def update(self, other: ProvBundle) -> None:
        """
        Append all the records of the *other* ProvBundle into this bundle.

        :param other: the other bundle whose records to be appended.
        :type other: :py:class:`ProvBundle`
        :returns: None.
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
                "instance (%s)" % type(other)
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
        attributes: Optional[RecordAttributesArg] = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvRecord:
        """
        Creates a new record.

        :param record_type: Type of record (one of :py:const:`PROV_REC_CLS`).
        :param identifier: Identifier for new record.
        :param attributes: Attributes as a dictionary or list of tuples to be added
            to the record optionally (default: None).
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        """
        Adds a new record that to the bundle.

        :param record: :py:class:`ProvRecord` to be added.
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
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvEntity:
        """
        Creates a new entity.

        :param identifier: Identifier for new entity.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
        """
        return self.new_record(PROV_ENTITY, identifier, None, other_attributes)  # type: ignore

    def activity(
        self,
        identifier: QualifiedNameCandidate,
        startTime: Optional[DatetimeOrStr] = None,
        endTime: Optional[DatetimeOrStr] = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvActivity:
        """
        Creates a new activity.

        :param identifier: Identifier for new activity.
        :param startTime: Optional start time for the activity (default: None).
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        :param endTime: Optional start time for the activity (default: None).
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        activity: Optional[ActivityRef] = None,
        time: Optional[DatetimeOrStr] = None,
        identifier: OptionalID = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvRecord:
        """
        Creates a new generation record for an entity.

        :param entity: Entity or a string identifier for the entity.
        :param activity: Activity or string identifier of the activity involved in
            the generation (default: None).
        :param time: Optional time for the generation (default: None).
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        :param identifier: Identifier for new generation record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        entity: Optional[EntityRef] = None,
        time: Optional[DatetimeOrStr] = None,
        identifier: OptionalID = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvUsage:
        """
        Creates a new usage record for an activity.

        :param activity: Activity or a string identifier for the entity.
        :param entity: Entity or string identifier of the entity involved in
            the usage relationship (default: None).
        :param time: Optional time for the usage (default: None).
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        :param identifier: Identifier for new usage record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        trigger: Optional[EntityRef] = None,
        starter: Optional[ActivityRef] = None,
        time: Optional[DatetimeOrStr] = None,
        identifier: OptionalID = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvStart:
        """
        Creates a new start record for an activity.

        :param activity: Activity or a string identifier for the entity.
        :param trigger: Entity triggering the start of this activity.
        :param starter: Optionally extra activity to state a qualified start
            through which the trigger entity for the start is generated
            (default: None).
        :param time: Optional time for the start (default: None).
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        :param identifier: Identifier for new start record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        trigger: Optional[EntityRef] = None,
        ender: Optional[ActivityRef] = None,
        time: Optional[DatetimeOrStr] = None,
        identifier: OptionalID = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvEnd:
        """
        Creates a new end record for an activity.

        :param activity: Activity or a string identifier for the entity.
        :param trigger: trigger: Entity triggering the end of this activity.
        :param ender: Optionally extra activity to state a qualified end
            through which the trigger entity for the end is generated
            (default: None).
        :param time: Optional time for the end (default: None).
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        :param identifier: Identifier for new end record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        activity: Optional[ActivityRef] = None,
        time: Optional[DatetimeOrStr] = None,
        identifier: OptionalID = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvInvalidation:
        """
        Creates a new invalidation record for an entity.

        :param entity: Entity or a string identifier for the entity.
        :param activity: Activity or string identifier of the activity involved in
            the invalidation (default: None).
        :param time: Optional time for the invalidation (default: None).
            Either a :py:class:`datetime.datetime` object or a string that can be
            parsed by :py:func:`dateutil.parser`.
        :param identifier: Identifier for the new invalidation record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvCommunication:
        """
        Creates a new communication record for an entity.

        :param informed: The informed activity (relationship destination).
        :param informant: The informing activity (relationship source).
        :param identifier: Identifier for new communication record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvAgent:
        """
        Creates a new agent.

        :param identifier: Identifier for new agent.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
        """
        return self.new_record(PROV_AGENT, identifier, None, other_attributes)  # type: ignore

    def attribution(
        self,
        entity: EntityRef,
        agent: AgentRef,
        identifier: OptionalID = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvAttribution:
        """
        Creates a new attribution record between an entity and an agent.

        :param entity: Entity or a string identifier for the entity (relationship
            source).
        :param agent: Agent or string identifier of the agent involved in the
            attribution (relationship destination).
        :param identifier: Identifier for new attribution record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        agent: Optional[AgentRef] = None,
        plan: Optional[EntityRef] = None,
        identifier: OptionalID = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvAssociation:
        """
        Creates a new association record for an activity.

        :param activity: Activity or a string identifier for the activity.
        :param agent: Agent or string identifier of the agent involved in the
            association (default: None).
        :param plan: Optionally extra entity to state qualified association through
            an internal plan (default: None).
        :param identifier: Identifier for new association record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        activity: Optional[ActivityRef] = None,
        identifier: OptionalID = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvDelegation:
        """
        Creates a new delegation record on behalf of an agent.

        :param delegate: Agent delegating the responsibility (relationship source).
        :param responsible: Agent the responsibility is delegated to (relationship
            destination).
        :param activity: Optionally extra activity to state qualified delegation
            internally (default: None).
        :param identifier: Identifier for new association record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvInfluence:
        """
        Creates a new influence record between two entities, activities or agents.

        :param influencee: Influenced entity, activity or agent (relationship
            source).
        :param influencer: Influencing entity, activity or agent (relationship
            destination).
        :param identifier: Identifier for new influence record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        activity: Optional[ActivityRef] = None,
        generation: Optional[GenrationRef] = None,
        usage: Optional[UsageRef] = None,
        identifier: OptionalID = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvDerivation:
        """
        Creates a new derivation record for a generated entity from a used entity.

        :param generatedEntity: Entity or a string identifier for the generated
            entity (relationship source).
        :param usedEntity: Entity or a string identifier for the used entity
            (relationship destination).
        :param activity: Activity or string identifier of the activity involved in
            the derivation (default: None).
        :param generation: Optionally extra activity to state qualified generation
            through a generation (default: None).
        :param usage: XXX (default: None).
        :param identifier: Identifier for new derivation record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        activity: Optional[ActivityRef] = None,
        generation: Optional[GenrationRef] = None,
        usage: Optional[UsageRef] = None,
        identifier: OptionalID = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvDerivation:
        """
        Creates a new revision record for a generated entity from a used entity.

        :param generatedEntity: Entity or a string identifier for the generated
            entity (relationship source).
        :param usedEntity: Entity or a string identifier for the used entity
            (relationship destination).
        :param activity: Activity or string identifier of the activity involved in
            the revision (default: None).
        :param generation: Optionally to state qualified revision through a
            generation activity (default: None).
        :param usage: XXX (default: None).
        :param identifier: Identifier for new revision record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        activity: Optional[ActivityRef] = None,
        generation: Optional[GenrationRef] = None,
        usage: Optional[UsageRef] = None,
        identifier: OptionalID = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvDerivation:
        """
        Creates a new quotation record for a generated entity from a used entity.

        :param generatedEntity: Entity or a string identifier for the generated
            entity (relationship source).
        :param usedEntity: Entity or a string identifier for the used entity
            (relationship destination).
        :param activity: Activity or string identifier of the activity involved in
            the quotation (default: None).
        :param generation: Optionally to state qualified quotation through a
            generation activity (default: None).
        :param usage: XXX (default: None).
        :param identifier: Identifier for new quotation record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        activity: Optional[ActivityRef] = None,
        generation: Optional[GenrationRef] = None,
        usage: Optional[UsageRef] = None,
        identifier: OptionalID = None,
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvDerivation:
        """
        Creates a new primary source record for a generated entity from a used
        entity.

        :param generatedEntity: Entity or a string identifier for the generated
            entity (relationship source).
        :param usedEntity: Entity or a string identifier for the used entity
            (relationship destination).
        :param activity: Activity or string identifier of the activity involved in
            the primary source (default: None).
        :param generation: Optionally to state qualified primary source through a
            generation activity (default: None).
        :param usage: XXX (default: None).
        :param identifier: Identifier for new primary source record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
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
        return record  # type: ignore

    def specialization(
        self, specificEntity: EntityRef, generalEntity: EntityRef
    ) -> ProvSpecialization:
        """
        Creates a new specialisation record for a specific from a general entity.

        :param specificEntity: Entity or a string identifier for the specific
            entity (relationship source).
        :param generalEntity: Entity or a string identifier for the general entity
            (relationship destination).
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
        """
        Creates a new alternate record between two entities.

        :param alternate1: Entity or a string identifier for the first entity
            (relationship source).
        :param alternate2: Entity or a string identifier for the second entity
            (relationship destination).
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
        """
        Creates a new mention record for a specific from a general entity.

        :param specificEntity: Entity or a string identifier for the specific
            entity (relationship source).
        :param generalEntity: Entity or a string identifier for the general entity
            (relationship destination).
        :param bundle: XXX
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
        other_attributes: Optional[RecordAttributesArg] = None,
    ) -> ProvEntity:
        """
        Creates a new collection record for a particular record.

        :param identifier: Identifier for new collection record.
        :param other_attributes: Optional other attributes as a dictionary or list
            of tuples to be added to the record optionally (default: None).
        """
        record = self.new_record(PROV_ENTITY, identifier, None, other_attributes)
        record.add_asserted_type(PROV["Collection"])
        return record  # type: ignore

    def membership(self, collection: EntityRef, entity: EntityRef) -> ProvMembership:
        """
        Creates a new membership record for an entity to a collection.

        :param collection: Collection the entity is to be added to.
        :param entity: Entity to be added to the collection.
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
        filename: Optional[PathLike] = None,
        show_nary: bool = True,
        use_labels: bool = False,
        show_element_attributes: bool = True,
        show_relation_attributes: bool = True,
    ) -> None:
        """
        Convenience function to plot a PROV document.

        :param filename: The filename to save to. If not given, it will open
            an interactive matplotlib plot. The filetype is determined from
            the filename ending.
        :type filename: String
        :param show_nary: Shows all elements in n-ary relations.
        :type show_nary: bool
        :param use_labels: Uses the `prov:label` property of an element as its
            name (instead of its identifier).
        :type use_labels: bool
        :param show_element_attributes: Shows attributes of elements.
        :type show_element_attributes: bool
        :param show_relation_attributes: Shows attributes of relations.
        :type show_relation_attributes: bool
        """
        # Lazy imports to have soft dependencies on pydot and matplotlib
        # (imported even later).
        from prov import dot

        if filename:
            format = str(os.path.splitext(filename))[-1].lower().strip(os.path.extsep)
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
        method = "create_%s" % format
        if not hasattr(d, method):
            raise ValueError("Format '%s' cannot be saved." % format)
        with io.BytesIO() as buf:
            buf.write(getattr(d, method)())

            buf.seek(0, 0)
            if filename:
                with open(filename, "wb") as fh:
                    fh.write(buf.read())
            else:
                # Use matplotlib to show the image as it likely is more
                # widespread than PIL and works nicely in the ipython notebook.
                import matplotlib.pylab as plt  # type: ignore
                import matplotlib.image as mpimg  # type: ignore

                max_size = 30

                img = mpimg.imread(buf)
                # pydot makes a border around the image. remove it.
                img = img[1:-1, 1:-1]
                size = (img.shape[1] / 100.0, img.shape[0] / 100.0)
                if max(size) > max_size:
                    scale = max_size / max(size)
                else:
                    scale = 1.0
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
        records: Optional[Iterable[ProvRecord]] = None,
        namespaces: Optional[NSCollection] = None,
    ):
        """
        Constructor.

        :param records: Optional records to add to the document (default: None).
        :param namespaces: Optional iterable of :py:class:`~prov.identifier.Namespace`s
            to set the document up with (default: None).
        """
        ProvBundle.__init__(
            self, records=records, identifier=None, namespaces=namespaces
        )
        self._bundles = dict()  # type: dict[QualifiedName, ProvBundle]

    def __repr__(self) -> str:
        return "<ProvDocument>"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ProvDocument):
            return False
        # Comparing the documents' content
        if not super(ProvDocument, self).__eq__(other):
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
        """
        `True` if the object is a document, `False` otherwise.

        :return: bool
        """
        return True

    def is_bundle(self) -> bool:
        """
        `True` if the object is a bundle, `False` otherwise.

        :return: bool
        """
        return False

    def has_bundles(self) -> bool:
        """
        `True` if the object has at least one bundle, `False` otherwise.

        :return: bool
        """
        return len(self._bundles) > 0

    @property
    def bundles(self) -> Iterable[ProvBundle]:
        """
        Returns bundles contained in the document

        :return: Iterable of :py:class:`ProvBundle`.
        """
        return self._bundles.values()

    # Transformations
    def flattened(self) -> ProvDocument:
        """
        Flattens the document by moving all the records in its bundles up
        to the document level.

        :returns: :py:class:`ProvDocument` -- the (new) flattened document.
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
        """
        Returns a new document containing all records having the same identifiers
        unified (including those inside bundles).

        :return: :py:class:`ProvDocument`
        """
        document = ProvDocument(self._unified_records())
        document._namespaces = self._namespaces
        for bundle in self.bundles:
            unified_bundle = bundle.unified()
            document.add_bundle(unified_bundle)
        return document

    def update(self, other: ProvBundle) -> None:
        """
        Append all the records of the *other* document/bundle into this document.
        Bundles having the same identifiers will be merged.

        :param other: The other document/bundle whose records to be appended.
        :type other: :py:class:`ProvDocument` or :py:class:`ProvBundle`
        :returns: None.
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
                "ProvBundle instance (%s)" % type(other)
            )

    # Bundle operations
    def add_bundle(
        self, bundle: ProvBundle, identifier: Optional[QualifiedName] = None
    ) -> None:
        """
        Add a bundle to the current document.

        :param bundle: The bundle to add to the document.
        :type bundle: :py:class:`ProvBundle`
        :param identifier: The (optional) identifier to use for the bundle
            (default: None). If none given, use the identifier from the bundle
            itself.
        """
        if not isinstance(bundle, ProvBundle):
            raise ProvException(
                "Only a ProvBundle instance can be added as a bundle in a "
                "ProvDocument."
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
        """
        Returns a new bundle from the current document.

        :param identifier: The identifier to use for the bundle.
        :return: :py:class:`ProvBundle`
        """
        if identifier is None:
            raise ProvException(
                "An identifier is required. Cannot create an unnamed bundle."
            )
        valid_id = self.valid_qualified_name(identifier)
        if valid_id is None:
            raise ProvException(
                'The provided identifier "%s" is not valid' % identifier
            )
        if valid_id in self._bundles:
            raise ProvException("A bundle with that identifier already exists")
        b = ProvBundle(identifier=valid_id, document=self)
        self._bundles[valid_id] = b
        return b

    # Serializing and deserializing
    def serialize(
        self,
        destination: Optional[io.IOBase | PathLike] = None,
        format: str = "json",
        **args: Any,
    ) -> str | None:
        """
        Serialize the :py:class:`ProvDocument` to the destination.

        Available serializers can be queried by the value of
        `:py:attr:~prov.serializers.Registry.serializers` after loading them via
        `:py:func:~prov.serializers.Registry.load_serializers()`.

        :param destination: Stream object to serialize the output to. Default is
            `None`, which serializes as a string.
        :param format: Serialization format (default: 'json'), defaulting to
            PROV-JSON.
        :return: Serialization in a string if no destination was given,
            None otherwise.
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
            scheme, netloc, path, params, _query, fragment = urlparse(location)
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
        source: Optional[io.IOBase | PathLike] = None,
        content: Optional[str | bytes] = None,
        format: str = "json",
        **args: Any,
    ) -> ProvDocument:
        """
        Deserialize the :py:class:`ProvDocument` from source (a stream or a
        file path) or directly from a string content.

        Available serializers can be queried by the value of
        `:py:attr:~prov.serializers.Registry.serializers` after loading them via
        `:py:func:~prov.serializers.Registry.load_serializers()`.

        Note: Not all serializers support deserialization.

        :param source: Stream object to deserialize the PROV document from
            (default: None).
        :param content: String to deserialize the PROV document from
            (default: None).
        :param format: Serialization format (default: 'json'), defaulting to
            PROV-JSON.
        :return: :py:class:`ProvDocument`
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
    """
    Helper function sorting attributes into the order required by PROV-XML.

    :param element: The prov element used to derive the type and the
        attribute order for the type.
    :param attributes: The attributes to sort.
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
