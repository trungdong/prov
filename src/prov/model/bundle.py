"""PROV bundles and documents: containers of PROV records."""

from __future__ import annotations  # defer eval: ProvDocument used before it's defined

import io
import itertools
import os
import re
import shutil
import tempfile
from collections import defaultdict
from collections.abc import Iterable, Iterator, ValuesView
from operator import attrgetter
from typing import Any, TypeVar, cast, overload
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
    PROV_BASE_CLS,
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
    AttributePair,
    DatetimeOrStr,
    EntityRef,
    GenerationRef,
    InfluencerRef,
    Literal,
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
    ProvUnificationError,
    ProvUsage,
    QualifiedNameCandidate,
    RecordAttributesArg,
    StreamOrPath,
    UsageRef,
    _attribute_pairs,
    _ensure_datetime,
)

_PROVN_IRI_FORBIDDEN = re.compile(r'[<>"{}|^`\\\x00-\x20]')


def _check_provn_iri(namespace: Namespace) -> None:
    """A namespace URI must be a PROV-N IRI_REF ([56]) to be declared."""
    if _PROVN_IRI_FORBIDDEN.search(namespace.uri):
        where = (
            f"prefix '{namespace.prefix}'"
            if namespace.prefix
            else "the default namespace"
        )
        raise ProvException(
            f"{where} has URI <{namespace.uri}>, which PROV-N cannot write as an IRI: "
            'it contains a space, a control character or one of <>"{}|^`\\'
        )


def _held_names(record: ProvRecord) -> Iterator[Any]:
    """The identifier, attribute names and values of ``record``, a literal
    standing for its datatype."""
    yield record.identifier
    for name, value in record.attributes:
        yield name
        yield value.datatype if isinstance(value, Literal) else value


def _held_qualified_names(records: Iterable[ProvRecord]) -> Iterator[QualifiedName]:
    """Every qualified name the records hold."""
    for record in records:
        for item in _held_names(record):
            if isinstance(item, QualifiedName):
                yield item


def _clashing_name(
    names: Iterable[QualifiedName], prefix: str, uri: str
) -> QualifiedName | None:
    """The first of ``names`` in ``prefix`` whose IRI is not under ``uri``."""
    return next(
        (n for n in names if n.namespace.prefix == prefix and n.namespace.uri != uri),
        None,
    )


# PROV-CONSTRAINTS (https://www.w3.org/TR/prov-constraints/) type compatibility
# for same-identifier records of *different* base types. §6.3 makes typeOf(id)
# a SET: an identifier may legitimately carry more than one type, so mixing
# types under one id is not automatically an error -- only the specific
# combinations below are. Text transcribed from §6.4 (Impossibility
# constraints):
#
# Constraint 55 (entity-activity-disjoint): "The set of entities and
# activities are disjoint": IF 'entity' in typeOf(id) AND 'activity' in
# typeOf(id) THEN INVALID. The spec explicitly carves out agent from this:
# "There is no disjointness between entities and agents. ... one can assert
# both entity(a1) and agent(a1) in a valid PROV instance. Similarly, there is
# no disjointness between activities and agents, and one can assert both
# activity(a1) and agent(a1)".
#
# Constraint 54 (impossible-object-property-overlap): "Identifiers of
# entities, agents and activities cannot also be identifiers of properties."
# For each p in {entity, activity, agent} and each r in {used, wasGeneratedBy,
# wasInvalidatedBy, wasInfluencedBy, wasStartedBy, wasEndedBy, wasInformedBy,
# wasDerivedFrom, wasAttributedTo, wasAssociatedWith, actedOnBehalfOf}: IF
# p(id, a1,...,am) and r(id; b1,...,bn) THEN INVALID -- i.e. every object
# (element) base type is disjoint from every one of Constraint 23's eleven
# *identified* relations, enumerated explicitly below as ``_IDENTIFIED_RELATIONS``.
# Alternate/Specialization/Mention/Membership are NOT in that set -- PROV-DM's
# abstract syntax gives them no identifier parameter, so the specification has
# nothing to merge them on and no opinion on an id they happen to share with
# anything. ``_unified_records`` leaves them out of the merge
# (``_KEYLESS_RELATIONS``), so they never reach these checks.
#
# Constraint 53 (impossible-property-overlap): "identifiers of basic
# relationships are disjoint": for r != s both in {used, wasGeneratedBy,
# wasInvalidatedBy, wasStartedBy, wasEndedBy, wasInformedBy, wasAttributedTo,
# wasAssociatedWith, actedOnBehalfOf}: IF r(id; a1,...,am) and s(id;
# b1,...,bn) THEN INVALID. This pairwise-disjoint set of NINE relations is a
# proper subset of Constraint 54's eleven: it deliberately excludes
# wasDerivedFrom and wasInfluencedBy. The spec calls out wasInfluencedBy by
# name as exempt because it is a superproperty meant to share an identifier
# with a more specific relation, giving the worked example "wasInfluencedBy(
# id;e2,e1)" + "wasDerivedFrom(id;e2,e1)" as valid ("This satisfies the
# disjointness constraint."); wasDerivedFrom itself is simply absent from the
# enumerated set. So a generation and a derivation -- or a derivation and an
# influence -- sharing an identifier is *not* rejected by Constraint 53.
_OBJECT_TYPES = frozenset({PROV_ENTITY, PROV_ACTIVITY, PROV_AGENT})
_ENTITY_ACTIVITY = frozenset({PROV_ENTITY, PROV_ACTIVITY})
# Constraint 23's eleven identified relations (Constraint 54's r-set).
_IDENTIFIED_RELATIONS = frozenset(
    {
        PROV_GENERATION,
        PROV_USAGE,
        PROV_COMMUNICATION,
        PROV_START,
        PROV_END,
        PROV_INVALIDATION,
        PROV_DERIVATION,
        PROV_ATTRIBUTION,
        PROV_ASSOCIATION,
        PROV_DELEGATION,
        PROV_INFLUENCE,
    }
)
# Constraint 53's nine pairwise-disjoint relations -- see the comment above.
_PAIRWISE_DISJOINT_RELATIONS = _IDENTIFIED_RELATIONS - {PROV_DERIVATION, PROV_INFLUENCE}
# Relations PROV-DM and PROV-Links give no identifier; unified() never merges them.
_KEYLESS_RELATIONS = frozenset(
    {PROV_ALTERNATE, PROV_SPECIALIZATION, PROV_MENTION, PROV_MEMBERSHIP}
)


# PROV-CONSTRAINTS Table 3: the formal positions that do not expand, each with
# the position whose presence makes it expandable again (None if none). A
# derivation that names its activity has expandable generation and usage.
_NON_EXPANDABLE: dict[
    QualifiedName, tuple[tuple[QualifiedName, QualifiedName | None], ...]
] = {
    PROV_ASSOCIATION: ((PROV_ATTR_PLAN, None),),
    PROV_DERIVATION: (
        (PROV_ATTR_ACTIVITY, None),
        (PROV_ATTR_GENERATION, PROV_ATTR_ACTIVITY),
        (PROV_ATTR_USAGE, PROV_ATTR_ACTIVITY),
    ),
}


def _check_non_expandable(records: list[ProvRecord]) -> None:
    """Raise if an absent non-expandable formal meets a present one in ``records``.

    The first such position in Table 3 order raises. The table lists each
    guard before its dependants, and a guard present in only some records has
    already raised, so by the time a dependant is reached its guard is present
    in every record or in none.

    Raises:
        ProvUnificationError: Naming the records' identifier, the position and
            the present value.
    """
    positions = _NON_EXPANDABLE.get(PROV_BASE_CLS[records[0].get_type()])
    if positions is None:
        return
    formal_values = [dict(record.formal_attributes) for record in records]
    for attr_name, guard in positions:
        if guard is not None and all(
            values[guard] is not None for values in formal_values
        ):
            continue
        present = [
            values[attr_name]
            for values in formal_values
            if values[attr_name] is not None
        ]
        if present and len(present) < len(records):
            condition = " on a derivation with no activity" if guard is not None else ""
            raise ProvUnificationError(
                f"{records[0].identifier}: an absent {attr_name}{condition} "
                f"means none, so it does not unify with {present[0]}"
            )


def _incompatible_types(type_a: QualifiedName, type_b: QualifiedName) -> bool:
    """True if two distinct base record types cannot share an identifier."""
    if {type_a, type_b} == _ENTITY_ACTIVITY:
        return True  # Constraint 55
    is_object_a = type_a in _OBJECT_TYPES
    is_object_b = type_b in _OBJECT_TYPES
    is_relation_a = type_a in _IDENTIFIED_RELATIONS
    is_relation_b = type_b in _IDENTIFIED_RELATIONS
    if (is_object_a and is_relation_b) or (is_object_b and is_relation_a):
        return True  # Constraint 54: an object type vs an identified relation
    # Constraint 53: two distinct pairwise-disjoint relations. Everything else
    # (this expression's False case) is either a spec-permitted overlap
    # (agent+entity, agent+activity) or a relation pair Constraint 53 does not
    # cover, such as derivation+generation or derivation+influence.
    return (
        type_a in _PAIRWISE_DISJOINT_RELATIONS
        and type_b in _PAIRWISE_DISJOINT_RELATIONS
    )


def _unify_same_type_group(records: list[ProvRecord]) -> ProvRecord:
    """Merge same-type records sharing an identifier by term unification.

    Formal attributes are unified positionally: an absent value is an
    existential ("unknown") that unifies with anything, equal concrete values
    unify, and two different concrete values do not unify. An absent value in
    a non-expandable position does not unify with a present one;
    ``_check_non_expandable`` raises once the merged record is built, so a
    conflict elsewhere in the records raises first. Non-formal ("extra")
    attributes are unioned. The merged record is newly constructed from the
    unified formal attributes, so no *formal-attribute* conflict is ever routed
    through :meth:`ProvRecord.add_attributes`' single-value guard -- a conflict
    between two records' *extra* attributes still is, since those are reasserted
    through the merged record's constructor unchanged.

    Args:
        records: Two or more records of the same base record type, carrying
            the same identifier, in assertion order.

    Returns:
        A single, newly created record standing for the whole group.

    Raises:
        ProvUnificationError: If two of the records hold different concrete
            values for the same formal attribute, or an absent value in a
            non-expandable position where another holds a concrete one.
    """
    first_record = records[0]
    record_type = first_record.get_type()
    identifier = first_record.identifier
    attributes: list[NameValuePair] = []
    # Same record type, hence the same FORMAL_ATTRIBUTES: zip() lines the
    # records' formal attributes up position by position.
    for pairs in zip(*(record.formal_attributes for record in records), strict=True):
        attr_name = pairs[0][0]
        unified_value = None
        for _, value in pairs:
            if value is None:
                # An absent formal attribute is an existential variable. The
                # model cannot express PROV-N's placeholder `-`, so absent
                # unifies with any concrete value; the non-expandable positions
                # are checked after the merge.
                continue
            if unified_value is None:
                unified_value = value
                continue
            # Every formal attribute is in PROV_ATTRIBUTES, so add_attributes
            # has already normalised its value to a QualifiedName or a
            # datetime: != is always well defined here.
            if unified_value != value:
                raise ProvUnificationError(
                    f"cannot unify {identifier}: {attr_name} has conflicting "
                    f"values {unified_value!r} and {value!r}"
                )
        if unified_value is not None:
            attributes.append((attr_name, unified_value))

    # Extra attributes keep their set-union semantics.
    for record in records:
        attributes.extend(record.extra_attributes)

    merged = PROV_REC_CLS[record_type](first_record.bundle, identifier, attributes)
    _check_non_expandable(records)
    return merged


def _unify_record_group(records: list[ProvRecord]) -> dict[ProvRecord, ProvRecord]:
    """Merge records sharing an identifier by PROV-CONSTRAINTS term unification.

    Records are first partitioned by base record type (:data:`PROV_BASE_CLS`,
    which reduces any subtyped derivation etc. to its base class). Within a
    type, :func:`_unify_same_type_group` applies. Across types, the identifier
    is only valid PROV-CONSTRAINTS usage if every pair of types present is one
    of the spec's permitted overlaps (see the compatibility table above);
    otherwise the whole group is invalid.

    Args:
        records: Two or more records carrying the same identifier, in
            assertion order.

    Returns:
        A mapping from each original record in the group to the single,
        newly created record that stands for its base type. Records of the
        same base type map to the same merged record.

    Raises:
        ProvUnificationError: If two records of the same type hold different
            concrete values for the same formal attribute, or an absent value
            in a non-expandable position where another holds a concrete one,
            or if the group spans two base record types that PROV-CONSTRAINTS'
            impossibility constraints (53/54/55) forbid combining under one
            identifier.
    """
    identifier = records[0].identifier
    groups: dict[QualifiedName, list[ProvRecord]] = defaultdict(list)
    for record in records:
        groups[PROV_BASE_CLS[record.get_type()]].append(record)

    base_types = list(groups)
    for type_a, type_b in itertools.combinations(base_types, 2):
        if _incompatible_types(type_a, type_b):
            raise ProvUnificationError(
                f"cannot unify {identifier}: incompatible types {type_a} and {type_b}"
            )

    merged_records: dict[ProvRecord, ProvRecord] = {}
    for group in groups.values():
        merged = _unify_same_type_group(group)
        for record in group:
            merged_records[record] = merged
    return merged_records


_R = TypeVar("_R", bound=ProvRecord)


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
                mapping or an iterable of :class:`~prov.identifier.Namespace`
                (default: ``None``).
            document: Optional parent document for the bundle (default:
                ``None``).
        """
        #  Initializing bundle-specific attributes
        self._identifier = identifier
        self._records: list[ProvRecord] = []
        self._id_map: dict[QualifiedName, list[ProvRecord]] = defaultdict(list)
        self._document = document
        self._namespaces: NamespaceManager = NamespaceManager(
            namespaces, parent=(document._namespaces if document is not None else None)
        )
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

        Raises:
            ProvException: If the bundle holds a name in the current default
                namespace, which the new one would make another name.
        """
        self._refuse_changed_reading("", uri)
        self._namespaces.set_default_namespace(uri)

    def _held_here(self) -> Iterator[QualifiedName]:
        """The qualified names this scope holds, its own identifier first."""
        if self._identifier is not None:
            yield self._identifier
        yield from _held_qualified_names(self._records)

    def _inheriting_bundles(self, prefix: str) -> list[ProvBundle]:
        """The bundles that read ``prefix`` through this scope."""
        return []

    def _refuse_changed_reading(self, prefix: str, uri: str) -> None:
        """Refuse a declaration that would change the IRI of a name this scope,
        or a bundle reading through it, holds."""
        for scope in [self, *self._inheriting_bundles(prefix)]:
            clash = _clashing_name(scope._held_here(), prefix, uri)
            if clash is not None:
                what = f"prefix {prefix} <{uri}>" if prefix else f"default <{uri}>"
                kind = "document" if scope.is_document() else "bundle"
                raise ProvException(
                    f"cannot declare {what}: this {kind} holds {clash}, "
                    f"which would read as {uri}{clash.localpart}"
                )

    def get_default_namespace(self) -> Namespace | None:
        """Return the default namespace, or ``None`` if none is set."""
        return self._namespaces.get_default_namespace()

    def _copy_default_from(self, source: ProvBundle) -> None:
        default = source.get_default_namespace()
        if default is not None:
            self.set_default_namespace(default.uri)

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
            ProvException: If a prefix string is given without a ``uri``, or
                the prefix is not bound here but an enclosing scope binds it
                and the bundle holds a name in that binding, which the new
                namespace would make another name.
        """
        if not isinstance(namespace_or_prefix, Namespace):
            if uri is None:
                raise ProvException("Cannot add a namespace without a URI")
            namespace_or_prefix = Namespace(namespace_or_prefix, uri)
        prefix = namespace_or_prefix.prefix
        if prefix and self._namespaces._binding(prefix) is None:
            self._refuse_changed_reading(prefix, namespace_or_prefix.uri)
        return self._namespaces.add_namespace(namespace_or_prefix)

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

        Raises:
            ProvExceptionInvalidQualifiedName: If the local part is one PROV-N
                cannot write (#524).
        """
        return self._namespaces.valid_qualified_name(identifier)

    def _lookup(self, prefix: str, local: str) -> QualifiedName | None:
        """Resolve a split name by its prefix in scope; see ``NamespaceManager.lookup``."""
        return self._namespaces.lookup(prefix, local)

    def _unresolved_reason(self, text: str) -> str:
        """Why ``text`` does not resolve in this bundle by its prefix, after
        :meth:`_lookup` returned ``None``."""
        return self._namespaces._unresolved_reason(text)

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

    @overload
    def get_records(self, class_or_type_or_tuple: type[_R]) -> list[_R]: ...

    @overload
    def get_records(
        self, class_or_type_or_tuple: tuple[type, ...] | None = None
    ) -> list[ProvRecord]: ...

    def get_records(
        self, class_or_type_or_tuple: type | tuple[type, ...] | None = None
    ) -> list[Any]:
        """Return the bundle's records, optionally filtered by type.

        Args:
            class_or_type_or_tuple: An optional class or tuple of classes; only
                records passing ``isinstance()`` against it are returned
                (default: ``None``, meaning all records).

        Returns:
            A new list of the matching :class:`ProvRecord` objects.
        """
        if class_or_type_or_tuple:
            return [
                record
                for record in self._records
                if isinstance(record, class_or_type_or_tuple)
            ]
        return list(self._records)

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
    def bundles(self) -> ValuesView[ProvBundle]:
        """The bundles contained in this object.

        Raises:
            ProvException: Always, since a plain bundle cannot contain
                sub-bundles. Only :class:`ProvDocument` overrides this.
        """
        raise ProvException("A PROV bundle does not contain sub-bundles")

    def _provn_header(self) -> str:
        if self.is_document():
            return "document"
        identifier = self._identifier
        return f"bundle {identifier.provn_bare_representation() if identifier else ''}"

    def _provn_namespace_lines(
        self,
        default_namespace: Namespace | None,
        registered_namespaces: list[Namespace],
    ) -> list[str]:
        """Return the header's ``default``/``prefix`` declaration lines.

        Checks every namespace being declared is a legal PROV-N IRI first,
        then a trailing blank line separates the declarations from the
        assertions that follow, present only when there is at least one.
        """
        for namespace in (
            [default_namespace] if default_namespace else []
        ) + registered_namespaces:
            _check_provn_iri(namespace)

        lines = [f"default <{default_namespace.uri}>"] if default_namespace else []
        lines.extend(
            f"prefix {namespace.prefix} <{namespace.uri}>"
            for namespace in registered_namespaces
        )
        if lines:
            #  a blank line between the prefixes and the assertions
            lines.append("")
        return lines

    def _enclosing_declarations(
        self,
        default_namespace: Namespace | None,
        registered_namespaces: list[Namespace],
    ) -> tuple[Namespace | None, list[Namespace]]:
        """Add the document's default when the bundle has none, and the
        document's prefixes the bundle does not rebind, so a bundle written
        alone reads."""
        own = set(map(attrgetter("prefix"), registered_namespaces))
        enclosing = cast("ProvDocument", self._document)._namespaces
        inherited = [
            namespace
            for namespace in enclosing.get_registered_namespaces()
            if namespace.prefix not in own
        ]
        return (
            default_namespace or enclosing.get_default_namespace(),
            registered_namespaces + inherited,
        )

    def get_provn(self, _indent_level: int = 0, strict: bool = False) -> str:
        """Return the PROV-N representation of the bundle.

        On a bundle inside a document, called with no indentation, the output
        also declares the document's default and prefixes the bundle does not
        bind itself, so a bundle written alone reads.

        Args:
            _indent_level: Indentation level for nested bundles.
            strict: Write output that parses under the strict PROV-N
                profile, as :meth:`ProvRecord.get_provn` describes, dropping
                what ``alternateOf``, ``specializationOf`` and ``hadMember``
                cannot carry there, with a warning each.
        """
        indentation = "" + ("  " * _indent_level)
        newline = "\n" + ("  " * (_indent_level + 1))

        #  if this is the document, start the document;
        # otherwise, start the bundle
        default_namespace = self._namespaces.get_default_namespace()
        registered_namespaces = list(self._namespaces.get_registered_namespaces())
        if _indent_level == 0 and self._document is not None:
            default_namespace, registered_namespaces = self._enclosing_declarations(
                default_namespace, registered_namespaces
            )
        record_lines = [record.get_provn(strict=strict) for record in self._records]
        lines = [self._provn_header()]
        lines.extend(
            self._provn_namespace_lines(default_namespace, registered_namespaces)
        )

        #  adding all the records
        lines.extend(record_lines)
        if self.is_document():
            # Print out bundles
            lines.extend(
                bundle.get_provn(_indent_level + 1, strict=strict)
                for bundle in self.bundles
            )
        provn_str = newline.join(lines) + "\n"

        #  closing the structure
        provn_str += indentation + (
            "endDocument" if self.is_document() else "endBundle"
        )
        return provn_str

    def __eq__(self, other: Any) -> bool:
        # Record equality agrees with record hashing, so one set comparison
        # settles it; a bundle and a document are unequal here too, for a
        # ProvBundle subclass that reaches this method first.
        return (
            isinstance(other, ProvBundle)
            and self.is_document() == other.is_document()
            and set(self.get_records()) == set(other.get_records())
        )

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    __hash__ = None  # type: ignore[assignment]

    # Transformations
    def _unified_records(self) -> list[ProvRecord]:
        """The records with same-identifier groups merged and each record
        kept once, in the order of the first occurrence."""
        merged_records: dict[ProvRecord, ProvRecord] = {}
        for records in self._id_map.values():
            if len(records) > 1:
                # Unify per base record type (usually one type, but
                # PROV-CONSTRAINTS permits an identifier to carry more than
                # one, e.g. agent + entity). PROV-DM and PROV-Links give the
                # keyless relations no identifier to merge on.
                keyed = [
                    record
                    for record in records
                    if record.get_type() not in _KEYLESS_RELATIONS
                ]
                if len(keyed) > 1:
                    merged_records.update(_unify_record_group(keyed))
        records = (
            [merged_records.get(record, record) for record in self._records]
            if merged_records
            else self._records
        )
        # dict.fromkeys keeps the first of equal records, by == and hash (#548).
        return list(dict.fromkeys(records))

    def unified(self) -> ProvBundle:
        """Return a new bundle with records sharing an identifier merged.

        For each identifier carried by more than one record, the records are
        first checked for type compatibility (W3C PROV-CONSTRAINTS'
        impossibility constraints 53, 54 and 55): an entity and an activity (or
        two distinct relation kinds, e.g. a generation and a usage) cannot
        share an identifier and raise; a spec-permitted overlap (an agent that
        is also an entity and/or an activity) is kept as separate records, one
        per type. Within each type, a single merged record is produced by the
        term unification of key constraints 22 and 23: the records' formal
        attributes are unified position by position — an absent formal
        attribute is an existential that unifies with any concrete value,
        equal concrete values unify, and two different concrete values do not
        — while their remaining attributes are unioned. In the non-expandable
        positions of PROV-CONSTRAINTS Table 3 (the plan of an association,
        the activity of a derivation, and the generation and usage of a
        derivation with no activity) an absent value means "none" and does
        not unify with a concrete value. Records with a unique identifier, or
        none, are not merged, and neither are ``alternateOf``,
        ``specializationOf``, ``mentionOf`` and ``hadMember`` records that
        share an identifier, since PROV-DM and PROV-Links give these relations
        no identifier to merge on. After the merge each record is kept once: a
        record equal to an earlier one is dropped and the earlier one keeps its
        position (#548).

        This is not the specification's full normalization: the uniqueness
        constraints keyed on something other than the record identifier
        (Constraints 24-29) are not checked and no inference is performed. The
        original bundle is left untouched.

        Returns:
            The new, unified :class:`ProvBundle`.

        Raises:
            ProvUnificationError: If two records of the same type sharing an
                identifier hold different concrete values for the same formal
                attribute, or an absent value in a non-expandable position
                where another holds a concrete one, or if two records sharing
                an identifier have incompatible types.
        """
        return self._unified_copy(self._document)

    def _unified_copy(self, document: ProvDocument | None) -> ProvBundle:
        """The unified bundle, built inside ``document``."""
        bundle = ProvBundle(
            identifier=self.identifier,
            namespaces=list(self.get_registered_namespaces()),
            document=document,
        )
        bundle._copy_default_from(self)
        for record in self._unified_records():
            bundle.add_record(record)
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
                :data:`~prov.model.PROV_REC_CLS`.
            identifier: The identifier for the new record (may be ``None`` for
                relations).
            attributes: Formal attributes of the record, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).
            other_attributes: Additional (non-formal) attributes, in the same
                forms (default: ``None``).

        Returns:
            The newly created and added :class:`ProvRecord`.
        """
        attr_list: list[AttributePair] = []
        if attributes:
            attr_list.extend(_attribute_pairs(attributes))
        if other_attributes:
            attr_list.extend(_attribute_pairs(other_attributes))
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
                a list of ``(name, value)`` pairs (default: ``None``).

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
            startTime: Optional start time, as a :class:`datetime.datetime` or an ``xsd:dateTime`` string accepted by
                :func:`~prov.model.parse_xsd_datetime`
                (default: ``None``).
            endTime: Optional end time, in the same forms (default: ``None``).
            other_attributes: Optional attributes for the activity, as a dict or
                a list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvActivity`.
        """
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_STARTTIME: _ensure_datetime(startTime),
            PROV_ATTR_ENDTIME: _ensure_datetime(endTime),
        }
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
                :class:`datetime.datetime` or an ``xsd:dateTime`` string accepted by
                :func:`~prov.model.parse_xsd_datetime` (default: ``None``).
            identifier: Optional identifier for the generation record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new generation record.
        """
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_ENTITY: entity,
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_TIME: _ensure_datetime(time),
        }
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
                an ``xsd:dateTime`` string accepted by
                :func:`~prov.model.parse_xsd_datetime`
                (default: ``None``).
            identifier: Optional identifier for the usage record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvUsage` record.
        """
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_ENTITY: entity,
            PROV_ATTR_TIME: _ensure_datetime(time),
        }
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
                an ``xsd:dateTime`` string accepted by
                :func:`~prov.model.parse_xsd_datetime`
                (default: ``None``).
            identifier: Optional identifier for the start record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvStart` record.
        """
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_TRIGGER: trigger,
            PROV_ATTR_STARTER: starter,
            PROV_ATTR_TIME: _ensure_datetime(time),
        }
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
            time: Optional time of the end, as a :class:`datetime.datetime` or an ``xsd:dateTime`` string accepted by
                :func:`~prov.model.parse_xsd_datetime`
                (default: ``None``).
            identifier: Optional identifier for the end record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvEnd` record.
        """
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_TRIGGER: trigger,
            PROV_ATTR_ENDER: ender,
            PROV_ATTR_TIME: _ensure_datetime(time),
        }
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
                :class:`datetime.datetime` or an ``xsd:dateTime`` string accepted by
                :func:`~prov.model.parse_xsd_datetime` (default: ``None``).
            identifier: Optional identifier for the invalidation record
                (default: ``None``).
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvInvalidation` record.
        """
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_ENTITY: entity,
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_TIME: _ensure_datetime(time),
        }
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
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvCommunication` record.
        """
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_INFORMED: informed,
            PROV_ATTR_INFORMANT: informant,
        }
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
            other_attributes: Optional attributes for the agent, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

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
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvAttribution` record.
        """
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_ENTITY: entity,
            PROV_ATTR_AGENT: agent,
        }
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
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvAssociation` record.
        """
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_AGENT: agent,
            PROV_ATTR_PLAN: plan,
        }
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
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvDelegation` record.
        """
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_DELEGATE: delegate,
            PROV_ATTR_RESPONSIBLE: responsible,
            PROV_ATTR_ACTIVITY: activity,
        }
        return self.new_record(
            PROV_DELEGATION,
            identifier,
            attributes,
            other_attributes,
        )  # type: ignore

    def influence(
        self,
        influencee: InfluencerRef,
        influencer: InfluencerRef,
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
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvInfluence` record.
        """
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_INFLUENCEE: influencee,
            PROV_ATTR_INFLUENCER: influencer,
        }
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
        generation: GenerationRef | None = None,
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
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

        Returns:
            The new :class:`ProvDerivation` record.
        """
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_GENERATED_ENTITY: generatedEntity,
            PROV_ATTR_USED_ENTITY: usedEntity,
            PROV_ATTR_ACTIVITY: activity,
            PROV_ATTR_GENERATION: generation,
            PROV_ATTR_USAGE: usage,
        }
        return self.new_record(
            PROV_DERIVATION, identifier, attributes, other_attributes
        )  # type: ignore

    def revision(
        self,
        generatedEntity: EntityRef,
        usedEntity: EntityRef,
        activity: ActivityRef | None = None,
        generation: GenerationRef | None = None,
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
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

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
        generation: GenerationRef | None = None,
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
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

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
        generation: GenerationRef | None = None,
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
            other_attributes: Optional extra attributes, as a dict or a
                list of ``(name, value)`` pairs (default: ``None``).

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
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_SPECIFIC_ENTITY: specificEntity,
            PROV_ATTR_GENERAL_ENTITY: generalEntity,
        }
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
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_ALTERNATE1: alternate1,
            PROV_ATTR_ALTERNATE2: alternate2,
        }
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
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_SPECIFIC_ENTITY: specificEntity,
            PROV_ATTR_GENERAL_ENTITY: generalEntity,
            PROV_ATTR_BUNDLE: bundle,
        }
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
                or a list of ``(name, value)`` pairs (default: ``None``).

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
        attributes: dict[QualifiedNameCandidate, Any] = {
            PROV_ATTR_COLLECTION: collection,
            PROV_ATTR_ENTITY: entity,
        }
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
                mapping or an iterable of :class:`~prov.identifier.Namespace`
                (default: ``None``).
        """
        ProvBundle.__init__(
            self, records=records, identifier=None, namespaces=namespaces
        )
        self._bundles: dict[QualifiedName, ProvBundle] = {}

    def __repr__(self) -> str:
        return "<ProvDocument>"

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, ProvDocument)
            and self._bundles == other._bundles
            and super().__eq__(other)
        )

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
    def bundles(self) -> ValuesView[ProvBundle]:
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
            self._refuse_flattening_other_defaults()
            # Creating a new document for all the records
            new_doc = ProvDocument(namespaces=list(self.get_registered_namespaces()))
            new_doc._copy_default_from(self)
            bundled_records = itertools.chain(
                *[b.get_records() for b in self._bundles.values()]
            )
            for record in itertools.chain(self._records, bundled_records):
                new_doc.add_record(record)
            return new_doc
        else:
            # returning the same document
            return self

    def _inheriting_bundles(self, prefix: str) -> list[ProvBundle]:
        return [
            bundle
            for bundle in self._bundles.values()
            if bundle._namespaces._binding(prefix) is None
        ]

    def _refuse_flattening_other_defaults(self) -> None:
        """Refuse to flatten a bundle whose default differs from the
        document's, since its bare names would have no spelling there."""
        own = self.default_ns_uri
        for bundle in self._bundles.values():
            default = bundle.default_ns_uri
            if default is not None and default != own:
                raise ProvException(
                    f"cannot flatten: bundle {bundle.identifier} declares default "
                    f"<{default}> while the document's is "
                    f"{'none' if own is None else f'<{own}>'}, so its bare names "
                    "have no spelling in the flat document; declare a prefix for "
                    "the namespace"
                )

    def unified(self) -> ProvDocument:
        """Return a new document with records sharing an identifier merged.

        The term unification of :meth:`ProvBundle.unified` is applied to the
        document's top-level records and, independently, to each contained
        bundle, preserving the bundle structure — as PROV-CONSTRAINTS §7.2
        requires, nothing is merged across a bundle boundary. The original
        document is left untouched.

        Returns:
            The new, unified :class:`ProvDocument`.

        Raises:
            ProvUnificationError: If two records sharing an identifier within
                the same scope hold different concrete values for the same
                formal attribute, or an absent value in a non-expandable
                position where another holds a concrete one, or have
                incompatible types (see :meth:`ProvBundle.unified`).
        """
        document = ProvDocument(namespaces=list(self.get_registered_namespaces()))
        document._copy_default_from(self)
        for record in self._unified_records():
            document.add_record(record)
        for bundle in self.bundles:
            document.add_bundle(bundle._unified_copy(document))
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
                    if bundle_id in self._bundles:
                        self._bundles[bundle_id].update(bundle)
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
                identifier collides with an existing bundle, or ``bundle``
                already belongs to another document.
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
            new_bundle = ProvBundle(namespaces=list(bundle.get_registered_namespaces()))
            new_bundle._copy_default_from(bundle)
            new_bundle.update(bundle)
            bundle = new_bundle

        if bundle._document is not None and bundle._document is not self:
            raise ProvException(
                "the bundle belongs to another document; "
                "a bundle is not moved between documents"
            )

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
    @overload
    def serialize(
        self, destination: None = None, format: str = "json", **args: Any
    ) -> str: ...

    @overload
    def serialize(
        self, destination: StreamOrPath, format: str = "json", **args: Any
    ) -> None: ...

    @overload
    def serialize(
        self, destination: StreamOrPath | None, format: str = "json", **args: Any
    ) -> str | None: ...

    def serialize(
        self,
        destination: StreamOrPath | None = None,
        format: str = "json",
        **args: Any,
    ) -> str | None:
        """Serialize this document to a destination or return it as a string.

        The available serialization formats are ``"json"``, ``"rdf"``, ``"xml"``,
        ``"provn"`` and ``"jsonld"`` (see :func:`prov.serializers.get`).

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
        source: StreamOrPath | None = None,
        content: str | bytes | None = None,
        format: str = "json",
        **args: Any,
    ) -> ProvDocument:
        """Deserialize a document from a source stream/file or a string.

        Exactly one of ``source`` or ``content`` should be given; ``content``
        takes precedence if both are.

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
                # Binary, matching serialize(path)'s UTF-8 write: every
                # deserializer accepts a binary stream, decoding it as
                # UTF-8 itself, so this must not depend on the locale
                # encoding open() would otherwise pick.
                with open(source, "rb") as f:
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
