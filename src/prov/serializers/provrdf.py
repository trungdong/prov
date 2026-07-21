"""PROV-RDF serializers for ProvDocument"""

import base64
import datetime
import io
import re
import warnings
from collections import OrderedDict
from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from typing import Any, cast

from rdflib import RDF, RDFS, XSD
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID, Dataset, Graph
from rdflib.term import BNode, Literal as RDFLiteral, Node, URIRef

import prov.model as pm
from prov import Error
from prov.constants import (
    PROV,
    PROV_ALTERNATE,
    PROV_ASSOCIATION,
    PROV_ATTR_ENDER,
    PROV_ATTR_ENDTIME,
    PROV_ATTR_INFORMANT,
    PROV_ATTR_RESPONSIBLE,
    PROV_ATTR_STARTER,
    PROV_ATTR_STARTTIME,
    PROV_ATTR_TIME,
    PROV_ATTR_TRIGGER,
    PROV_ATTR_USED_ENTITY,
    PROV_ATTRIBUTION,
    PROV_BASE_CLS,
    PROV_COMMUNICATION,
    PROV_DELEGATION,
    PROV_DERIVATION,
    PROV_END,
    PROV_GENERATION,
    PROV_ID_ATTRIBUTES_MAP,
    PROV_INFLUENCE,
    PROV_INVALIDATION,
    PROV_LOCATION,
    PROV_MENTION,
    PROV_N_MAP,
    PROV_ROLE,
    PROV_START,
    PROV_USAGE,
    XSD_DOUBLE,
    XSD_QNAME,
)
from prov.identifier import QualifiedName
from prov.serializers import Serializer, _is_text_stream

__author__ = "Satrajit S. Ghosh"
__email__ = "satra@mit.edu"


class ProvRDFException(Error):
    """Raised when a PROV-RDF/PROV-O graph cannot be decoded by this package."""


class AnonymousIDGenerator:
    """Assigns and caches stable blank-node identifier strings for unidentified records."""

    def __init__(self) -> None:
        self._cache = {}  # type: dict[Any, str]
        self._count = 0  # type: int

    def get_anon_id(self, obj: pm.ProvRecord, local_prefix: str = "id") -> str:
        """Return a blank-node identifier string (``"_:<local_prefix><n>"``) for a record.

        The same object always gets the same identifier string back; a new
        one is minted and cached the first time a given record is seen.

        Args:
            obj: Record needing an anonymous identifier.
            local_prefix: Prefix used when minting a new identifier.

        Returns:
            The cached or newly minted blank-node identifier string for
            ``obj``.
        """
        if obj not in self._cache:
            self._count += 1
            self._cache[obj] = f"_:{local_prefix}{self._count}"
        return self._cache[obj]


_XSD_GYEAR_RE = re.compile(r"^(-?\d{4,})(?:Z|[+-]\d{2}:\d{2})?$")
_XSD_GYEARMONTH_RE = re.compile(r"^(-?\d{4,})-(\d{2})(?:Z|[+-]\d{2}:\d{2})?$")

# Reverse map for prov.model.XSD_DATATYPE_PARSERS
LITERAL_XSDTYPE_MAP = {
    float: XSD["double"],
    # boolean, string values are supported natively by PROV-RDF: str falls
    # through to a plain (undecorated) rdflib.Literal -- RDF 1.1 treats a
    # plain literal and an explicit xsd:string one as the same value, and
    # PROV-RDF now emits only the former as the canonical form (#89)
    # int values are typed by magnitude, via canonical_xsd_datatype() (#256)
    # datetime values are converted separately
}
"""Maps Python literal types to their RDF ``xsd:*`` datatype URIRef, for
types not natively/simply representable in PROV-RDF."""


class _FullPrecisionDoubleLiteral(RDFLiteral):
    """An ``xsd:double`` ``rdflib.Literal`` that keeps its exact lexical form on output.

    rdflib's Turtle/TriG writer abbreviates ``xsd:double`` literals to a bare
    (undecorated) numeric token via ``f"{float(self):e}"``, which is capped at
    Python's default ``%e`` precision (~7 significant digits) -- discarding
    precision regardless of the literal's actual stored lexical form (#225).
    Forcing the non-abbreviated ``_literal_n3`` path keeps our full-precision
    lexical (``repr(value)``) intact in every RDF output format.
    """

    def _literal_n3(self, use_plain: bool = False, qname_callback: Any = None) -> str:
        return super()._literal_n3(False, qname_callback)


# Datatypes whose rdflib-coerced ``.value`` losslessly round-trips back to the
# original lexical form via `str()`, so `decode_rdf_representation` may use it
# directly. Every other datatype (`xsd:decimal`, `xsd:unsignedInt`,
# `xsd:positiveInteger`, other XSD numeric subtypes, custom datatypes, ...)
# is reconstructed from the RDF term's own lexical form instead (#218).
_LOSSLESS_COLLAPSE_DATATYPES = frozenset(
    {
        XSD["double"],
        XSD["boolean"],
        XSD["int"],
        XSD["long"],
        XSD["integer"],
        XSD["anyURI"],
        XSD["string"],
    }
)

RELATION_MAP = {
    URIRef(PROV["alternateOf"].uri): "alternate",
    URIRef(PROV["actedOnBehalfOf"].uri): "delegation",
    URIRef(PROV["specializationOf"].uri): "specialization",
    URIRef(PROV["mentionOf"].uri): "mention",
    URIRef(PROV["wasAssociatedWith"].uri): "association",
    URIRef(PROV["wasDerivedFrom"].uri): "derivation",
    URIRef(PROV["wasAttributedTo"].uri): "attribution",
    URIRef(PROV["wasInformedBy"].uri): "communication",
    URIRef(PROV["wasGeneratedBy"].uri): "generation",
    URIRef(PROV["wasInfluencedBy"].uri): "influence",
    URIRef(PROV["wasInvalidatedBy"].uri): "invalidation",
    URIRef(PROV["wasEndedBy"].uri): "end",
    URIRef(PROV["wasStartedBy"].uri): "start",
    URIRef(PROV["hadMember"].uri): "membership",
    URIRef(PROV["used"].uri): "usage",
}
"""Default ``relation_mapper`` for :meth:`ProvRDFSerializer.deserialize`/
:meth:`~ProvRDFSerializer.decode_container`: maps each PROV-O relation
predicate URIRef to the name of the :class:`~prov.model.ProvBundle` factory
method used to recreate it (e.g. ``bundle.derivation(...)``)."""
PREDICATE_MAP = {
    RDFS.label: pm.PROV["label"],
    URIRef(PROV["atLocation"].uri): PROV_LOCATION,
    URIRef(PROV["startedAtTime"].uri): PROV_ATTR_STARTTIME,
    URIRef(PROV["endedAtTime"].uri): PROV_ATTR_ENDTIME,
    URIRef(PROV["atTime"].uri): PROV_ATTR_TIME,
    URIRef(PROV["hadRole"].uri): PROV_ROLE,
    URIRef(PROV["hadPlan"].uri): pm.PROV_ATTR_PLAN,
    URIRef(PROV["hadUsage"].uri): pm.PROV_ATTR_USAGE,
    URIRef(PROV["hadGeneration"].uri): pm.PROV_ATTR_GENERATION,
    URIRef(PROV["hadActivity"].uri): pm.PROV_ATTR_ACTIVITY,
}
"""Default ``predicate_mapper`` for :meth:`ProvRDFSerializer.deserialize`/
:meth:`~ProvRDFSerializer.decode_container`: maps PROV-O predicate URIRefs
that don't already match a PROV formal-attribute QualifiedName to the
QualifiedName of the formal attribute they represent."""


#: Relation types whose two leading formal attributes are *not* emitted as a
#: plain binary ``subject predicate object`` triple when the relation is
#: unidentified -- unless those two attributes are the only thing it carries.
#: Everything else about them lives on the ``prov:qualified*`` node instead.
_QUALIFIED_ONLY_RELATIONS = frozenset(
    {
        PROV_END,
        PROV_START,
        PROV_USAGE,
        PROV_GENERATION,
        PROV_DERIVATION,
        PROV_ASSOCIATION,
        PROV_INVALIDATION,
    }
)

#: ``prov:type`` values that rename a derivation's qualification node, e.g. a
#: derivation typed ``prov:Revision`` is qualified via ``prov:qualifiedRevision``
#: and typed ``prov:Revision`` rather than ``prov:Derivation``.
_DERIVATION_SUBTYPES = frozenset(
    {PROV["Revision"], PROV["Quotation"], PROV["PrimarySource"]}
)

#: Relation types whose plain binary triple is always emitted (they are not
#: gated by :data:`_QUALIFIED_ONLY_RELATIONS`) *and* whose second formal
#: attribute is the relation's influencer per the PROV-O section 3.1
#: qualification tables (``prov:activity``/``prov:agent``/``prov:agent``/
#: ``prov:influencer``). Whenever one of these relations gets a
#: ``prov:qualified*`` node -- identified, or anonymous with extra
#: qualifiers -- that influencer must also be asserted directly on the node,
#: not only implied by the binary triple, so the node is interpretable in
#: isolation (#250). ``prov:mentionOf`` and ``prov:alternateOf`` are
#: deliberately excluded: they are already special-cased elsewhere in the
#: binary-triple/qualification-node machinery.
_BINARY_TRIPLE_INFLUENCER_RELATIONS = frozenset(
    {PROV_COMMUNICATION, PROV_ATTRIBUTION, PROV_DELEGATION, PROV_INFLUENCE}
)


def _prov_uri(localpart: str) -> URIRef:
    """Return the ``prov:`` predicate URIRef for a PROV-O term local part."""
    return URIRef(PROV[localpart].uri)


#: Per-record-type predicate rewrites applied, in order, to the predicate
#: chosen for a qualified relation's attribute. Each entry is a
#: ``(needle, replacement)`` pair: when ``needle`` (a full ``prov:`` term URI)
#: occurs in the predicate computed so far, the predicate becomes
#: ``replacement``. Rewrites are sequential -- a later pair sees the result of
#: an earlier one -- which is what lets e.g. ``prov:used`` become
#: ``prov:entity`` on a usage before the shared time/location rewrites run.
#:
#: This table replaces the per-type ``if`` ladder that used to live inline in
#: :meth:`ProvRDFSerializer.encode_container`; the ordering here reproduces
#: that ladder exactly. The ladder's ``rec_type in [PROV_ACTIVITY]`` arm is
#: deliberately absent: it was unreachable (this code only ever runs for
#: records where ``is_relation()`` is true, so ``rec_type`` is never an
#: element type) and would have raised ``TypeError`` had it been reached.
_TIMED_INFLUENCE_REWRITES = (
    (PROV["time"].uri, _prov_uri("atTime")),
    (PROV["ender"].uri, _prov_uri("hadActivity")),
    (PROV["starter"].uri, _prov_uri("hadActivity")),
    (PROV["location"].uri, _prov_uri("atLocation")),
)
_RELATION_PREDICATE_REWRITES: dict[QualifiedName, tuple[tuple[str, URIRef], ...]] = {
    PROV_DELEGATION: ((PROV["activity"].uri, _prov_uri("hadActivity")),),
    PROV_END: ((PROV["trigger"].uri, _prov_uri("entity")), *_TIMED_INFLUENCE_REWRITES),
    PROV_START: (
        (PROV["trigger"].uri, _prov_uri("entity")),
        *_TIMED_INFLUENCE_REWRITES,
    ),
    PROV_USAGE: ((PROV["used"].uri, _prov_uri("entity")), *_TIMED_INFLUENCE_REWRITES),
    PROV_GENERATION: _TIMED_INFLUENCE_REWRITES,
    PROV_INVALIDATION: _TIMED_INFLUENCE_REWRITES,
    PROV_DERIVATION: (
        (PROV["activity"].uri, _prov_uri("hadActivity")),
        (PROV["generation"].uri, _prov_uri("hadGeneration")),
        (PROV["usage"].uri, _prov_uri("hadUsage")),
        (PROV["usedEntity"].uri, _prov_uri("entity")),
    ),
}

#: Predicate rewrites applied to every relation type, before the per-type
#: rewrites in :data:`_RELATION_PREDICATE_REWRITES`.
_COMMON_PREDICATE_REWRITES = (
    (PROV["plan"].uri, _prov_uri("hadPlan")),
    (PROV["informant"].uri, _prov_uri("activity")),
    (PROV["responsible"].uri, _prov_uri("agent")),
)

#: Extra-attribute names with a dedicated PROV-O predicate, used when encoding
#: the attributes hanging off a relation's qualification node.
_QUALIFIED_ATTR_PREDICATES = {
    PROV["role"]: _prov_uri("hadRole"),
    PROV["plan"]: _prov_uri("hadPlan"),
    PROV["type"]: RDF.type,
    PROV["label"]: RDFS.label,
}

#: Predicates for the attributes encoded directly onto an element (entity,
#: activity, agent) rather than onto a qualification node.
_ELEMENT_ATTR_PREDICATES = {
    PROV["type"]: RDF.type,
    PROV["label"]: RDFS.label,
    PROV_ATTR_STARTTIME: _prov_uri("startedAtTime"),
    PROV_ATTR_ENDTIME: _prov_uri("endedAtTime"),
}

#: Per-record-type formal-attribute rewrites applied, in order, when decoding.
#: Each ``(needle, replacement)`` pair replaces the predicate resolved so far
#: with ``replacement`` when ``needle`` occurs in its string form -- the decode
#: mirror of :data:`_RELATION_PREDICATE_REWRITES`, and likewise a faithful
#: transcription of the ``if`` ladder it replaces.
_DECODE_PREDICATE_REWRITES: dict[
    QualifiedName, tuple[tuple[str, QualifiedName], ...]
] = {
    PROV_COMMUNICATION: (("activity", PROV_ATTR_INFORMANT),),
    PROV_DELEGATION: (("agent", PROV_ATTR_RESPONSIBLE),),
    PROV_END: (
        ("entity", PROV_ATTR_TRIGGER),
        ("activity", PROV_ATTR_ENDER),
        ("endTime", PROV_ATTR_TIME),
    ),
    PROV_START: (
        ("entity", PROV_ATTR_TRIGGER),
        ("activity", PROV_ATTR_STARTER),
        ("startTime", PROV_ATTR_TIME),
    ),
    PROV_DERIVATION: (("entity", PROV_ATTR_USED_ENTITY),),
}


@dataclass
class _DecodeState:
    """Mutable state threaded through :meth:`ProvRDFSerializer.decode_container`.

    Attributes:
        record_types: Maps a subject to the record type decoded for it.
        formal_attributes: Per subject, the formal attribute values gathered
            so far (``None`` where still unknown or ambiguous).
        unique_sets: Per subject, every candidate value seen for each formal
            attribute -- more than one means the attribute is ambiguous and
            must be resolved by walking the combinations.
        other_attributes: Per subject, the non-formal attributes gathered so
            far. Entries are removed as they are consumed, so whatever
            remains at the end could not be converted.
    """

    record_types: dict[str, pm.QualifiedName] = field(default_factory=dict)
    formal_attributes: dict[str, dict[pm.QualifiedName, Any]] = field(
        default_factory=dict
    )
    unique_sets: dict[str, dict[pm.QualifiedName, list[Any]]] = field(
        default_factory=dict
    )
    other_attributes: dict[str, list[tuple[pm.QualifiedNameCandidate, Any]]] = field(
        default_factory=dict
    )

    def register(self, subj: str, prov_obj: pm.QualifiedName) -> None:
        """Record ``subj``'s type and seed its empty formal-attribute slots.

        Args:
            subj: The subject being typed.
            prov_obj: The record type decoded for it.
        """
        self.record_types[subj] = prov_obj
        klass = pm.PROV_REC_CLS[prov_obj]
        self.formal_attributes[subj] = OrderedDict(
            [(key, None) for key in klass.FORMAL_ATTRIBUTES]
        )
        self.unique_sets[subj] = OrderedDict(
            [(key, []) for key in klass.FORMAL_ATTRIBUTES]
        )


def attr2rdf(attr: QualifiedName) -> URIRef:
    """Return the PROV-O predicate URIRef for a PROV formal attribute.

    Args:
        attr: A formal attribute QualifiedName, e.g. ``PROV_ATTR_ENTITY``.

    Returns:
        The corresponding ``prov:*`` predicate URIRef (e.g.
        ``prov:entity``), derived from
        :data:`~prov.constants.PROV_ID_ATTRIBUTES_MAP`.
    """
    return URIRef(PROV[PROV_ID_ATTRIBUTES_MAP[attr].split("prov:")[1]].uri)


class ProvRDFSerializer(Serializer):
    """PROV-O serializer for :class:`~prov.model.ProvDocument`."""

    def serialize(
        self,
        stream: io.IOBase,
        rdf_format: str = "trig",
        PROV_N_MAP: dict[pm.QualifiedName, str] = PROV_N_MAP,
        **kwargs: Any,
    ) -> None:
        """Serialize ``self.document`` to `PROV-O <https://www.w3.org/TR/prov-o/>`_.

        Args:
            stream: Stream to write the output to. Text streams receive the
                serialized text directly; other (binary) streams receive it
                UTF-8-encoded.
            rdf_format: The rdflib RDF format name for the output (e.g.
                ``"trig"``, ``"xml"``, ``"turtle"``, ``"nquads"``).
            PROV_N_MAP: Maps record type QualifiedName to PROV-N keyword,
                used when building the relation predicates; defaults to
                :data:`~prov.constants.PROV_N_MAP`.
            **kwargs: Extra keyword arguments passed through to rdflib's
                ``Graph.serialize()``.

        Raises:
            ProvRDFException: If ``self.document`` is ``None``.
        """
        if self.document is None:
            raise ProvRDFException("No document to serialize.")

        container = self.encode_document(self.document, PROV_N_MAP=PROV_N_MAP)
        newargs = kwargs.copy()
        newargs["format"] = rdf_format

        buf = io.BytesIO()
        try:
            container.serialize(buf, **newargs)
            buf.seek(0, 0)
            # Right now this is a bytestream. If the object to stream to is
            # a text object is must be decoded. We assume utf-8 here which
            # should be fine for almost every case.
            if _is_text_stream(stream):
                stream.write(buf.read().decode("utf-8"))
            else:
                stream.write(buf.read())
        finally:
            buf.close()

    def deserialize(
        self,
        stream: io.IOBase,
        rdf_format: str = "trig",
        relation_mapper: dict[URIRef, str] = RELATION_MAP,
        predicate_mapper: dict[URIRef, pm.QualifiedName] = PREDICATE_MAP,
        **kwargs: Any,
    ) -> pm.ProvDocument:
        """Deserialize a `PROV-O <https://www.w3.org/TR/prov-o/>`_ graph
        into a :class:`~prov.model.ProvDocument`.

        Also sets ``self.document`` to the returned document as a side
        effect.

        Args:
            stream: Input data, parsed by rdflib.
            rdf_format: The rdflib RDF format name of the input data (e.g.
                ``"trig"``, ``"xml"``, ``"turtle"``, ``"nquads"``).
            relation_mapper: Maps PROV-O relation predicate URIRefs to
                :class:`~prov.model.ProvBundle` factory method names;
                defaults to :data:`RELATION_MAP`.
            predicate_mapper: Maps PROV-O predicate URIRefs to formal
                attribute QualifiedNames; defaults to :data:`PREDICATE_MAP`.
            **kwargs: Extra keyword arguments passed through to rdflib's
                ``Graph.parse()``.

        Returns:
            The deserialized :class:`~prov.model.ProvDocument` (also stored
            in ``self.document``).
        """
        newargs = kwargs.copy()
        newargs["format"] = rdf_format
        container = Dataset(default_union=True)
        # rdflib accepts any readable stream at runtime (via create_input_source)
        # but its declared parameter type does not include io.IOBase.
        container.parse(stream, **newargs)  # type: ignore[arg-type]
        self.document = pm.ProvDocument()
        self.decode_document(
            container,
            self.document,
            relation_mapper=relation_mapper,
            predicate_mapper=predicate_mapper,
        )
        return self.document

    def valid_identifier(
        self, value: pm.QualifiedNameCandidate | None
    ) -> pm.QualifiedName | None:
        """Resolve a candidate value to a :class:`~prov.identifier.QualifiedName`.

        Args:
            value: Candidate qualified name, or ``None``.

        Returns:
            The resolved :class:`~prov.identifier.QualifiedName`, or ``None``
            if ``value`` is ``None``/falsy or cannot be resolved against
            ``self.document``'s namespaces.
        """
        # valid_qualified_name returns None for falsy inputs, so passing None
        # through is safe despite its declared parameter type.
        return self.document.valid_qualified_name(value)  # type: ignore[union-attr, arg-type]

    def encode_rdf_representation(self, value: Any) -> RDFLiteral | URIRef:
        """Encode a single attribute value to its RDF term representation.

        Args:
            value: Attribute value to encode: a ``URIRef`` (returned as-is),
                a :class:`~prov.model.Literal`, a :class:`datetime.datetime`,
                a :class:`~prov.identifier.QualifiedName`, another
                :class:`~prov.identifier.Identifier`, a plain ``int``
                (typed by magnitude via
                :func:`~prov.model.canonical_xsd_datatype`), a type listed in
                :data:`LITERAL_XSDTYPE_MAP`, or another value passed straight
                to ``rdflib.Literal``.

        Returns:
            The RDF term (``URIRef`` or ``rdflib.Literal``) for ``value``.
        """
        if isinstance(value, URIRef):
            return value
        elif isinstance(value, pm.Literal):
            return literal_rdf_representation(value)
        elif isinstance(value, datetime.datetime):
            return RDFLiteral(value.isoformat(), datatype=XSD["dateTime"])
        elif isinstance(value, pm.QualifiedName):
            return URIRef(value.uri)
        elif isinstance(value, pm.Identifier):
            return RDFLiteral(value.uri, datatype=XSD["anyURI"])
        elif (
            isinstance(value, int)
            and (xsd_datatype := pm.canonical_xsd_datatype(value)) is not None
        ):
            # bool is an int subtype but canonical_xsd_datatype(bool) is
            # None, so bools fall through unaffected (#256).
            return RDFLiteral(str(value), datatype=XSD[xsd_datatype.localpart])
        elif type(value) in LITERAL_XSDTYPE_MAP:
            # LITERAL_XSDTYPE_MAP maps only `float -> XSD["double"]` today, so
            # the full-precision lexical form always applies here: a datatype
            # that skips rdflib's precision-losing bare-double abbreviation
            # (#225) on output.
            return _FullPrecisionDoubleLiteral(
                repr(value), datatype=LITERAL_XSDTYPE_MAP[type(value)]
            )
        else:
            return RDFLiteral(value)

    def decode_rdf_representation(self, literal: Any, graph: Graph) -> Any:
        """Decode a single RDF term back to its PROV attribute value representation.

        If ``literal`` is a ``URIRef`` that cannot be resolved to a
        QualifiedName in ``self.document``'s existing namespaces, a new
        namespace is minted (via ``graph``'s namespace manager) and
        registered on ``self.document`` as a side effect.

        Args:
            literal: RDF term to decode: an ``rdflib.Literal`` or a
                ``URIRef``, or already a plain value to return unchanged.
            graph: Graph ``literal`` came from, used to compute a QName/mint
                a namespace for unresolved ``URIRef`` values.

        Returns:
            A :class:`datetime.datetime` for ``xsd:dateTime`` literals, a
            :class:`~prov.model.Literal` for other typed/tagged literals, a
            resolved (or newly minted) :class:`~prov.identifier.QualifiedName`
            for ``URIRef`` values, or ``literal`` unchanged otherwise.
        """
        if isinstance(literal, RDFLiteral):
            value = literal.value if literal.value is not None else literal
            datatype = literal.datatype
            langtag = literal.language
            value_overridden = False
            if datatype and "XMLLiteral" in datatype:
                value = literal
                value_overridden = True
            if datatype and "base64Binary" in datatype:
                # rdflib decodes xsd:base64Binary literals to bytes; re-encode and
                # take the ASCII text, not the bytes repr (#288)
                value = base64.standard_b64encode(cast(bytes, value)).decode("ascii")
                value_overridden = True
            if datatype == XSD["QName"]:
                return pm.Literal(literal, datatype=XSD_QNAME)
            if datatype == XSD["dateTime"]:
                parsed = pm.parse_xsd_datetime(str(literal))
                if parsed is None:
                    raise ValueError(f"Invalid xsd:dateTime literal: {literal}")
                return parsed
            if datatype == XSD["gYear"]:
                year_match = _XSD_GYEAR_RE.match(str(literal))
                if year_match is None:
                    raise ValueError(f"Invalid xsd:gYear literal: {literal}")
                return pm.Literal(
                    int(year_match.group(1)),
                    datatype=self.valid_identifier(datatype),
                )
            if datatype == XSD["gYearMonth"]:
                ym_match = _XSD_GYEARMONTH_RE.match(str(literal))
                if ym_match is None:
                    raise ValueError(f"Invalid xsd:gYearMonth literal: {literal}")
                return pm.Literal(
                    f"{int(ym_match.group(1))}-{int(ym_match.group(2)):02d}",
                    datatype=self.valid_identifier(datatype),
                )
            else:
                if (
                    not value_overridden
                    and datatype is not None
                    and datatype not in _LOSSLESS_COLLAPSE_DATATYPES
                ):
                    # #218: datatypes without a lossless Python-value collapse
                    # (e.g. xsd:decimal, xsd:unsignedInt, xsd:positiveInteger,
                    # other XSD numeric subtypes, or custom datatypes) --
                    # rdflib's coerced `.value` (a Decimal/int/etc.)
                    # re-canonicalises the lexical form when stringified,
                    # silently mutating the asserted literal on decode. Use
                    # the RDF term's own lexical form instead, so what was
                    # asserted on encode is exactly what comes back.
                    value = str(literal)
                # The literal of standard Python types is not converted here
                # It will be automatically converted when added to a record by
                # _auto_literal_conversion()
                return pm.Literal(value, self.valid_identifier(datatype), langtag)
        elif isinstance(literal, URIRef):
            rval = self.valid_identifier(literal)
            if rval is None:
                prefix, iri, _ = graph.namespace_manager.compute_qname(literal)
                ns = self.document.add_namespace(prefix, iri)  # type: ignore[union-attr]
                rval = pm.QualifiedName(ns, literal.replace(ns.uri, ""))
            return rval
        else:
            # simple type, just return it
            return literal

    def encode_document(
        self,
        document: pm.ProvDocument,
        PROV_N_MAP: dict[pm.QualifiedName, str] = PROV_N_MAP,
    ) -> Dataset:
        """Encode a whole :class:`~prov.model.ProvDocument`, including its named bundles.

        Args:
            document: Document to encode.
            PROV_N_MAP: Maps record type QualifiedName to PROV-N keyword;
                defaults to :data:`~prov.constants.PROV_N_MAP`.

        Returns:
            A ``Dataset`` (union view) containing the document's own triples
            plus one named graph per bundle in ``document.bundles``.
        """
        container = Dataset(default_union=True)
        # Encode the document's own records into a plain Graph first, then
        # merge it into the Dataset's default graph via addN(), rather than
        # passing the Dataset itself as encode_container()'s `container`:
        # as of rdflib 7.3, Dataset.add() internally touches the deprecated
        # Dataset.default_context property (its default_context/contexts()
        # -> default_graph/graphs() migration is incomplete -- add() itself
        # wasn't updated), which trips DeprecationWarning even though we
        # never reference that property ourselves. addN() with an explicit
        # graph avoids it.
        doc_graph = self.encode_container(document, PROV_N_MAP=PROV_N_MAP)
        for prefix, uri in doc_graph.namespaces():
            container.bind(prefix, uri)
        default_graph = container.graph(DATASET_DEFAULT_GRAPH_ID)
        container.addN((s, p, o, default_graph) for s, p, o in doc_graph)
        for item in document.bundles:
            #  encoding the sub-bundle into a named graph carrying its IRI
            bundle = self.encode_container(
                item,
                identifier=item.identifier.uri,  # type: ignore[union-attr]
                PROV_N_MAP=PROV_N_MAP,
            )
            # #96: the context passed here must be a Dataset-owned graph
            # (via container.graph(), mirroring `default_graph` above), not
            # the standalone `bundle` Graph object itself -- passing that
            # object directly makes older rdflib Datasets keep it as a
            # distinct context with its own private NamespaceManager
            # (unlike a container.graph()-obtained one, which shares the
            # Dataset's own). The bundle's own bindings still reach the
            # output that way, but the `override=False` collision guarantee
            # below silently does not: a bundle-local prefix colliding with
            # a document-level one may clobber it instead of being renamed.
            # That outcome is *order-dependent, not version-dependent* --
            # with the standalone-Graph form it varies run to run on the
            # same rdflib (observed flipping on 7.0.0 and 7.1.0 across
            # fresh interpreters), so sampling one run per release invents
            # a version boundary that does not exist. container.graph() is
            # deterministic and correct on the 7.0.0 floor and upwards.
            named_graph = container.graph(bundle.identifier)
            container.addN((s, p, o, named_graph) for s, p, o in bundle)
            # #96: bundle-local namespace bindings (and the bundle's own
            # default namespace, bound by encode_container() below) are
            # otherwise never copied into the Dataset, so TriG output falls
            # back to an rdflib-minted `ns1:`-style prefix for them.
            # override=False: rdflib's own collision handling already renames
            # the *incoming* namespace (e.g. to `prefix1:`) whenever the
            # prefix string is already bound to a different URI, regardless
            # of `override` -- that flag only controls whether a namespace
            # already bound under a different prefix gets *rebound* to this
            # new preferred prefix. Passing False keeps every earlier
            # binding (the document-level ones bound just above, and the
            # core prov/xsd/rdf/rdfs ones bound in encode_container()) as
            # the preferred spelling, so document-level prefixes always win
            # on collision.
            for prefix, uri in bundle.namespaces():
                container.bind(prefix, uri, override=False)
        return container

    def encode_container(
        self,
        bundle: pm.ProvBundle,
        PROV_N_MAP: dict[pm.QualifiedName, str] = PROV_N_MAP,
        container: Graph | None = None,
        identifier: str | None = None,
    ) -> Graph:
        """Encode a single bundle's namespaces and records into an RDF graph.

        Does not recurse into named bundles; see :meth:`encode_document` for
        a whole document. Elements are encoded directly as PROV-O triples;
        relations are encoded per the PROV-O qualification pattern (a
        subject-predicate-object triple for the two main formal attributes,
        plus a ``prov:qualified*`` blank/identified node carrying any
        remaining formal and extra attributes), following the mappings from
        PROV-N attribute names to PROV-O predicates defined by the PROV-O
        specification.

        Args:
            bundle: Bundle (or document, treated as its top-level bundle) to
                encode.
            PROV_N_MAP: Maps record type QualifiedName to PROV-N keyword;
                defaults to :data:`~prov.constants.PROV_N_MAP`.
            container: Graph to add triples to. If ``None``, a new
                ``Graph`` is created (with ``identifier``, and with the
                ``prov`` namespace pre-bound). When called from
                :meth:`encode_document`, ``container`` is always ``None``,
                so this method builds a fresh plain ``Graph``;
                :meth:`encode_document` then merges the returned triples
                into its ``Dataset`` via ``addN()``. This method expects a
                plain ``Graph`` here: passing a ``Dataset`` works, but its
                ``.add()`` calls will surface rdflib's own internal
                ``DeprecationWarning`` on ``Dataset.default_context`` (rdflib
                >=7.3), which is exactly why :meth:`encode_document` uses a
                plain ``Graph`` plus ``addN()`` instead of passing its
                ``Dataset`` in here.
            identifier: Identifier for the new graph, used only when
                ``container`` is ``None``.

        Returns:
            The graph that was passed in as ``container``, or the newly
            created one.
        """
        if container is None:
            container = Graph(identifier=identifier)
            nm = container.namespace_manager
            nm.bind("prov", PROV.uri)

        for namespace in bundle.namespaces:
            container.bind(namespace.prefix, namespace.uri)
        # #96: `bundle.namespaces` excludes the bundle's default namespace
        # (a separate concept from the core prov/xsd/xsi namespaces that
        # `get_registered_namespaces` excludes -- `set_default_namespace`
        # never writes to the registered-namespace dict), so it needs its
        # own bind() call here, under the empty prefix, for its terms to
        # render as `:local` rather than a full IRI. Note this widens the
        # surface of #294: a default- or bundle-namespace term whose local
        # part ends in a character rdflib cannot abbreviate is now bound
        # but still emitted as a full IRI, and fails to decode.
        default_namespace = bundle.get_default_namespace()
        if default_namespace is not None:
            container.bind("", default_namespace.uri)

        id_generator = AnonymousIDGenerator()

        def real_or_anon_id(record: pm.ProvRecord) -> str:
            return (
                record._identifier.uri
                if record._identifier
                else id_generator.get_anon_id(record)
            )

        for record in bundle._records:
            rec_type = record.get_type()
            rec_id: URIRef | None
            if hasattr(record, "identifier") and record.identifier:
                rec_id = URIRef(str(real_or_anon_id(record)))
                container.add((rec_id, RDF.type, URIRef(rec_type.uri)))
            else:
                rec_id = None
            if not record.attributes:
                continue
            if record.is_relation():
                self._encode_relation(container, record, rec_type, rec_id, PROV_N_MAP)
            else:
                self._encode_element(container, record, rec_id, real_or_anon_id)
        return container

    def _encode_element(
        self,
        container: Graph,
        record: pm.ProvRecord,
        identifier: URIRef | None,
        real_or_anon_id: Callable[[pm.ProvRecord], str],
    ) -> None:
        """Encode an element's (entity/activity/agent) attributes as direct triples.

        Args:
            container: Graph to add triples to.
            record: The element record being encoded.
            identifier: The element's subject URIRef.
            real_or_anon_id: Resolves a referenced record to its identifier
                string, minting a stable anonymous one where needed.
        """
        all_attributes = list(record.formal_attributes) + list(record.attributes)
        for attr, value in all_attributes:
            if value is None:
                continue
            if isinstance(value, pm.ProvRecord):
                obj: RDFLiteral | URIRef = URIRef(str(real_or_anon_id(value)))
            else:
                #  Assuming this is a datetime value
                obj = self.encode_rdf_representation(value)
            pred: URIRef | RDFLiteral
            if attr == PROV["location"]:
                pred = _prov_uri("atLocation")
                # `False and ...` deliberately disables this branch (see
                # git history back to 2014): kept for now because touching
                # it risks changing frozen 2.x RDF output; scheduled for
                # deletion in 3.0 (item F2 in
                # docs/superpowers/specs/2026-07-04-3x-typing-api-improvements.md).
                if False and isinstance(value, (URIRef, pm.QualifiedName)):  # noqa: SIM223
                    if isinstance(value, pm.QualifiedName):
                        value = URIRef(value.uri)
                    container.add((identifier, pred, value))
                else:
                    container.add(
                        (
                            # elements always carry an identifier here
                            cast("URIRef | BNode", identifier),
                            pred,
                            self.encode_rdf_representation(obj),
                        )
                    )
                continue
            if isinstance(attr, pm.QualifiedName) and attr in _ELEMENT_ATTR_PREDICATES:
                pred = _ELEMENT_ATTR_PREDICATES[attr]
            else:
                pred = self.encode_rdf_representation(attr)
            # elements always carry an identifier here
            container.add((cast("URIRef | BNode", identifier), pred, obj))

    def _encode_relation(
        self,
        container: Graph,
        record: pm.ProvRecord,
        rec_type: pm.QualifiedName,
        identifier: URIRef | None,
        PROV_N_MAP: dict[pm.QualifiedName, str],
    ) -> None:
        """Encode a relation using PROV-O's qualification pattern.

        Emits the binary ``subject predicate object`` triple for the two
        leading formal attributes where PROV-O allows one, then hangs the
        remaining formal and extra attributes off a ``prov:qualified*`` node
        (the record's own identifier, or a fresh blank node).

        Args:
            container: Graph to add triples to.
            record: The relation record being encoded.
            rec_type: ``record``'s record type QualifiedName.
            identifier: The relation's own subject URIRef, or ``None`` when it
                is unidentified (in which case a blank node is minted).
            PROV_N_MAP: Maps record type QualifiedName to PROV-N keyword.
        """
        bnode = None
        formal_objects: list[pm.QualifiedName] = []
        used_objects: list[pm.QualifiedName] = []
        all_attributes = list(record.formal_attributes) + list(record.attributes)
        formal_qualifiers = False
        for attrid, (_attr, value) in enumerate(list(record.formal_attributes)):
            if (identifier is not None and value is not None) or (
                identifier is None and value is not None and attrid > 1
            ):
                formal_qualifiers = True
        has_qualifiers = len(record.extra_attributes) > 0 or formal_qualifiers

        node: URIRef | BNode | None = identifier
        for attr, value in all_attributes:
            # The qualification head is (re)built until a blank node is minted
            # for it; for an identified relation no blank node is ever minted,
            # so this re-runs per attribute exactly as it always has -- every
            # triple it emits is idempotent, so the repetition is harmless.
            if bnode is None:
                node, bnode, skip = self._encode_relation_head(
                    container,
                    record,
                    rec_type,
                    node,
                    PROV_N_MAP,
                    formal_objects,
                    used_objects,
                    has_qualifiers,
                )
                if skip:
                    continue
            if value is not None and attr not in used_objects:
                container.add(
                    (
                        # a qualified relation always has a URIRef or
                        # BNode identifier by this point
                        cast("URIRef | BNode", node),
                        self._qualified_attr_predicate(rec_type, attr, formal_objects),
                        self.encode_rdf_representation(value),
                    )
                )

    def _encode_relation_head(
        self,
        container: Graph,
        record: pm.ProvRecord,
        rec_type: pm.QualifiedName,
        identifier: URIRef | BNode | None,
        PROV_N_MAP: dict[pm.QualifiedName, str],
        formal_objects: list[pm.QualifiedName],
        used_objects: list[pm.QualifiedName],
        has_qualifiers: bool,
    ) -> tuple[URIRef | BNode | None, BNode | None, bool]:
        """Emit a relation's binary triple and its ``prov:qualified*`` node.

        Args:
            container: Graph to add triples to.
            record: The relation record being encoded.
            rec_type: ``record``'s record type QualifiedName.
            identifier: The relation's subject URIRef, or ``None``.
            PROV_N_MAP: Maps record type QualifiedName to PROV-N keyword.
            formal_objects: Accumulator, extended with the record's formal
                attribute names (used to recognise formal attributes later).
            used_objects: Accumulator, replaced in place with the formal
                attributes already consumed by the binary triple.
            has_qualifiers: Whether the relation carries anything beyond the
                two attributes of its binary triple.

        Returns:
            ``(node, bnode, skip)``: the subject to hang remaining attributes
            off, the blank node minted for it (``None`` if none was), and
            whether the caller should skip this attribute entirely.
        """
        pred = _prov_uri(PROV_N_MAP[rec_type])
        valid_formal_indices = set()
        for idx, (key, val) in enumerate(record.formal_attributes):
            formal_objects.append(key)
            if val:
                valid_formal_indices.add(idx)
        used_objects[:] = [record.formal_attributes[0][0]]
        subj: URIRef | RDFLiteral | None = None
        if record.formal_attributes[0][1]:
            subj = URIRef(record.formal_attributes[0][1].uri)
        if identifier is None and subj is not None:
            has_qualifiers = self._encode_relation_binary_triple(
                container,
                record,
                rec_type,
                pred,
                subj,
                valid_formal_indices,
                used_objects,
                has_qualifiers,
            )
        if rec_type in [PROV_ALTERNATE]:
            # #258/#250 territory: alternateOf emits only its binary triple,
            # so any extra attributes it carries are dropped. Preserved as-is.
            return identifier, None, True
        if subj and (has_qualifiers or identifier):
            return (
                *self._encode_qualification_node(
                    container, record, rec_type, identifier, subj
                ),
                False,
            )
        return identifier, None, False

    def _encode_relation_binary_triple(
        self,
        container: Graph,
        record: pm.ProvRecord,
        rec_type: pm.QualifiedName,
        pred: URIRef,
        subj: URIRef | RDFLiteral,
        valid_formal_indices: set[int],
        used_objects: list[pm.QualifiedName],
        has_qualifiers: bool,
    ) -> bool:
        """Emit the plain binary triple for an unidentified relation, if allowed.

        Args:
            container: Graph to add triples to.
            record: The relation record being encoded.
            rec_type: ``record``'s record type QualifiedName.
            pred: The relation's PROV-O predicate.
            subj: Subject term for the binary triple.
            valid_formal_indices: Indices of formal attributes that have a value.
            used_objects: Accumulator, extended with the formal attributes
                consumed by the emitted triple(s).
            has_qualifiers: Current qualification flag.

        Returns:
            The (possibly updated) ``has_qualifiers`` flag.
        """
        try:
            obj_val = record.formal_attributes[1][1]
        except IndexError:
            obj_val = None
        if not obj_val:
            return has_qualifiers
        if rec_type in _QUALIFIED_ONLY_RELATIONS and not (
            valid_formal_indices == {0, 1} and len(record.extra_attributes) == 0
        ):
            return has_qualifiers
        # #250: skip the object append when a qualification node will be
        # minted for this influencer relation and will assert the influencer
        # attribute directly (as a rewrite of the formal attribute).
        if not (rec_type in _BINARY_TRIPLE_INFLUENCER_RELATIONS and has_qualifiers):
            used_objects.append(record.formal_attributes[1][0])
        obj_term: URIRef | RDFLiteral = self.encode_rdf_representation(obj_val)
        container.add((subj, pred, obj_term))
        if rec_type == PROV_MENTION:
            if record.formal_attributes[2][1]:
                used_objects.append(record.formal_attributes[2][0])
                container.add(
                    (
                        subj,
                        _prov_uri("asInBundle"),
                        self.encode_rdf_representation(record.formal_attributes[2][1]),
                    )
                )
            has_qualifiers = False
        return has_qualifiers

    def _encode_qualification_node(
        self,
        container: Graph,
        record: pm.ProvRecord,
        rec_type: pm.QualifiedName,
        identifier: URIRef | BNode | None,
        subj: URIRef | RDFLiteral,
    ) -> tuple[URIRef | BNode, BNode | None]:
        """Link (and, when anonymous, create and type) a ``prov:qualified*`` node.

        A ``prov:type`` of ``prov:Revision``/``prov:Quotation``/
        ``prov:PrimarySource`` renames the qualification property and the
        node's own type, replacing the record type's own ``rdf:type`` triple.

        Args:
            container: Graph to add triples to.
            record: The relation record being encoded.
            rec_type: ``record``'s record type QualifiedName.
            identifier: The relation's subject URIRef, or ``None`` to mint a
                blank node.
            subj: Subject the qualification node hangs off.

        Returns:
            ``(node, bnode)``: the qualification node, and the blank node
            minted for it (``None`` when ``identifier`` was already set).
        """
        qualifier = rec_type._localpart
        rec_uri = rec_type.uri
        for attr_name, val in record.extra_attributes:
            if attr_name == PROV["type"] and val in _DERIVATION_SUBTYPES:
                qualifier = val._localpart
                rec_uri = val.uri
                if identifier is not None:
                    container.remove((identifier, RDF.type, URIRef(rec_type.uri)))
        QRole = _prov_uri("qualified" + qualifier)
        if identifier is not None:
            container.add((subj, QRole, identifier))
            return identifier, None
        # #250: the anonymous qualification node's influencer property (e.g.
        # `prov:agent` on an attribution/delegation node) is *not* added
        # here -- for _BINARY_TRIPLE_INFLUENCER_RELATIONS it is asserted by
        # the main _encode_relation() loop once this node exists (see the
        # `used_objects.remove(...)` in _encode_relation_binary_triple),
        # exactly like every other attribute hanging off the node.
        bnode = BNode()
        container.add((subj, QRole, bnode))
        container.add((bnode, RDF.type, URIRef(rec_uri)))
        return bnode, bnode

    def _qualified_attr_predicate(
        self,
        rec_type: pm.QualifiedName,
        attr: pm.QualifiedNameCandidate,
        formal_objects: list[pm.QualifiedName],
    ) -> URIRef | RDFLiteral:
        """Return the PROV-O predicate for one attribute of a qualified relation.

        Picks a base predicate for ``attr``, then applies the common and
        per-record-type rewrites from :data:`_COMMON_PREDICATE_REWRITES` and
        :data:`_RELATION_PREDICATE_REWRITES` in order.

        Args:
            rec_type: The relation's record type QualifiedName.
            attr: The attribute name being encoded.
            formal_objects: The relation's formal attribute names.

        Returns:
            The predicate term to use for ``attr``.
        """
        pred: URIRef | RDFLiteral
        if attr in formal_objects:
            pred = attr2rdf(cast(QualifiedName, attr))
        elif isinstance(attr, pm.QualifiedName) and attr in _QUALIFIED_ATTR_PREDICATES:
            pred = _QUALIFIED_ATTR_PREDICATES[attr]
        elif isinstance(attr, pm.QualifiedName):
            pred = URIRef(attr.uri)
        else:
            pred = self.encode_rdf_representation(attr)
        for needle, replacement in (
            *_COMMON_PREDICATE_REWRITES,
            *_RELATION_PREDICATE_REWRITES.get(rec_type, ()),
        ):
            if needle in pred:
                pred = replacement
        return pred

    def decode_document(
        self,
        content: Dataset,
        document: pm.ProvDocument,
        relation_mapper: dict[URIRef, str] = RELATION_MAP,
        predicate_mapper: dict[URIRef, pm.QualifiedName] = PREDICATE_MAP,
    ) -> None:
        """Decode a whole RDF graph, including named subgraphs, into a document.

        Mutates ``document`` in place: registers ``content``'s namespaces on
        it, then decodes each subgraph (the default/bnode-identified
        subgraph as the document's own records; IRI-identified subgraphs as
        named bundles added via :meth:`~prov.model.ProvBundle.bundle`) via
        :meth:`decode_container`. If ``content`` has no ``graphs()`` (i.e. it
        is a plain ``Graph``, not a ``Dataset``), it is decoded directly as
        the document's own records.

        Args:
            content: RDF graph (typically a ``Dataset``, as produced by
                :meth:`encode_document`) to decode.
            document: Document to populate.
            relation_mapper: Maps PROV-O relation predicate URIRefs to
                :class:`~prov.model.ProvBundle` factory method names;
                defaults to :data:`RELATION_MAP`.
            predicate_mapper: Maps PROV-O predicate URIRefs to formal
                attribute QualifiedNames; defaults to :data:`PREDICATE_MAP`.
        """
        for prefix, url in content.namespaces():
            document.add_namespace(prefix, str(url))
        if hasattr(content, "graphs"):
            for graph in content.graphs():
                if (
                    isinstance(graph.identifier, BNode)
                    or graph.identifier == DATASET_DEFAULT_GRAPH_ID
                ):
                    self.decode_container(
                        graph,
                        document,
                        relation_mapper=relation_mapper,
                        predicate_mapper=predicate_mapper,
                    )
                else:
                    # Resolve the bundle IRI to a qualified name; if no
                    # registered namespace matches (rdflib >= 7 no longer
                    # carries bundle-graph prefix bindings into TriG output,
                    # so re-parsed documents may lack them), fall back to
                    # minting a namespace via compute_qname, as
                    # decode_rdf_representation does for all other IRIs.
                    bundle_id = self.decode_rdf_representation(graph.identifier, graph)
                    bundle = document.bundle(bundle_id)
                    self.decode_container(
                        graph,
                        bundle,
                        relation_mapper=relation_mapper,
                        predicate_mapper=predicate_mapper,
                    )
        else:
            self.decode_container(
                content,
                document,
                relation_mapper=relation_mapper,
                predicate_mapper=predicate_mapper,
            )

    def decode_container(
        self,
        graph: Graph,
        bundle: pm.ProvBundle,
        relation_mapper: dict[URIRef, str] = RELATION_MAP,
        predicate_mapper: dict[URIRef, pm.QualifiedName] = PREDICATE_MAP,
    ) -> None:
        """Decode a single RDF (sub)graph's triples into records added to a bundle.

        Reconstructs each subject's record type from its ``rdf:type``
        triple(s), then walks every triple in the graph to fill in that
        record's formal and non-formal attributes (mapping PROV-O relation
        predicates back to :class:`~prov.model.ProvBundle` factory calls via
        ``relation_mapper``, and other predicates back to formal attributes
        via ``predicate_mapper`` and PROV-O's qualification pattern), adding
        each reconstructed record to ``bundle`` via
        :meth:`~prov.model.ProvBundle.new_record`. Mutates ``bundle`` (and,
        for unresolvable subject IRIs, ``self.document``'s namespaces) in
        place.

        Args:
            graph: The RDF (sub)graph to decode, e.g. one context of a
                ``Dataset``.
            bundle: Bundle (or document) to add the decoded records to.
            relation_mapper: Maps PROV-O relation predicate URIRefs to
                :class:`~prov.model.ProvBundle` factory method names;
                defaults to :data:`RELATION_MAP`.
            predicate_mapper: Maps PROV-O predicate URIRefs to formal
                attribute QualifiedNames; defaults to :data:`PREDICATE_MAP`.

        Raises:
            ValueError: If a relation's object term cannot be decoded to a
                usable attribute value.

        Warns:
            UserWarning: If, after decoding, some attributes could not be
                matched to any formal attribute or converted.
        """
        prov_cls_map = {
            prov_type.uri: base_cls for prov_type, base_cls in PROV_BASE_CLS.items()
        }
        state = _DecodeState()
        self._decode_type_triples(graph, state, prov_cls_map)
        self._decode_triples(graph, bundle, state, relation_mapper, predicate_mapper)
        self._emit_decoded_records(bundle, state)

        if state.other_attributes:
            warnings.warn(
                "The following attributes were not converted: "
                + str(state.other_attributes),
                UserWarning,
                stacklevel=2,
            )

    def _decode_type_triples(
        self,
        graph: Graph,
        state: "_DecodeState",
        prov_cls_map: dict[str, pm.QualifiedName],
    ) -> None:
        """Reconstruct each subject's record type from its ``rdf:type`` triples.

        Registers a record type in ``state`` for every subject typed with a
        known PROV-O class; every other ``rdf:type`` object (and the extra
        types of an already-registered subject) becomes a ``prov:type``
        attribute instead.

        Args:
            graph: The RDF (sub)graph being decoded.
            state: Decode state, mutated in place.
            prov_cls_map: Maps a PROV-O class URI to its base record type.
        """
        for stmt in graph.triples((None, RDF.type, None)):
            subj = str(stmt[0])
            obj = str(stmt[2])
            add_attr = (
                self._register_record_type(graph, stmt, subj, obj, prov_cls_map, state)
                if obj in prov_cls_map
                else True
            )
            if add_attr:
                state.other_attributes.setdefault(subj, []).append(
                    (pm.PROV["type"], self.decode_rdf_representation(stmt[2], graph))
                )

    def _register_record_type(
        self,
        graph: Graph,
        stmt: tuple[Node, Node, Node],
        subj: str,
        obj: str,
        prov_cls_map: dict[str, pm.QualifiedName],
        state: "_DecodeState",
    ) -> bool:
        """Register one subject's record type, if this triple establishes it.

        Args:
            graph: The RDF (sub)graph being decoded.
            stmt: The ``rdf:type`` triple.
            subj: ``stmt``'s subject, as a string.
            obj: ``stmt``'s object, as a string.
            prov_cls_map: Maps a PROV-O class URI to its base record type.
            state: Decode state, mutated in place.

        Returns:
            Whether the triple's object should *also* be recorded as a
            ``prov:type`` attribute (true for a derivation subtype or an
            extra type on a blank node, and for any subject already typed).
        """
        if not isinstance(stmt[0], BNode) and self.valid_identifier(subj) is None:
            prefix, iri, _ = graph.namespace_manager.compute_qname(subj)
            self.document.add_namespace(prefix, iri)  # type: ignore[union-attr]
        prov_obj = prov_cls_map[obj]
        # objects of rdf:type triples are URIRefs (str subclass);
        # rdflib types them only as Node
        isderivation = any(
            subtype.uri in cast(str, stmt[2]) for subtype in _DERIVATION_SUBTYPES
        )
        if subj in state.record_types or not (
            prov_obj.uri == obj or isderivation or isinstance(stmt[0], BNode)
        ):
            return True
        state.register(subj, prov_obj)
        return (isinstance(stmt[0], BNode) or isderivation) and prov_obj.uri != obj

    def _decode_triples(
        self,
        graph: Graph,
        bundle: pm.ProvBundle,
        state: "_DecodeState",
        relation_mapper: dict[URIRef, str],
        predicate_mapper: dict[URIRef, pm.QualifiedName],
    ) -> None:
        """Walk every triple, filling in relations and attributes.

        Args:
            graph: The RDF (sub)graph being decoded.
            bundle: Bundle to add reconstructed relations to.
            state: Decode state, mutated in place.
            relation_mapper: Maps PROV-O relation predicate URIRefs to
                :class:`~prov.model.ProvBundle` factory method names.
            predicate_mapper: Maps PROV-O predicate URIRefs to formal
                attribute QualifiedNames.
        """
        for subj_node, pred_node, obj in graph:
            subj = str(subj_node)
            # predicates in RDF are always URIRefs; rdflib types them as Node
            pred = cast(URIRef, pred_node)
            state.other_attributes.setdefault(subj, [])
            if pred == RDF.type:
                continue
            if pred in relation_mapper:
                self._decode_relation_triple(
                    graph, bundle, state, subj, pred, obj, relation_mapper
                )
            elif subj in state.record_types:
                self._decode_attribute_triple(
                    graph, state, subj, pred, obj, predicate_mapper
                )
            local_key = str(obj)
            if local_key in state.record_types and "qualified" in pred:
                # The qualification node's influencer: the subject that points
                # at it fills the relation's first formal attribute.
                state.formal_attributes[local_key][
                    next(iter(state.formal_attributes[local_key].keys()))
                ] = subj

    def _decode_relation_triple(
        self,
        graph: Graph,
        bundle: pm.ProvBundle,
        state: "_DecodeState",
        subj: str,
        pred: URIRef,
        obj: Node,
        relation_mapper: dict[URIRef, str],
    ) -> None:
        """Recreate one relation from its PROV-O binary triple.

        Most relations map straight onto a :class:`~prov.model.ProvBundle`
        factory call. ``prov:mentionOf`` picks up its bundle from the
        subject's ``prov:asInBundle`` triple; and delegation/association
        defer to their qualification node when they have one, filling its
        first two formal attributes instead of creating a record here.

        Args:
            graph: The RDF (sub)graph being decoded.
            bundle: Bundle to add the relation to.
            state: Decode state, mutated in place.
            subj: The triple's subject, as a string.
            pred: The triple's relation predicate.
            obj: The triple's object.
            relation_mapper: Maps PROV-O relation predicate URIRefs to
                :class:`~prov.model.ProvBundle` factory method names.
        """
        factory = getattr(bundle, relation_mapper[pred])
        if "alternateOf" in pred:
            factory(subj, str(obj))
            return
        if "mentionOf" in pred:
            mention_bundle = None
            for stmt in graph.triples(
                (URIRef(subj), URIRef(pm.PROV["asInBundle"].uri), None)
            ):
                mention_bundle = stmt[2]
            factory(subj, str(obj), mention_bundle)
            return
        if "actedOnBehalfOf" in pred or "wasAssociatedWith" in pred:
            name = relation_mapper[pred]
            qualifier = "qualified" + name.upper()[0] + name[1:]
            qualifier_bnode = None
            agent_pred = URIRef(pm.PROV["agent"].uri)
            for stmt in graph.triples(
                (URIRef(subj), URIRef(pm.PROV[qualifier].uri), None)
            ):
                candidate = stmt[2]
                # #226/#250: a subject may point at more than one
                # qualification node of the same kind -- e.g. two
                # delegations from the same delegate to the same activity,
                # differing only in `responsible` -- which "last node seen"
                # cannot tell apart. Since #250, a freshly-encoded node
                # also carries its own `prov:agent` triple, so prefer
                # whichever candidate's `prov:agent` matches this binary
                # triple's object; only fall back to "last node seen" (the
                # pre-#250 behaviour, which cannot do better) when no
                # candidate carries that triple at all, i.e. legacy
                # (pre-3.0) input.
                qualifier_bnode = candidate
                if (candidate, agent_pred, obj) in graph:
                    break
            if qualifier_bnode is not None:
                fakeys = list(state.formal_attributes[str(qualifier_bnode)].keys())
                state.formal_attributes[str(qualifier_bnode)][fakeys[0]] = subj
                state.formal_attributes[str(qualifier_bnode)][fakeys[1]] = str(obj)
                return
        factory(subj, str(obj))

    def _decode_attribute_triple(
        self,
        graph: Graph,
        state: "_DecodeState",
        subj: str,
        pred: URIRef,
        obj: Node,
        predicate_mapper: dict[URIRef, pm.QualifiedName],
    ) -> None:
        """Decode one non-relation triple into a formal or extra attribute.

        Args:
            graph: The RDF (sub)graph being decoded.
            state: Decode state, mutated in place.
            subj: The triple's subject, as a string.
            pred: The triple's predicate.
            obj: The triple's object.
            predicate_mapper: Maps PROV-O predicate URIRefs to formal
                attribute QualifiedNames.

        Raises:
            ValueError: If ``obj`` cannot be decoded to a usable value.
        """
        obj1 = self.decode_rdf_representation(obj, graph)
        if obj is not None and obj1 is None:
            raise ValueError(("Error transforming", obj))
        pred_new: URIRef | pm.QualifiedName = predicate_mapper.get(pred, pred)
        for needle, replacement in _DECODE_PREDICATE_REWRITES.get(
            state.record_types[subj], ()
        ):
            if needle in str(pred_new):
                pred_new = replacement
        # NOTE: `str(pred_new)` is the short prefixed form (e.g. "prov:time")
        # when `pred_new` came from `predicate_mapper` (a QualifiedName), but
        # `val.uri` below is always the full URI -- so a PREDICATE_MAP-routed
        # predicate (atTime/startedAtTime/endedAtTime/atLocation/hadRole/...)
        # never matches here and falls through to `other_attributes` instead
        # (a single occurrence is still recovered downstream, since
        # ProvRecord.add_attributes() matches extras against formal
        # attributes by qname on its own). This is deliberate, not an
        # oversight: matching it here would route repeated instances of such
        # a predicate into `unique_sets`, and `walk()` in
        # `_emit_decoded_records` would then emit more than one record for
        # the *same* identifier -- i.e. resurrect the rejected
        # permutation-decode option (see docs/reference/conformance.md) for
        # an identified qualified node. Do not "fix" this format mismatch.
        # On a qualified Start/End node specifically, `startedAtTime`/
        # `endedAtTime` have already been rewritten to `prov:time` by the
        # `_DECODE_PREDICATE_REWRITES` loop just above, so the name carried
        # into `other_attributes` for those two predicates is "prov:time",
        # not "prov:startTime"/"prov:endTime" -- the fall-through-then-
        # reconcile mechanism described here is otherwise unchanged.
        if str(pred_new) in [val.uri for val in state.formal_attributes[subj]]:
            qname_key = self.document.mandatory_valid_qname(pred_new)  # type: ignore[union-attr]
            state.formal_attributes[subj][qname_key] = obj1
            state.unique_sets[subj][qname_key].append(obj1)
            if len(state.unique_sets[subj][qname_key]) > 1:
                # An ambiguous formal attribute is cleared here and resolved
                # by walking every combination in _emit_decoded_records().
                state.formal_attributes[subj][qname_key] = None
        elif "qualified" not in str(pred_new) and "asInBundle" not in str(pred_new):
            state.other_attributes[subj].append((str(pred_new), obj1))

    def _emit_decoded_records(
        self, bundle: pm.ProvBundle, state: "_DecodeState"
    ) -> None:
        """Add a record to ``bundle`` for every decoded subject.

        A subject whose formal attributes picked up more than one candidate
        value yields one record per combination of those values.

        Args:
            bundle: Bundle to add the records to.
            state: Decode state; consumed attributes are removed from it, so
                what remains afterwards is what could not be converted.

        Raises:
            ProvException: If a subject carries more than one value for a
                formal attribute that :attr:`_DecodeState.unique_sets`
                doesn't track separately (e.g. two ``prov:atTime`` triples
                on one identified qualified node) -- the documented,
                permanent PROV-O representational limitation described in
                ``docs/reference/conformance.md``. Any other ``ProvException``
                raised while constructing a record (e.g. an unresolvable
                qualified name) propagates unchanged.
        """
        for subj in state.record_types:
            attrs = state.other_attributes.get(subj)
            items_to_walk = [
                (qname, values)
                for qname, values in state.unique_sets[subj].items()
                if values and len(values) > 1
            ]
            try:
                if items_to_walk:
                    for subset in list(walk(items_to_walk)):
                        for prov_type, value in subset.items():
                            state.formal_attributes[subj][prov_type] = value
                        bundle.new_record(
                            state.record_types[subj],
                            subj,
                            state.formal_attributes[subj].items(),
                            attrs,
                        )
                else:
                    bundle.new_record(
                        state.record_types[subj],
                        subj,
                        state.formal_attributes[subj].items(),
                        attrs,
                    )
            except pm.ProvException as exc:
                # Only relabel the specific #217 shape: a formal-attribute
                # predicate repeated in `attrs` (see the duplicate-detection
                # docstring below for why such repeats land there instead of
                # being walked). Anything else -- e.g. an unresolvable
                # qualified name -- is a genuinely different failure and
                # must propagate with its original message, not this one.
                duplicate_attr = _repeated_formal_attribute(
                    state.record_types[subj], attrs
                )
                if duplicate_attr is None:
                    raise
                raise pm.ProvException(
                    f"Cannot decode {subj!r} as a single "
                    f"{state.record_types[subj]} record: more than one "
                    f"value for formal attribute {duplicate_attr!r} ({exc}). "
                    "This is a documented PROV-O representational "
                    "limitation -- PROV-O reifies a relation as one "
                    "qualified node named by its identifier, so two "
                    "same-identifier relations that disagree on a formal "
                    "attribute (e.g. two prov:atTime values) cannot both be "
                    "represented. See "
                    "https://github.com/trungdong/prov/blob/master/docs/reference/conformance.md "
                    "for details."
                ) from exc

            if attrs is not None:
                del state.other_attributes[subj]


def _repeated_formal_attribute(
    record_type: pm.QualifiedName,
    attrs: list[tuple[pm.QualifiedNameCandidate, Any]] | None,
) -> str | None:
    """Return the formal-attribute name repeated in ``attrs``, if any.

    A predicate that :data:`PREDICATE_MAP` maps to a formal-attribute
    ``QualifiedName`` (e.g. ``prov:atTime``) never matches the URI-keyed
    lookup in :meth:`ProvRDFSerializer._decode_attribute_triple`
    (``str(pred_new)`` is the short prefixed form, e.g. ``"prov:time"``,
    compared against the full-URI ``val.uri`` of each formal-attribute
    ``QualifiedName`` -- deliberately left as-is, since "fixing" it would
    route such predicates into ``unique_sets`` and make ``walk()`` emit
    more than one record for the *same* identifier, i.e. the rejected
    permutation-decode option). A second instance of such a predicate on
    the same identified qualified node therefore lands in ``attrs`` as two
    same-key entries instead of being tracked there, and reaches
    :meth:`~prov.model.records.ProvRecord.add_attributes` as a duplicate
    plain attribute, which raises ``ProvException``. This function
    recognizes that specific shape so callers can relabel only it, leaving
    every other ``ProvException`` (e.g. an unresolvable qualified name)
    untouched.

    Note: on a qualified node, ``Start``/``End`` carry their time as
    ``prov:atTime`` too, matching every other timed relation's generic
    ``prov:time`` formal attribute. Some producers instead put the binary-
    triple predicates ``prov:startedAtTime``/``prov:endedAtTime`` directly
    on the qualified Start/End node; :data:`_DECODE_PREDICATE_REWRITES`
    rewrites those onto ``prov:time`` too (issue #299), so a duplicate of
    either one lands here as a repeated ``prov:time`` entry, exactly like a
    duplicated ``prov:atTime``, and is relabelled the same way.

    Args:
        record_type: The record type being constructed.
        attrs: The subject's non-formal attributes, as passed to
            :meth:`~prov.model.ProvBundle.new_record`.

    Returns:
        The (string) formal-attribute name that appears more than once in
        ``attrs``, or ``None`` if ``attrs`` has no such repeat.
    """
    if not attrs:
        return None
    formal_names = {str(q) for q in pm.PROV_REC_CLS[record_type].FORMAL_ATTRIBUTES}
    seen: set[str] = set()
    for key, _value in attrs:
        key_str = str(key)
        if key_str in formal_names:
            if key_str in seen:
                return key_str
            seen.add(key_str)
    return None


def walk(
    children: list[tuple[Any, Any]],
    level: int = 0,
    path: dict[Any, Any] | None = None,
    usename: bool = True,
) -> Generator[dict[Any, Any]]:
    """Generate all the full paths in a tree, as a dict.

    Args:
        children: ``(name, iterable)`` pairs; each is one level of the tree,
            enumerated in order. Each ``iterable`` must be an iterable of
            values (not a callable) -- it is iterated directly.
        level: Current recursion depth; only used as the dict key when
            ``usename`` is ``False``.
        path: Path accumulated so far; ``None`` (the default) starts a fresh
            path at the top-level call.
        usename: If ``True``, key each path dict by the level's ``name``;
            if ``False``, key it by the level's integer depth instead.

    Yields:
        One dict per full path through ``children``, mapping each level's
        key to the value chosen at that level.

    Example:
        >>> from prov.serializers.provrdf import walk
        >>> iterables = [('a', [1, 2]), ('b', [3, 4])]
        >>> [val['a'] for val in walk(iterables)]
        [1, 1, 2, 2]
        >>> [val['b'] for val in walk(iterables)]
        [3, 4, 3, 4]
    """
    # Entry point
    if path is None:
        path = {}

    # Exit condition
    if not children:
        yield path.copy()
        return
    # Tree recursion
    head, tail = children[0], children[1:]
    name, func = head
    for child in func:
        # We can use the arg name or the tree level as a key
        if usename:
            path[name] = child
        else:
            path[level] = child
        # Recurse into the next level
        yield from walk(tail, level + 1, path, usename)


def literal_rdf_representation(literal: pm.Literal) -> RDFLiteral:
    """Encode a :class:`~prov.model.Literal` to an ``rdflib.Literal``.

    Args:
        literal: Literal to encode.

    Returns:
        A language-tagged ``rdflib.Literal`` if ``literal`` has a language
        tag, otherwise a datatype-tagged one (base64-encoding the value
        first for ``xsd:base64Binary``).

    Raises:
        ValueError: If ``literal`` has neither a language tag nor a
            datatype.
    """
    if literal.langtag:
        #  a language tag can only go with prov:InternationalizedString
        return RDFLiteral(literal.value, lang=literal.langtag)
    else:
        datatype = literal.datatype
        if datatype is not None:
            if "base64Binary" in datatype.uri:
                return RDFLiteral(literal.value.encode(), datatype=datatype.uri)
            elif datatype == XSD_DOUBLE:
                # Same precision-preserving datatype as the plain-float path
                # in encode_rdf_representation (#225): the literal's own
                # lexical form is already the asserted value's string, so
                # just skip rdflib's bare-double abbreviation on output.
                return _FullPrecisionDoubleLiteral(literal.value, datatype=datatype.uri)
            else:
                return RDFLiteral(literal.value, datatype=datatype.uri)
        else:
            raise ValueError("Literal has no datatype")
