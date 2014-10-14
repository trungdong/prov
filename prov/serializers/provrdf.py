"""PROV-RDF serializers for ProvDocument

@author: Satrajit Ghosh <satra@mit.edu>
@copyright: University of Southampton 2014
"""
import logging
logger = logging.getLogger(__name__)

import base64
import datetime
import dateutil.parser
from prov import Serializer, Error
from prov.constants import *
from prov.model import (Literal, Identifier, QualifiedName, Namespace,
                        ProvRecord, ProvDocument, XSDQName)
import prov.model as pm

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

def valid_qualified_name(bundle, value, xsd_qname=False):
    if value is None:
        return None
    qualified_name = bundle.valid_qualified_name(value)
    return qualified_name if not xsd_qname else XSDQName(qualified_name)


class ProvRDFSerializer(Serializer):
    def serialize(self, stream=None, **kwargs):
        container = self.encode_document(self.document)
        newargs = kwargs.copy()
        if newargs and 'rdf_format' in newargs:
            newargs['format'] = newargs['rdf_format']
            del newargs['rdf_format']
        container.serialize(stream, **newargs)

    def deserialize(self, stream, **kwargs):
        newargs = kwargs.copy()
        if newargs and 'rdf_format' in newargs:
            newargs['format'] = newargs['rdf_format']
            del newargs['rdf_format']
        container = ConjunctiveGraph().parse(stream, **newargs)
        document = ProvDocument()
        self.document = document
        self.decode_document(container, document)
        return document

    def valid_identifier(self, value):
        return self.document.valid_qualified_name(value)

    def encode_rdf_representation(self, value):
        #print value, type(value) #dbg
        if isinstance(value, URIRef):
            return value
        elif isinstance(value, Literal):
            return literal_rdf_representation(value)
        elif isinstance(value, datetime.datetime):
            return RDFLiteral(value.isoformat(), datatype=XSD['dateTime'])
        elif isinstance(value, QualifiedName):
            return URIRef(value.uri) #, datatype=XSD['QName'])
        elif isinstance(value, XSDQName):
            return URIRef(value.uri) #, datatype=XSD['QName'])
        elif isinstance(value, Identifier):
            return URIRef(value.uri)
        elif type(value) in LITERAL_XSDTYPE_MAP:
            return RDFLiteral(value, datatype=LITERAL_XSDTYPE_MAP[type(value)])
        else:
            return RDFLiteral(value)

    """
    def decode_rdf_representation(self, literal):
        if isinstance(literal, RDFLiteral):
            # complex type
            value = literal.value if literal.value is not None else literal
            datatype = literal.datatype if hasattr(literal, 'datatype') else None
            langtag = literal.language if hasattr(literal, 'language') else None
            datatype = valid_qualified_name(self.document, datatype)
            if datatype == XSD_ANYURI:
                return Identifier(value)
            elif datatype == XSD_QNAME:
                return valid_qualified_name(self.document, value, xsd_qname=True)
            elif datatype == PROV_QUALIFIEDNAME:
                return valid_qualified_name(self.document, value)
            else:
                # The literal of standard Python types is not converted here
                # It will be automatically converted when added to a record by _auto_literal_conversion()
                return Literal(value, datatype, langtag)
        elif isinstance(literal, URIRef):
            val = unicode(literal)
            return Identifier(val)
        else:
            # simple type, just return it
            return literal

    """
    def decode_rdf_representation(self, literal):
        #print(('Decode', literal))
        if isinstance(literal, RDFLiteral):
            value = literal.value if literal.value is not None else literal
            datatype = literal.datatype if hasattr(literal, 'datatype') else None
            langtag = literal.language if hasattr(literal, 'language') else None
            if datatype and 'base64Binary' in datatype:
                value = base64.standard_b64encode(value)
            #print((value, datatype, langtag)) #dbg
            '''
            if datatype == XSD['anyURI']:
                return Identifier(value)
            elif datatype == PROV['QualifiedName']:
                return self.valid_identifier(value)
            '''
            if datatype == XSD['QName']:
                for ns in self.document.namespaces:
                    if literal.startswith(ns.prefix):
                        return pm.XSDQName(QualifiedName(ns,
                                                         literal.replace(ns.prefix + ':',
                                                                         '')))
                raise Exception('No namespace found for: %s' % literal)
            if datatype == XSD['dateTime']:
                return dateutil.parser.parse(literal)
            else:
                # The literal of standard Python types is not converted here
                # It will be automatically converted when added to a record by _auto_literal_conversion()
                return Literal(value, self.valid_identifier(datatype), langtag)
        elif isinstance(literal, URIRef):
            val = unicode(literal)
            return Identifier(val)
        else:
            # simple type, just return it
            return literal

    def encode_document(self, document):
        container = self.encode_container(document)
        for b_id, b in document._bundles.items():
            #  encoding the sub-bundle
            bundle = self.encode_container(b, identifier=b_id.uri)
            container.addN(bundle.quads())
        return container

    def encode_container(self, bundle, container=None, identifier=None):
        if container is None:
            container = ConjunctiveGraph(identifier=identifier)
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
            if hasattr(record, 'identifier') and record.identifier: #record.is_relation():
                identifier = URIRef(unicode(real_or_anon_id(record)))
                container.add((identifier, RDF.type, URIRef(rec_type.uri)))
            else:
                identifier = None
            if record.attributes:
                bnode = None
                formal_objects = []
                used_objects = []
                all_attributes = set(record.formal_attributes).union(set(record.attributes))
                for idx, (attr, value) in enumerate(all_attributes):
                    #print identifier, idx, attr, value
                    #print record, rec_type.uri
                    if record.is_relation():
                        pred = URIRef(PROV[PROV_N_MAP[rec_type]].uri)
                        # create bnode relation
                        if bnode is None:
                            for key, val in record.formal_attributes:
                                formal_objects.append(key)
                            used_objects = [record.formal_attributes[0][0]]
                            subj = None
                            if record.formal_attributes[0][1]:
                                subj = URIRef(record.formal_attributes[0][1].uri)
                            if identifier is None and subj is not None:
                                try:
                                    obj_val = record.formal_attributes[1][1]
                                    obj_attr = URIRef(record.formal_attributes[1][0].uri)
                                except IndexError:
                                    obj_val = None
                                if obj_val:
                                    used_objects.append(record.formal_attributes[1][0])
                                    obj_val = self.encode_rdf_representation(obj_val)
                                    container.add((subj, pred, obj_val))
                                #print identifier, pred, obj_val
                            if rec_type in [PROV_ALTERNATE]: #, PROV_ASSOCIATION]:
                                continue
                            if subj and identifier:
                                QRole = URIRef(PROV['qualified' +
                                                    rec_type._localpart].uri)
                                container.add((subj, QRole, identifier))

                            '''
                            for key, val in record.formal_attributes:
                                formal_objects.append(key)
                            used_objects = [record.formal_attributes[0][0]]
                            if record.formal_attributes[0][1]:
                                identifier = URIRef(record.formal_attributes[0][1].uri)
                                try:
                                    obj_val = record.formal_attributes[1][1]
                                    obj_attr = URIRef(record.formal_attributes[1][0].uri)
                                except IndexError:
                                    obj_val = None
                                if obj_val:
                                    used_objects.append(record.formal_attributes[1][0])
                                    obj_val = self.encode_rdf_representation(obj_val)
                                    container.add((identifier, pred, obj_val))
                                print identifier, pred, obj_val
                                if rec_type in [PROV_ALTERNATE]: #, PROV_ASSOCIATION]:
                                    continue
                                QRole = URIRef(PROV['qualified' +
                                                    rec_type._localpart].uri)
                                if hasattr(record, 'identifier') and record.identifier:
                                    bnode = URIRef(record.identifier.uri)
                                else:
                                    bnode = BNode()
                                container.add((identifier, QRole, bnode))
                                container.add((bnode, RDF.type,
                                               URIRef(rec_type.uri)))
                                # reset identifier to BNode
                                identifier = bnode
                                print identifier, obj_attr, obj_val #dbg
                                if obj_val:
                                    container.add((identifier, obj_attr, obj_val))
                            '''
                        if value is not None and attr not in used_objects:
                            #print 'attr', attr #dbg
                            if attr in formal_objects:
                                pred = attr2rdf(attr)
                            elif attr == PROV['role']:
                                pred = URIRef(PROV['hadRole'].uri)
                            elif attr == PROV['plan']:
                                pred = URIRef(PROV['hadPlan'].uri)
                            elif attr == PROV['type']:
                                pred = RDF.type
                            elif attr == PROV['label']:
                                pred = RDFS.label
                            elif isinstance(attr, QualifiedName):
                                pred = URIRef(attr.uri)
                            else:
                                pred = self.encode_rdf_representation(attr)
                            if PROV['plan'].uri in pred:
                                pred = URIRef(PROV['hadPlan'].uri)
                            #print pred #dbg
                            container.add((identifier, pred,
                                           self.encode_rdf_representation(value)))
                        continue
                    if value is None:
                        continue
                    if isinstance(value, ProvRecord):
                        obj = URIRef(unicode(real_or_anon_id(value)))
                    else:
                        #  Assuming this is a datetime value
                        obj = self.encode_rdf_representation(value)
                    if attr == PROV['location']:
                        pred = URIRef(PROV['atLocation'].uri)
                        if isinstance(value, (URIRef, QualifiedName)):
                            if isinstance(value, QualifiedName):
                                #value = RDFLiteral(unicode(value), datatype=XSD['QName'])
                                value = URIRef(value.uri)
                            container.add((identifier, pred, value))
                            #container.add((value, RDF.type,
                            #               URIRef(PROV['Location'].uri)))
                        else:
                            container.add((identifier, pred,
                                           self.encode_rdf_representation(obj)))
                        continue
                    #pred = attr2rdf(attr)
                    if attr == PROV['type']:
                        pred = RDF.type
                    elif attr == PROV['label']:
                        pred = RDFS.label
                    else:
                        pred = self.encode_rdf_representation(attr)
                    container.add((identifier, pred, obj))
        return container

    def decode_document(self, content, document):
        for prefix, url in content.namespaces():
            #if prefix in ['rdf', 'rdfs', 'xml']:
            #    continue
            document.add_namespace(prefix, unicode(url))
        if hasattr(content, 'contexts'):
            for graph in content.contexts():
                bundle_id = unicode(graph.identifier)
                bundle = document.bundle(bundle_id)
                self.decode_container(graph, bundle)
        else:
            self.decode_container(content, document)

    def decode_container(self, graph, bundle):
        ids = {}
        PROV_CLS_MAP = {}
        for key, val in PROV_N_MAP.items():
            PROV_CLS_MAP[key.uri] = val
        for key, val in ADDITIONAL_N_MAP.items():
            PROV_CLS_MAP[key.uri] = val
        for stmt in graph.triples((None, RDF.type, None)):
            id = unicode(stmt[0])
            obj = unicode(stmt[2])
            #print obj, type(obj), obj in PROV_CLS_MAP #dbg
            if obj in PROV_CLS_MAP:
                #print 'obj_found' #dbg
                try:
                    prov_obj = getattr(bundle, PROV_CLS_MAP[obj])(identifier=id)
                except TypeError, e:
                    #print e
                    prov_obj = getattr(bundle, PROV_CLS_MAP[obj])
                if id not in ids:
                    ids[id] = prov_obj
                else:
                    raise ValueError(('An object cannot be of two different '
                                     'PROV types'))
        other_attributes = {}
        for stmt in graph.triples((None, RDF.type, None)):
            id = unicode(stmt[0])
            if id not in other_attributes:
                other_attributes[id] = []
            obj = unicode(stmt[2]) #unicode(stmt[2]).replace('http://www.w3.org/ns/prov#', '').lower()
            if obj in PROV_CLS_MAP:
                continue
            elif id in ids:
                obj = self.decode_rdf_representation(stmt[2])
                if hasattr(ids[id], '__call__'):
                    other_attributes[id].append((pm.PROV['type'], obj))
                else:
                    ids[id].add_attributes([(pm.PROV['type'], obj)])
        for id, pred, obj in graph:
            #print((id, pred, obj)) #dbg
            id = unicode(id)
            if id not in other_attributes:
                other_attributes[id] = []
            if pred == RDF.type:
                continue
            elif pred == URIRef(PROV['alternateOf'].uri):
                bundle.alternate(id, unicode(obj))
            elif pred == URIRef(PROV['wasAssociatedWith'].uri):
                bundle.association(id, unicode(obj))
            elif id in ids:
                #print((id, pred, obj)) #dbg
                obj1 = self.decode_rdf_representation(obj)
                if pred == RDFS.label:
                    if hasattr(ids[id], '__call__'):
                        other_attributes[id].append((pm.PROV['label'], obj1))
                    else:
                        ids[id].add_attributes([(pm.PROV['label'], obj1)])
                elif pred == URIRef(PROV['atLocation'].uri):
                    ids[id].add_attributes([(pm.PROV['location'], obj1)])
                else:
                    if hasattr(ids[id], '__call__'):
                        if ids[id].__name__ == 'association':
                            if 'agent' in unicode(pred):
                                aid = ids[id](None, agent=obj1,
                                              identifier=unicode(id))
                                ids[id] = aid
                                if other_attributes[id]:
                                    aid.add_attributes(other_attributes[id])
                                    other_attributes[id] = []
                            else:
                                if 'hadPlan' in pred:
                                    pred = pm.PROV_ATTR_PLAN
                                elif 'hadRole' in pred:
                                    pred = PROV_ROLE
                                other_attributes[id].append((pred, obj1))
                    else:
                        if 'hadPlan' in pred:
                            ids[id].add_attributes([(pm.PROV_ATTR_PLAN, obj1)])
                        elif 'hadRole' in pred:
                            ids[id].add_attributes([(PROV_ROLE,
                                                     obj1)])
                        else:
                            ids[id].add_attributes([(unicode(pred), obj1)])
            if unicode(obj) in ids:
                #print obj #dbg
                if pred == URIRef(PROV['qualifiedAssociation'].uri):
                    if hasattr(ids[unicode(obj)], '__call__'):
                        aid = ids[unicode(obj)](id, identifier=unicode(obj))
                        if other_attributes[id]:
                            aid.add_attributes(other_attributes[id])
                            other_attributes[id] = []
                        ids[unicode(obj)] = aid
                    else:
                        ids[unicode(obj)].add_attributes([(pm.PROV_ATTR_ACTIVITY,
                                                           id)])
            #print other_attributes #dbg
        for key, val in other_attributes.items():
            if val:
                ids[key].add_attributes(val)

        '''
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
        '''

def literal_rdf_representation(literal):
    value = unicode(literal.value) if literal.value else literal
    if literal.langtag:
        #  a language tag can only go with prov:InternationalizedString
        return RDFLiteral(value, lang=str(literal.langtag))
    else:
        datatype = literal.datatype
        '''
        if isinstance(datatype, QualifiedName):
            print 'QName', datatype, datatype.uri
            return RDFLiteral(unicode(literal.value),
                              datatype=unicode(datatype))
        else:
            #  Assuming it is a valid identifier
            print 'URI', datatype
        '''
        if 'base64Binary' in datatype.uri:
            value = base64.standard_b64encode(value)
        return RDFLiteral(value, datatype=datatype.uri)
