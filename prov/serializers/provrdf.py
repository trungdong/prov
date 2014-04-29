"""PROV-JSON serializers for ProvDocument

@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2014
"""
import logging
logger = logging.getLogger(__name__)

from collections import defaultdict
import datetime
import json
from prov import Serializer, Error
from prov.constants import *
from prov.model import (Literal, Identifier, QName, Namespace, ProvRecord,
                        ProvDocument)

attr2rdf = lambda attr: URIRef(PROV[PROV_ID_ATTRIBUTES_MAP[attr].split('prov:')[1]].uri)

from rdflib.term import URIRef, BNode
from rdflib.term import Literal as RDFLiteral
from rdflib.graph import ConjunctiveGraph
from rdflib.namespace import RDF, RDFS, XSD

class ProvRDFException(Error):
    pass


class AnonymousIDGenerator():
    def __init__(self):
        self._cache = {}
        self._count = 0

    def get_anon_id(self, obj, local_prefix="id"):
        if obj not in self._cache:
            self._count += 1
            self._cache[obj] = Identifier('_:%s%d' % (local_prefix,
                                                      self._count)).uri
        return self._cache[obj]


# Reverse map for prov.model.XSD_DATATYPE_PARSERS
LITERAL_XSDTYPE_MAP = {
    float: XSD['double'],
    long: XSD['long'],
    int: XSD['int'],
    # boolean, string values are supported natively by PROV-JSON
    # datetime values are converted separately
}


class ProvRDFSerializer(Serializer):
    def serialize(self, stream=None, **kwargs):
        container = self.encode_document(self.document)
        newargs = kwargs.copy()
        if newargs and 'rdf_format' in newargs:
            newargs['format'] = newargs['rdf_format']
            del newargs['rdf_format']
        container.serialize(stream, **newargs)

    def deserialize(self, stream, **kwargs):
        container = json.load(stream, **kwargs)
        document = ProvDocument()
        self.document = document
        self.decode_document(container, document)
        return document

    def valid_identifier(self, value):
        return self.document.valid_identifier(value)

    def encode_rdf_representation(self, value):
        if isinstance(value, Literal):
            return literal_rdf_representation(value)
        elif isinstance(value, datetime.datetime):
            return RDFLiteral(value.isoformat(), datatype=XSD['dateTime'])
        elif isinstance(value, (QName, Identifier)):
            return URIRef(value.uri)
        elif type(value) in LITERAL_XSDTYPE_MAP:
            return RDFLiteral(value, datatype=LITERAL_XSDTYPE_MAP[type(value)])
        else:
            return RDFLiteral(value)

    def decode_rdf_representation(self, literal):
        if isinstance(literal, dict):
            # complex type
            value = literal['$']
            datatype = literal['type'] if 'type' in literal else None
            langtag = literal['lang'] if 'lang' in literal else None
            if datatype == u'xsd:anyURI':
                return Identifier(value)
            elif datatype == u'prov:QualifiedName':
                return self.valid_identifier(value)
            else:
                # The literal of standard Python types is not converted here
                # It will be automatically converted when added to a record by _auto_literal_conversion()
                return Literal(value, self.valid_identifier(datatype), langtag)
        else:
            # simple type, just return it
            return literal

    def encode_document(self, document):
        container = self.encode_container(document)
        for b_id, b in document._bundles.items():
            #  encoding the sub-bundle
            bundle_json = self.encode_container(b)
            container['bundle'][unicode(b_id)] = bundle_json
        return container

    def encode_container(self, bundle):
        container = ConjunctiveGraph()
        nm = container.namespace_manager
        nm.bind('prov', PROV.uri)
        prefixes = {}
        for namespace in bundle._namespaces.get_registered_namespaces():
            container.bind(namespace.prefix, namespace.uri)
        if bundle._namespaces._default:
            prefixes['default'] = bundle._namespaces._default.uri

        id_generator = AnonymousIDGenerator()
        real_or_anon_id = lambda record: record._identifier.uri if \
            record._identifier else id_generator.get_anon_id(record)

        for record in bundle._records:
            rec_type = record.get_type()
            rec_label = PROV[PROV_N_MAP[rec_type]].uri
            if record.is_relation():
                identifier = None
            else:
                identifier = URIRef(unicode(real_or_anon_id(record)))
                container.add((identifier, RDF.type, URIRef(rec_type.uri)))
            if record._attributes:
                for idx, (attr, value) in enumerate(record._attributes.items()):
                    if record.is_relation():
                        pred = URIRef(PROV[PROV_N_MAP[rec_type]].uri)
                        print idx, attr, value
                        if idx == 0:
                            identifier = URIRef(value.uri)
                        elif idx == 1:
                            if value:
                                obj = URIRef(value.uri)
                                container.add((identifier, pred, obj))
                            QRole = URIRef(PROV['qualified' +
                                                rec_type.get_localpart()].uri)
                            bnode = BNode()
                            container.add((identifier, QRole, bnode))
                            container.add((bnode, RDF.type,
                                           URIRef(rec_type.uri)))
                            # reset identifier to BNode
                            identifier = bnode
                            if value:
                                container.add((identifier, attr2rdf(attr), obj))
                        elif value:
                            pred = attr2rdf(attr)
                            container.add((identifier, pred,
                                           self.encode_rdf_representation(value)))
                        continue
                    if value is None:
                        continue
                    pred = attr2rdf(attr)
                    if isinstance(value, ProvRecord):
                        obj = URIRef(unicode(real_or_anon_id(value)))
                    else:
                        #  Assuming this is a datetime value
                        obj = self.encode_rdf_representation(value)
                    container.add((identifier, pred, obj))
            if record._extra_attributes:
                for (attr, value) in record._extra_attributes:
                    obj = self.encode_rdf_representation(value)
                    if attr == PROV['location']:
                        pred = URIRef(PROV['atLocation'].uri)
                        if isinstance(value, (URIRef, QName)):
                            if isinstance(value, QName):
                                value = URIRef(value.uri)
                            container.add((identifier, pred, value))
                            container.add((value, RDF.type,
                                           URIRef(PROV['Location'].uri)))
                        else:
                            container.add((identifier, pred, obj))
                        continue
                    if attr == PROV['type']:
                        pred = RDF.type
                    elif attr == PROV['label']:
                        pred = RDFS.label
                    else:
                        pred = self.encode_rdf_representation(attr)
                    container.add((identifier, pred, obj))
        return container

    def decode_document(self, content, document):
        bundles = dict()
        if u'bundle' in content:
            bundles = content[u'bundle']
            del content[u'bundle']

        self.decode_container(content, document)

        for bundle_id, bundle_content in bundles.items():
            bundle = document.bundle(bundle_id)
            self.decode_container(bundle_content, bundle)

    def decode_container(self, jc, bundle):
        if u'prefix' in jc:
            prefixes = jc[u'prefix']
            for prefix, uri in prefixes.items():
                if prefix != 'default':
                    bundle.add_namespace(Namespace(prefix, uri))
                else:
                    bundle.set_default_namespace(uri)
            del jc[u'prefix']

        for rec_type_str in jc:
            rec_type = PROV_RECORD_IDS_MAP[rec_type_str]
            for rec_id, content in jc[rec_type_str].items():
                if rec_type == PROV_BUNDLE:
                    raise ProvRDFException('A bundle cannot have nested bundles')
                else:
                    if hasattr(content, 'items'):  # it is a dict
                        #  There is only one element, create a singleton list
                        elements = [content]
                    else:
                        # expect it to be a list of dictionaries
                        elements = content

                    for element in elements:
                        prov_attributes = {}
                        extra_attributes = []
                        #  Splitting PROV attributes and the others
                        membership_extra_members = None  # this is for the multiple-entity membership hack to come
                        for attr, value in element.items():
                            if attr in PROV_ATTRIBUTES_ID_MAP:
                                attr_id = PROV_ATTRIBUTES_ID_MAP[attr]
                                if isinstance(value, list):
                                    # Multiple values
                                    if len(value) == 1:
                                        # Only a single value in the list, unpack it
                                        value = value[0]
                                    else:
                                        if rec_type == PROV_MEMBERSHIP and attr_id == PROV_ATTR_ENTITY:
                                            # This is a membership relation with multiple entities
                                            # HACK: create multiple membership relations, one for each entity
                                            membership_extra_members = value[1:]  # Store all the extra entities
                                            value = value[0]  # Create the first membership relation as normal for the first entity
                                        else:
                                            error_msg = 'The prov package does not support PROV attributes having multiple values.'
                                            logger.error(error_msg)
                                            raise ProvRDFException(error_msg)
                                prov_attributes[attr_id] =\
                                    self.valid_identifier(value) if attr_id not in PROV_ATTRIBUTE_LITERALS else \
                                    self.decode_rdf_representation(value)
                            else:
                                attr_id = self.valid_identifier(attr)
                                if isinstance(value, list):
                                    #  Parsing multi-value attribute
                                    extra_attributes.extend(
                                        (attr_id, self.decode_rdf_representation(value_single))
                                        for value_single in value
                                    )
                                else:
                                    #  add the single-value attribute
                                    extra_attributes.append((attr_id, self.decode_rdf_representation(value)))
                        bundle.add_record(rec_type, rec_id, prov_attributes, extra_attributes)
                        # HACK: creating extra (unidentified) membership relations
                        if membership_extra_members:
                            collection = prov_attributes[PROV_ATTR_COLLECTION]
                            for member in membership_extra_members:
                                bundle.membership(collection, self.valid_identifier(member))


def literal_rdf_representation(literal):
    if literal.get_langtag():
        #  a language tag can only go with prov:InternationalizedString
        return RDFLiteral(unicode(literal.get_value()),
                          lang=str(literal.get_langtag()))
    else:
        datatype = literal.get_datatype()
        if isinstance(datatype, QName):
            return RDFLiteral(unicode(literal.get_value()),
                              datatype=unicode(datatype))
        else:
            #  Assuming it is a valid identifier
            return RDFLiteral(unicode(literal.get_value()),
                              datatype=datatype.uri)
