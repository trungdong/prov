"""PROV-RDF serializers for ProvDocument"""

import base64
import datetime
import io
import re
import warnings
from collections import OrderedDict
from collections.abc import Generator
from typing import Any, cast

from rdflib import RDF, RDFS, XSD
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID, Dataset, Graph
from rdflib.term import BNode, Literal as RDFLiteral, Node, URIRef

import prov.model as pm
from prov import Error
from prov.constants import (
    PROV,
    PROV_ACTIVITY,
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
    PROV_BASE_CLS,
    PROV_COMMUNICATION,
    PROV_DELEGATION,
    PROV_DERIVATION,
    PROV_END,
    PROV_GENERATION,
    PROV_ID_ATTRIBUTES_MAP,
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
            datatype = LITERAL_XSDTYPE_MAP[type(value)]
            if datatype == XSD["double"]:
                # Full-precision lexical form, and a datatype that skips
                # rdflib's precision-losing bare-double abbreviation (#225).
                return _FullPrecisionDoubleLiteral(repr(value), datatype=datatype)
            return RDFLiteral(value, datatype=datatype)
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
                # rdflib decodes xsd:base64Binary literals to bytes
                value = base64.standard_b64encode(cast(bytes, value))
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
            container.addN((s, p, o, bundle) for s, p, o in bundle)
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

        id_generator = AnonymousIDGenerator()

        def real_or_anon_id(record: pm.ProvRecord) -> str:
            return (
                record._identifier.uri
                if record._identifier
                else id_generator.get_anon_id(record)
            )

        for record in bundle._records:
            rec_type = record.get_type()
            if hasattr(record, "identifier") and record.identifier:
                identifier = URIRef(str(real_or_anon_id(record)))
                container.add((identifier, RDF.type, URIRef(rec_type.uri)))
            else:
                identifier = None
            if record.attributes:
                bnode = None
                formal_objects = []
                used_objects = []
                all_attributes = list(record.formal_attributes) + list(
                    record.attributes
                )
                formal_qualifiers = False
                for attrid, (_attr, value) in enumerate(list(record.formal_attributes)):
                    if (identifier is not None and value is not None) or (
                        identifier is None and value is not None and attrid > 1
                    ):
                        formal_qualifiers = True
                has_qualifiers = len(record.extra_attributes) > 0 or formal_qualifiers
                for idx, (attr, value) in enumerate(all_attributes):
                    if record.is_relation():
                        pred: URIRef | RDFLiteral = URIRef(
                            PROV[PROV_N_MAP[rec_type]].uri
                        )
                        # create bnode relation
                        if bnode is None:
                            valid_formal_indices = set()
                            for idx, (key, val) in enumerate(record.formal_attributes):
                                formal_objects.append(key)
                                if val:
                                    valid_formal_indices.add(idx)
                            used_objects = [record.formal_attributes[0][0]]
                            subj: URIRef | RDFLiteral | None = None
                            if record.formal_attributes[0][1]:
                                subj = URIRef(record.formal_attributes[0][1].uri)
                            if identifier is None and subj is not None:
                                try:
                                    obj_val = record.formal_attributes[1][1]
                                except IndexError:
                                    obj_val = None
                                if obj_val and (
                                    rec_type
                                    not in {
                                        PROV_END,
                                        PROV_START,
                                        PROV_USAGE,
                                        PROV_GENERATION,
                                        PROV_DERIVATION,
                                        PROV_ASSOCIATION,
                                        PROV_INVALIDATION,
                                    }
                                    or (
                                        valid_formal_indices == {0, 1}
                                        and len(record.extra_attributes) == 0
                                    )
                                ):
                                    used_objects.append(record.formal_attributes[1][0])
                                    obj_val = self.encode_rdf_representation(obj_val)
                                    if rec_type == PROV_ALTERNATE:
                                        subj, obj_val = obj_val, subj
                                    container.add((subj, pred, obj_val))
                                    if rec_type == PROV_MENTION:
                                        if record.formal_attributes[2][1]:
                                            used_objects.append(
                                                record.formal_attributes[2][0]
                                            )
                                            obj_val = self.encode_rdf_representation(
                                                record.formal_attributes[2][1]
                                            )
                                            container.add(
                                                (
                                                    subj,
                                                    URIRef(PROV["asInBundle"].uri),
                                                    obj_val,
                                                )
                                            )
                                        has_qualifiers = False
                            if rec_type in [PROV_ALTERNATE]:
                                continue
                            if subj and (has_qualifiers or identifier):
                                qualifier = rec_type._localpart
                                rec_uri = rec_type.uri
                                for attr_name, val in record.extra_attributes:
                                    if attr_name == PROV["type"] and (
                                        PROV["Revision"] == val
                                        or PROV["Quotation"] == val
                                        or PROV["PrimarySource"] == val
                                    ):
                                        qualifier = val._localpart
                                        rec_uri = val.uri
                                        if identifier is not None:
                                            container.remove(
                                                (
                                                    identifier,
                                                    RDF.type,
                                                    URIRef(rec_type.uri),
                                                )
                                            )
                                QRole = URIRef(PROV["qualified" + qualifier].uri)
                                if identifier is not None:
                                    container.add((subj, QRole, identifier))
                                else:
                                    bnode = identifier = BNode()
                                    container.add((subj, QRole, identifier))
                                    container.add(
                                        (identifier, RDF.type, URIRef(rec_uri))
                                    )  # reset identifier to BNode
                        if value is not None and attr not in used_objects:
                            if attr in formal_objects:
                                pred = attr2rdf(attr)
                            elif attr == PROV["role"]:
                                pred = URIRef(PROV["hadRole"].uri)
                            elif attr == PROV["plan"]:
                                pred = URIRef(PROV["hadPlan"].uri)
                            elif attr == PROV["type"]:
                                pred = RDF.type
                            elif attr == PROV["label"]:
                                pred = RDFS.label
                            elif isinstance(attr, pm.QualifiedName):
                                pred = URIRef(attr.uri)
                            else:
                                pred = self.encode_rdf_representation(attr)
                            if PROV["plan"].uri in pred:
                                pred = URIRef(PROV["hadPlan"].uri)
                            if PROV["informant"].uri in pred:
                                pred = URIRef(PROV["activity"].uri)
                            if PROV["responsible"].uri in pred:
                                pred = URIRef(PROV["agent"].uri)
                            if (
                                rec_type == PROV_DELEGATION
                                and PROV["activity"].uri in pred
                            ):
                                pred = URIRef(PROV["hadActivity"].uri)
                            if (
                                rec_type in [PROV_END, PROV_START]
                                and PROV["trigger"].uri in pred
                            ) or (
                                rec_type in [PROV_USAGE] and PROV["used"].uri in pred
                            ):
                                pred = URIRef(PROV["entity"].uri)
                            if rec_type in [
                                PROV_GENERATION,
                                PROV_END,
                                PROV_START,
                                PROV_USAGE,
                                PROV_INVALIDATION,
                            ]:
                                if PROV["time"].uri in pred:
                                    pred = URIRef(PROV["atTime"].uri)
                                if PROV["ender"].uri in pred:
                                    pred = URIRef(PROV["hadActivity"].uri)
                                if PROV["starter"].uri in pred:
                                    pred = URIRef(PROV["hadActivity"].uri)
                                if PROV["location"].uri in pred:
                                    pred = URIRef(PROV["atLocation"].uri)
                            if rec_type in [PROV_ACTIVITY]:
                                # dead branch kept as-is: rec_type is never
                                # PROV_ACTIVITY inside the is_relation() path, and
                                # `QualifiedName in URIRef` would raise TypeError
                                if PROV_ATTR_STARTTIME in pred:  # type: ignore[operator]
                                    pred = URIRef(PROV["startedAtTime"].uri)
                                if PROV_ATTR_ENDTIME in pred:  # type: ignore[operator]
                                    pred = URIRef(PROV["endedAtTime"].uri)
                            if rec_type == PROV_DERIVATION:
                                if PROV["activity"].uri in pred:
                                    pred = URIRef(PROV["hadActivity"].uri)
                                if PROV["generation"].uri in pred:
                                    pred = URIRef(PROV["hadGeneration"].uri)
                                if PROV["usage"].uri in pred:
                                    pred = URIRef(PROV["hadUsage"].uri)
                                if PROV["usedEntity"].uri in pred:
                                    pred = URIRef(PROV["entity"].uri)
                            container.add(
                                (
                                    # a qualified relation always has a URIRef or
                                    # BNode identifier by this point
                                    cast("URIRef | BNode", identifier),
                                    pred,
                                    self.encode_rdf_representation(value),
                                )
                            )
                        continue
                    if value is None:
                        continue
                    if isinstance(value, pm.ProvRecord):
                        obj: RDFLiteral | URIRef = URIRef(str(real_or_anon_id(value)))
                    else:
                        #  Assuming this is a datetime value
                        obj = self.encode_rdf_representation(value)
                    if attr == PROV["location"]:
                        pred = URIRef(PROV["atLocation"].uri)
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
                    if attr == PROV["type"]:
                        pred = RDF.type
                    elif attr == PROV["label"]:
                        pred = RDFS.label
                    elif attr == PROV_ATTR_STARTTIME:
                        pred = URIRef(PROV["startedAtTime"].uri)
                    elif attr == PROV_ATTR_ENDTIME:
                        pred = URIRef(PROV["endedAtTime"].uri)
                    else:
                        pred = self.encode_rdf_representation(attr)
                    # elements always carry an identifier here
                    container.add((cast("URIRef | BNode", identifier), pred, obj))
        return container

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
        record_types = {}  # type: dict[str, pm.QualifiedName]
        PROV_CLS_MAP = {}  # type: dict[str, pm.QualifiedName]
        formal_attributes = {}  # type: dict[str, dict[pm.QualifiedName, pm.QualifiedNameCandidate | datetime.datetime | None]]
        unique_sets = {}  # type: dict[str, dict[pm.QualifiedName, list[pm.QualifiedNameCandidate | datetime.datetime]]]
        for prov_type, _ in PROV_BASE_CLS.items():
            PROV_CLS_MAP[prov_type.uri] = PROV_BASE_CLS[prov_type]
        other_attributes = {}  # type: dict[str, list[tuple[pm.QualifiedNameCandidate, Any]]]
        # subj/obj hold rdflib terms (Node) when bound by the triple loops below
        # and their string forms after conversion
        subj: str | Node
        obj: str | Node
        for stmt in graph.triples((None, RDF.type, None)):
            subj = str(stmt[0])
            obj = str(stmt[2])
            if obj in PROV_CLS_MAP:
                if (
                    not isinstance(stmt[0], BNode)
                    and self.valid_identifier(subj) is None
                ):
                    prefix, iri, _ = graph.namespace_manager.compute_qname(subj)
                    self.document.add_namespace(prefix, iri)  # type: ignore[union-attr]
                try:
                    prov_obj = PROV_CLS_MAP[obj]
                except AttributeError:
                    prov_obj = None
                add_attr = True
                # objects of rdf:type triples are URIRefs (str subclass);
                # rdflib types them only as Node
                isderivation = (
                    pm.PROV["Revision"].uri in cast(str, stmt[2])
                    or pm.PROV["Quotation"].uri in cast(str, stmt[2])
                    or pm.PROV["PrimarySource"].uri in cast(str, stmt[2])
                )
                if (
                    subj not in record_types
                    and prov_obj
                    and (
                        prov_obj.uri == obj
                        or isderivation
                        or isinstance(stmt[0], BNode)
                    )
                ):
                    record_types[subj] = prov_obj
                    klass = pm.PROV_REC_CLS[prov_obj]
                    formal_attributes[subj] = OrderedDict(
                        [(key, None) for key in klass.FORMAL_ATTRIBUTES]
                    )
                    unique_sets[subj] = OrderedDict(
                        [(key, []) for key in klass.FORMAL_ATTRIBUTES]
                    )
                    add_attr = False or (
                        (isinstance(stmt[0], BNode) or isderivation)
                        and prov_obj.uri != obj
                    )
                if add_attr:
                    if subj not in other_attributes:
                        other_attributes[subj] = []
                    obj_formatted = self.decode_rdf_representation(stmt[2], graph)
                    other_attributes[subj].append((pm.PROV["type"], obj_formatted))
            else:
                if subj not in other_attributes:
                    other_attributes[subj] = []
                obj = self.decode_rdf_representation(stmt[2], graph)
                other_attributes[subj].append((pm.PROV["type"], obj))
        for subj, pred, obj in graph:
            subj = str(subj)
            # predicates in RDF are always URIRefs; rdflib types them as Node
            pred = cast(URIRef, pred)
            if subj not in other_attributes:
                other_attributes[subj] = []
            if pred == RDF.type:
                continue
            if pred in relation_mapper:
                if "alternateOf" in pred:
                    getattr(bundle, relation_mapper[pred])(obj, subj)
                elif "mentionOf" in pred:
                    mentionBundle = None
                    for stmt in graph.triples(
                        (URIRef(subj), URIRef(pm.PROV["asInBundle"].uri), None)
                    ):
                        mentionBundle = stmt[2]
                    getattr(bundle, relation_mapper[pred])(
                        subj, str(obj), mentionBundle
                    )
                elif "actedOnBehalfOf" in pred or "wasAssociatedWith" in pred:
                    qualifier = (
                        "qualified"
                        + relation_mapper[pred].upper()[0]
                        + relation_mapper[pred][1:]
                    )
                    qualifier_bnode = None
                    for stmt in graph.triples(
                        (URIRef(subj), URIRef(pm.PROV[qualifier].uri), None)
                    ):
                        qualifier_bnode = stmt[2]
                    if qualifier_bnode is None:
                        getattr(bundle, relation_mapper[pred])(subj, str(obj))
                    else:
                        fakeys = list(formal_attributes[str(qualifier_bnode)].keys())
                        formal_attributes[str(qualifier_bnode)][fakeys[0]] = subj
                        formal_attributes[str(qualifier_bnode)][fakeys[1]] = str(obj)
                else:
                    getattr(bundle, relation_mapper[pred])(subj, str(obj))
            elif subj in record_types:
                obj1 = self.decode_rdf_representation(obj, graph)
                if obj is not None and obj1 is None:
                    raise ValueError(("Error transforming", obj))
                pred_new: URIRef | pm.QualifiedName = pred
                if pred in predicate_mapper:
                    pred_new = predicate_mapper[pred]
                if record_types[subj] == PROV_COMMUNICATION and "activity" in str(
                    pred_new
                ):
                    pred_new = PROV_ATTR_INFORMANT
                if record_types[subj] == PROV_DELEGATION and "agent" in str(pred_new):
                    pred_new = PROV_ATTR_RESPONSIBLE
                if record_types[subj] in [PROV_END, PROV_START] and "entity" in str(
                    pred_new
                ):
                    pred_new = PROV_ATTR_TRIGGER
                if record_types[subj] in [PROV_END] and "activity" in str(pred_new):
                    pred_new = PROV_ATTR_ENDER
                if record_types[subj] in [PROV_START] and "activity" in str(pred_new):
                    pred_new = PROV_ATTR_STARTER
                if record_types[subj] == PROV_DERIVATION and "entity" in str(pred_new):
                    pred_new = PROV_ATTR_USED_ENTITY
                if str(pred_new) in [val.uri for val in formal_attributes[subj]]:
                    qname_key = self.document.mandatory_valid_qname(pred_new)  # type: ignore[union-attr]
                    formal_attributes[subj][qname_key] = obj1
                    unique_sets[subj][qname_key].append(obj1)
                    if len(unique_sets[subj][qname_key]) > 1:
                        formal_attributes[subj][qname_key] = None
                else:
                    if "qualified" not in str(pred_new) and "asInBundle" not in str(
                        pred_new
                    ):
                        other_attributes[subj].append((str(pred_new), obj1))
            local_key = str(obj)
            if local_key in record_types and "qualified" in pred:
                formal_attributes[local_key][
                    next(iter(formal_attributes[local_key].keys()))
                ] = subj
        for subj in record_types:
            attrs = None
            if subj in other_attributes:
                attrs = other_attributes[subj]
            items_to_walk = []  # type: list[tuple[pm.QualifiedName, list[pm.QualifiedNameCandidate | datetime.datetime]]]
            for qname, values in unique_sets[subj].items():
                if values and len(values) > 1:
                    items_to_walk.append((qname, values))
            if items_to_walk:
                for subset in list(walk(items_to_walk)):
                    for prov_type, value in subset.items():
                        formal_attributes[subj][prov_type] = value
                    bundle.new_record(
                        record_types[subj], subj, formal_attributes[subj].items(), attrs
                    )
            else:
                bundle.new_record(
                    record_types[subj], subj, formal_attributes[subj].items(), attrs
                )

            if attrs is not None:
                del other_attributes[subj]

        if other_attributes:
            warnings.warn(
                "The following attributes were not converted: " + str(other_attributes),
                UserWarning,
                stacklevel=2,
            )


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
