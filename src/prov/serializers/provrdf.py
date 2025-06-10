"""PROV-RDF serializers for ProvDocument"""

from __future__ import annotations  # needed for | type annotations in Python < 3.10
import base64
from collections import OrderedDict
import datetime
import io
from typing import Any, Optional, Generator
import warnings

import dateutil.parser

from rdflib.term import URIRef, BNode  # type: ignore[import-not-found]
from rdflib.term import Literal as RDFLiteral
from rdflib.graph import ConjunctiveGraph  # type: ignore[import-not-found]
from rdflib.namespace import RDF, RDFS, XSD  # type: ignore[import-not-found]

from prov import Error
import prov.model as pm
from prov.constants import (
    PROV,
    PROV_ID_ATTRIBUTES_MAP,
    PROV_N_MAP,
    PROV_BASE_CLS,
    XSD_QNAME,
    PROV_END,
    PROV_START,
    PROV_USAGE,
    PROV_GENERATION,
    PROV_DERIVATION,
    PROV_INVALIDATION,
    PROV_ALTERNATE,
    PROV_MENTION,
    PROV_DELEGATION,
    PROV_ACTIVITY,
    PROV_ATTR_STARTTIME,
    PROV_ATTR_ENDTIME,
    PROV_LOCATION,
    PROV_ATTR_TIME,
    PROV_ROLE,
    PROV_COMMUNICATION,
    PROV_ATTR_INFORMANT,
    PROV_ATTR_RESPONSIBLE,
    PROV_ATTR_TRIGGER,
    PROV_ATTR_ENDER,
    PROV_ATTR_STARTER,
    PROV_ATTR_USED_ENTITY,
    PROV_ASSOCIATION,
)
from prov.identifier import QualifiedName
from prov.serializers import Serializer


__author__ = "Satrajit S. Ghosh"
__email__ = "satra@mit.edu"


class ProvRDFException(Error):
    pass


class AnonymousIDGenerator:
    def __init__(self) -> None:
        self._cache = {}  # type: dict[Any, str]
        self._count = 0  # type: int

    def get_anon_id(self, obj: pm.ProvRecord, local_prefix: str = "id") -> str:
        if obj not in self._cache:
            self._count += 1
            self._cache[obj] = "_:%s%d" % (local_prefix, self._count)
        return self._cache[obj]


# Reverse map for prov.model.XSD_DATATYPE_PARSERS
LITERAL_XSDTYPE_MAP = {
    float: XSD["double"],
    int: XSD["int"],
    str: XSD["string"],
    # boolean, string values are supported natively by PROV-RDF
    # datetime values are converted separately
}

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


def attr2rdf(attr: QualifiedName) -> URIRef:
    return URIRef(PROV[PROV_ID_ATTRIBUTES_MAP[attr].split("prov:")[1]].uri)


class ProvRDFSerializer(Serializer):
    """
    PROV-O serializer for :class:`~prov.model.ProvDocument`
    """

    def serialize(
        self,
        stream: io.IOBase,
        rdf_format: str = "trig",
        PROV_N_MAP: dict[pm.QualifiedName, str] = PROV_N_MAP,
        **kwargs: Any,
    ) -> None:
        """
        Serializes a :class:`~prov.model.ProvDocument` instance to
        `PROV-O <https://www.w3.org/TR/prov-o/>`_.

        :param stream: Where to save the output.
        :param rdf_format: The RDF format of the output, default to TRiG.
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
            if isinstance(stream, io.TextIOBase):
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
        """
        Deserialize from the `PROV-O <https://www.w3.org/TR/prov-o/>`_
        representation to a :class:`~prov.model.ProvDocument` instance.

        :param stream: Input data.
        :param rdf_format: The RDF format of the input data, default: TRiG.
        """
        newargs = kwargs.copy()
        newargs["format"] = rdf_format
        container = ConjunctiveGraph()
        container.parse(stream, **newargs)
        self.document = pm.ProvDocument()
        self.decode_document(
            container,
            self.document,
            relation_mapper=relation_mapper,
            predicate_mapper=predicate_mapper,
        )
        return self.document

    def valid_identifier(
        self, value: pm.QualifiedNameCandidate
    ) -> pm.QualifiedName | None:
        return self.document.valid_qualified_name(value)  # type: ignore[union-attr]

    def encode_rdf_representation(self, value: Any) -> RDFLiteral | URIRef:
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
        elif type(value) in LITERAL_XSDTYPE_MAP:
            return RDFLiteral(value, datatype=LITERAL_XSDTYPE_MAP[type(value)])
        else:
            return RDFLiteral(value)

    def decode_rdf_representation(self, literal: Any, graph: ConjunctiveGraph) -> Any:
        if isinstance(literal, RDFLiteral):
            value = literal.value if literal.value is not None else literal
            datatype = literal.datatype
            langtag = literal.language
            if datatype and "XMLLiteral" in datatype:
                value = literal
            if datatype and "base64Binary" in datatype:
                value = base64.standard_b64encode(value)
            if datatype == XSD["QName"]:
                return pm.Literal(literal, datatype=XSD_QNAME)
            if datatype == XSD["dateTime"]:
                return dateutil.parser.parse(literal)
            if datatype == XSD["gYear"]:
                return pm.Literal(
                    dateutil.parser.parse(literal).year,
                    datatype=self.valid_identifier(datatype),
                )
            if datatype == XSD["gYearMonth"]:
                parsed_info = dateutil.parser.parse(literal)
                return pm.Literal(
                    "{0}-{1:02d}".format(parsed_info.year, parsed_info.month),
                    datatype=self.valid_identifier(datatype),
                )
            else:
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
    ) -> ConjunctiveGraph:
        container = self.encode_container(document)
        for item in document.bundles:
            #  encoding the sub-bundle
            bundle = self.encode_container(
                item, identifier=item.identifier.uri, PROV_N_MAP=PROV_N_MAP  # type: ignore[union-attr]
            )
            container.addN(bundle.quads())
        return container

    def encode_container(
        self,
        bundle: pm.ProvBundle,
        PROV_N_MAP: dict[pm.QualifiedName, str] = PROV_N_MAP,
        container: Optional[ConjunctiveGraph] = None,
        identifier: Optional[str] = None,
    ) -> ConjunctiveGraph:
        if container is None:
            container = ConjunctiveGraph(identifier=identifier)
            nm = container.namespace_manager
            nm.bind("prov", PROV.uri)

        for namespace in bundle.namespaces:
            container.bind(namespace.prefix, namespace.uri)

        id_generator = AnonymousIDGenerator()
        real_or_anon_id = lambda record: (
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
                for attrid, (attr, value) in enumerate(list(record.formal_attributes)):
                    if (identifier is not None and value is not None) or (
                        identifier is None and value is not None and attrid > 1
                    ):
                        formal_qualifiers = True
                has_qualifiers = len(record.extra_attributes) > 0 or formal_qualifiers
                for idx, (attr, value) in enumerate(all_attributes):
                    if record.is_relation():
                        pred = URIRef(PROV[PROV_N_MAP[rec_type]].uri)
                        # create bnode relation
                        if bnode is None:
                            valid_formal_indices = set()
                            for idx, (key, val) in enumerate(record.formal_attributes):
                                formal_objects.append(key)
                                if val:
                                    valid_formal_indices.add(idx)
                            used_objects = [record.formal_attributes[0][0]]
                            subj = None
                            if record.formal_attributes[0][1]:
                                subj = URIRef(record.formal_attributes[0][1].uri)
                            if identifier is None and subj is not None:
                                try:
                                    obj_val = record.formal_attributes[1][1]
                                    obj_attr = URIRef(
                                        record.formal_attributes[1][0].uri
                                    )
                                    # TODO: Why is obj_attr above not used anywhere?
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
                                    if attr_name == PROV["type"]:
                                        if (
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
                                if PROV_ATTR_STARTTIME in pred:
                                    pred = URIRef(PROV["startedAtTime"].uri)
                                if PROV_ATTR_ENDTIME in pred:
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
                                    identifier,
                                    pred,
                                    self.encode_rdf_representation(value),
                                )
                            )
                        continue
                    if value is None:
                        continue
                    if isinstance(value, pm.ProvRecord):
                        obj = URIRef(str(real_or_anon_id(value)))
                    else:
                        #  Assuming this is a datetime value
                        obj = self.encode_rdf_representation(value)
                    if attr == PROV["location"]:
                        pred = URIRef(PROV["atLocation"].uri)
                        if False and isinstance(value, (URIRef, pm.QualifiedName)):
                            if isinstance(value, pm.QualifiedName):
                                value = URIRef(value.uri)
                            container.add((identifier, pred, value))
                        else:
                            container.add(
                                (identifier, pred, self.encode_rdf_representation(obj))
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
                    container.add((identifier, pred, obj))
        return container

    def decode_document(
        self,
        content: ConjunctiveGraph,
        document: pm.ProvDocument,
        relation_mapper: dict[URIRef, str] = RELATION_MAP,
        predicate_mapper: dict[URIRef, pm.QualifiedName] = PREDICATE_MAP,
    ) -> None:
        for prefix, url in content.namespaces():
            document.add_namespace(prefix, str(url))
        if hasattr(content, "contexts"):
            for graph in content.contexts():
                if isinstance(graph.identifier, BNode):
                    self.decode_container(
                        graph,
                        document,
                        relation_mapper=relation_mapper,
                        predicate_mapper=predicate_mapper,
                    )
                else:
                    bundle_id = str(graph.identifier)
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
        graph: ConjunctiveGraph,
        bundle: pm.ProvBundle,
        relation_mapper: dict[URIRef, str] = RELATION_MAP,
        predicate_mapper: dict[URIRef, pm.QualifiedName] = PREDICATE_MAP,
    ) -> None:
        record_types = {}  # type: dict[str, pm.QualifiedName]
        PROV_CLS_MAP = {}  # type: dict[str, pm.QualifiedName]
        formal_attributes = (
            {}
        )  # type: dict[str, dict[pm.QualifiedName, Optional[pm.QualifiedNameCandidate | datetime.datetime]]]
        unique_sets = (
            {}
        )  # type: dict[str, dict[pm.QualifiedName, list[pm.QualifiedNameCandidate | datetime.datetime]]]
        for prov_type, _ in PROV_BASE_CLS.items():
            PROV_CLS_MAP[prov_type.uri] = PROV_BASE_CLS[prov_type]
        other_attributes = (
            {}
        )  # type: dict[str, list[tuple[pm.QualifiedNameCandidate, Any]]]
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
                isderivation = (
                    pm.PROV["Revision"].uri in stmt[2]
                    or pm.PROV["Quotation"].uri in stmt[2]
                    or pm.PROV["PrimarySource"].uri in stmt[2]
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
                pred_new = pred
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
            if local_key in record_types:
                if "qualified" in pred:
                    formal_attributes[local_key][
                        list(formal_attributes[local_key].keys())[0]
                    ] = subj
        for subj in record_types:
            attrs = None
            if subj in other_attributes:
                attrs = other_attributes[subj]
            items_to_walk = (
                []
            )  # type: list[tuple[pm.QualifiedName, list[pm.QualifiedNameCandidate | datetime.datetime]]]
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
            )


def walk(
    children: list, level: int = 0, path: dict = None, usename: bool = True  # type: ignore[assignment]
) -> Generator[dict]:
    """Generate all the full paths in a tree, as a dict.

    :Example:

    >>> from prov.serializers.provrdf import walk
    >>> iterables = [('a', lambda: [1, 2]), ('b', lambda: [3, 4])]
    >>> [val['a'] for val in walk(iterables)]
    [1, 1, 2, 2]
    >>> [val['b'] for val in walk(iterables)]
    [3, 4, 3, 4]
    """
    # Entry point
    if level == 0:
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
        for child_paths in walk(tail, level + 1, path, usename):
            yield child_paths


def literal_rdf_representation(literal: pm.Literal) -> RDFLiteral:
    if literal.langtag:
        #  a language tag can only go with prov:InternationalizedString
        return RDFLiteral(literal.value, lang=literal.langtag)
    else:
        datatype = literal.datatype
        if datatype is not None:
            if "base64Binary" in datatype.uri:
                return RDFLiteral(literal.value.encode(), datatype=datatype.uri)
            else:
                return RDFLiteral(literal.value, datatype=datatype.uri)
        else:
            raise ValueError("Literal has no datatype")
