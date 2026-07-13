"""PROV bundles and documents: containers of PROV records."""

from __future__ import annotations  # needed for | type annotations in Python < 3.10

import io
import itertools
import logging
import os
import shutil
import tempfile
import warnings
from collections import defaultdict
from collections.abc import Iterable
from typing import IO, Any, cast
from urllib.parse import urlparse

from prov import serializers
from prov.constants import (
    PROV,
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
    PROV_ATTRIBUTION,
    PROV_COMMUNICATION,
    PROV_DELEGATION,
    PROV_DERIVATION,
    PROV_END,
    PROV_ENTITY,
    PROV_GENERATION,
    PROV_INFLUENCE,
    PROV_INVALIDATION,
    PROV_LABEL,
    PROV_LOCATION,
    PROV_MEMBERSHIP,
    PROV_MENTION,
    PROV_ROLE,
    PROV_SPECIALIZATION,
    PROV_START,
    PROV_TYPE,
    PROV_USAGE,
    PROV_VALUE,
)
from prov.identifier import Namespace, QualifiedName
from prov.model.namespaces import NamespaceManager
from prov.model.records import (
    PROV_REC_CLS,
    ActivityRef,
    AgentRef,
    DatetimeOrStr,
    EntityRef,
    GenrationRef,
    NameValuePair,
    NSCollection,
    OptionalID,
    PathLike,
    ProvActivity,
    ProvAgent,
    ProvAlternate,
    ProvAssociation,
    ProvAttribution,
    ProvCommunication,
    ProvDelegation,
    ProvDerivation,
    ProvEnd,
    ProvEntity,
    ProvException,
    ProvExceptionInvalidQualifiedName,
    ProvInfluence,
    ProvInvalidation,
    ProvMembership,
    ProvMention,
    ProvRecord,
    ProvSpecialization,
    ProvStart,
    ProvUsage,
    QualifiedNameCandidate,
    RecordAttributesArg,
    UsageRef,
    _ensure_datetime,
)

logger = logging.getLogger(__name__)


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
        warnings.warn(
            "prov 3.0 will change unified() to merge records per the W3C "
            "PROV-CONSTRAINTS rules; records sharing an identifier but having "
            "conflicting formal attributes will then raise an error instead of "
            "having their attributes silently unioned. See "
            "https://github.com/trungdong/prov/blob/master/ROADMAP.md",
            FutureWarning,
            stacklevel=2,
        )
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
            img_format = (
                str(os.path.splitext(filename)[-1]).lower().strip(os.path.extsep)
            )
        else:
            img_format = "png"
        img_format = img_format.lower()
        d = dot.prov_to_dot(
            self,
            show_nary=show_nary,
            use_labels=use_labels,
            show_element_attributes=show_element_attributes,
            show_relation_attributes=show_relation_attributes,
        )
        method = f"create_{img_format}"
        if not hasattr(d, method):
            raise ValueError(f"Format '{img_format}' cannot be saved.")
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
        warnings.warn(
            "prov 3.0 will change unified() to merge records per the W3C "
            "PROV-CONSTRAINTS rules; records sharing an identifier but having "
            "conflicting formal attributes will then raise an error instead of "
            "having their attributes silently unioned. See "
            "https://github.com/trungdong/prov/blob/master/ROADMAP.md",
            FutureWarning,
            stacklevel=2,
        )
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
                    if (
                        bundle_id is None
                    ):  # pragma: no cover -- bundles are always named
                        raise AssertionError("bundle has no identifier")
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
        destination: io.IOBase | IO[Any] | PathLike | None = None,
        format: str = "json",
        **args: Any,
    ) -> str | None:
        """Serialize this document to a destination or return it as a string.

        The available serialization formats are ``"json"``, ``"rdf"``, ``"xml"``
        and ``"provn"`` (see :func:`prov.serializers.get`).

        Args:
            destination: A writable stream (any object with a ``write``
                method) or a local file path to write to. If ``None``, the
                serialization is returned as a string (default: ``None``). A
                non-local (network) location is not written and yields
                ``None``.
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

        # Duck-type on write() rather than isinstance(..., io.IOBase): common
        # file-like wrappers such as tempfile.NamedTemporaryFile's
        # _TemporaryFileWrapper proxy a stream's write() but are not
        # themselves io.IOBase instances (#240).
        if hasattr(destination, "write"):
            stream = cast(io.IOBase, destination)
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
        source: io.IOBase | IO[Any] | PathLike | None = None,
        content: str | bytes | None = None,
        format: str = "json",
        **args: Any,
    ) -> ProvDocument:
        """Deserialize a document from a source stream/file or a string.

        Exactly one of ``source`` or ``content`` should be given; ``content``
        takes precedence if both are. Note that not all formats support
        deserialization (PROV-N is write-only).

        Args:
            source: A readable stream (any object with a ``read`` method) or
                a file path to read from (default: ``None``).
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
            # Duck-type on read() rather than isinstance(..., io.IOBase): see
            # the matching comment in serialize() (#240).
            if hasattr(source, "read"):
                return serializer.deserialize(cast(io.IOBase, source), **args)
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
