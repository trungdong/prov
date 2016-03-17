"""PROV-RDF serializers for ProvDocument
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

__author__ = 'Satrajit S. Ghosh'
__email__ = 'satra@mit.edu'

import logging
logger = logging.getLogger('rdf')

from collections import defaultdict
import datetime
import io

from prov.serializers import Serializer, Error
from prov.constants import *
from prov.model import (Literal, Identifier, QualifiedName,
                        Namespace, ProvDocument, ProvBundle, first,
                        parse_xsd_datetime, ProvRecord)

import base64
import datetime
import dateutil.parser
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
    int: XSD['int'],
    unicode: XSD['string'],
    # boolean, string values are supported natively by PROV-RDF
    # datetime values are converted separately
}

# Add long on Python 2
if six.integer_types[-1] not in LITERAL_XSDTYPE_MAP:
    LITERAL_XSDTYPE_MAP[six.integer_types[-1]] = 'xsd:long'


def valid_qualified_name(bundle, value, xsd_qname=False):
    if value is None:
        return None
    qualified_name = bundle.valid_qualified_name(value)
    return qualified_name if not xsd_qname else XSDQName(qualified_name)


class ProvRDFSerializer(Serializer):
    """
    PROV-O serializer for :class:`~prov.model.ProvDocument`
    """

    def serialize(self, stream=None, **kwargs):
        """
        Serializes a :class:`~prov.model.ProvDocument` instance to
        `Prov-O <https://www.w3.org/TR/prov-o/>`_.

        :param stream: Where to save the output.
        """
        container = self.encode_document(self.document)
        newargs = kwargs.copy()
        if newargs and 'rdf_format' in newargs:
            newargs['format'] = newargs['rdf_format']
            del newargs['rdf_format']
        if six.PY2:
            buf = io.BytesIO()
            try:
                container.serialize(buf, **newargs)
                buf.seek(0, 0)
                # Right now this is a bytestream. If the object to stream to is
                # a text object is must be decoded. We assume utf-8 here which
                # should be fine for almost every case.
                if isinstance(stream, io.TextIOBase):
                    stream.write(buf.read().decode('utf-8'))
                else:
                    stream.write(buf.read())
            finally:
                buf.close()
        else:
            buf = io.StringIO()
            try:
                container.serialize(buf, **newargs)
                buf.seek(0, 0)
                # Right now this is a bytestream. If the object to stream to is
                # a text object is must be decoded. We assume utf-8 here which
                # should be fine for almost every case.
                if isinstance(stream, io.TextIOBase):
                    stream.write(buf.read())
                else:
                    stream.write(buf.read().encode('utf-8'))
            finally:
                buf.close()

    def deserialize(self, stream, **kwargs):
        """
        Deserialize from the `Prov-O <https://www.w3.org/TR/prov-o/>`_
        representation to a :class:`~prov.model.ProvDocument` instance.

        :param stream: Input data.
        """
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
        #logger.debug((value, type(value))) #dbg
        if isinstance(value, URIRef):
            return value
        elif isinstance(value, Literal):
            return literal_rdf_representation(value)
        elif isinstance(value, datetime.datetime):
            return RDFLiteral(value.isoformat(), datatype=XSD['dateTime'])
        elif isinstance(value, QualifiedName):
            #if value.namespace == PROV:
                return URIRef(value.uri) #, datatype=XSD['QName'])
            #else:
            #    return RDFLiteral(value, datatype=XSD['QName'])
        #elif isinstance(value, XSDQName):
        #    return RDFLiteral(value, datatype=XSD['QName'])
        elif isinstance(value, Identifier):
            return RDFLiteral(value.uri, datatype=XSD['anyURI'])
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
        if isinstance(literal, RDFLiteral):
            value = literal.value if literal.value is not None else literal
            datatype = literal.datatype if hasattr(literal, 'datatype') else None
            langtag = literal.language if hasattr(literal, 'language') else None
            if datatype and 'XMLLiteral' in datatype:
                value = literal
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
                return pm.Literal(literal, datatype=XSD_QNAME)
                '''
                for ns in self.document.namespaces:
                    if literal.startswith(ns.prefix):
                        return pm.Literal(literal, datatype=XSD_QNAME)
                        #return pm.QualifiedName(ns,
                        #                        literal.replace(ns.prefix + ':',
                        #                                        ''))
                raise Exception('No namespace found for: %s' % literal)
                '''
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
                printed = False
                all_attributes = list(record.formal_attributes) + list(record.attributes)
                formal_qualifiers = False
                for attrid, (attr, value) in enumerate(list(record.formal_attributes)): #[1:]:
                    logger.debug((identifier, attrid, attr, value, formal_qualifiers))
                    if (identifier is not None and value is not None) or \
                            (identifier is None and value is not None and attrid > 1):
                        formal_qualifiers = True
                has_qualifiers = len(record.extra_attributes) > 0 or formal_qualifiers
                #print all_attributes
                #print record, rec_type.uri
                #print "attr", record.attributes
                #all_attributes = set(record.formal_attributes).union(set(record.attributes))
                for idx, (attr, value) in enumerate(all_attributes):
                    logger.debug((identifier, idx, attr, value))
                    if record.is_relation():
                        if not printed:
                            #print "attr", record.extra_attributes
                            printed = True
                        pred = URIRef(PROV[PROV_N_MAP[rec_type]].uri)
                        # create bnode relation
                        if bnode is None:
                            #print(record.formal_attributes)
                            for key, val in record.formal_attributes:
                                formal_objects.append(key)
                            used_objects = [record.formal_attributes[0][0]]
                            subj = None
                            if record.formal_attributes[0][1]:
                                subj = URIRef(record.formal_attributes[0][1].uri)
                            #print("SUBJ:  ", subj, identifier, has_qualifiers)
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
                            if subj and has_qualifiers:
                                qualifier = rec_type._localpart
                                rec_uri = rec_type.uri
                                for attr_name, val in record.extra_attributes:
                                    if attr_name == PROV['type']:
                                        #logger.debug(("qualifier", val))
                                        if PROV['Revision'] == val or PROV['Quotation'] == val:
                                            qualifier = val._localpart
                                            rec_uri = val.uri
                                QRole = URIRef(PROV['qualified' + qualifier].uri)
                                if identifier is not None:
                                    container.add((subj, QRole, identifier))
                                else:
                                    bnode = identifier = BNode()
                                    container.add((subj, QRole, identifier))
                                    container.add((identifier, RDF.type,
                                                   URIRef(rec_uri)))
                                               # reset identifier to BNode
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
                            #logger.debug(('attr', attr)) #dbg
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
                            if PROV['informant'].uri in pred:
                                pred = URIRef(PROV['activity'].uri)
                            if PROV['responsible'].uri in pred:
                                pred = URIRef(PROV['agent'].uri)
                            if rec_type == PROV_DELEGATION and PROV['activity'].uri in pred:
                                pred = URIRef(PROV['hadActivity'].uri)
                            #logger.debug(('Q:', identifier, pred, value))
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
                    #print type(value), type(obj)
                    if attr == PROV['location']:
                        pred = URIRef(PROV['atLocation'].uri)
                        if False and isinstance(value, (URIRef, QualifiedName)):
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
                    logger.debug((identifier, pred, obj))
                    '''
                    gtemp = ConjunctiveGraph()
                    gtemp.add((identifier, pred, obj))
                    print(gtemp.serialize(format='turtle'))
                    '''
                    container.add((identifier, pred, obj))
        return container

    def decode_document(self, content, document):
        for prefix, url in content.namespaces():
            #if prefix in ['rdf', 'rdfs', 'xml']:
            #    continue
            document.add_namespace(prefix, unicode(url))
        for bundle_stmt in content.triples((None, RDF.type,
                                            URIRef(pm.PROV['bundle'].uri))):
            bundle_id = unicode(bundle_stmt[0])
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
        formal_attributes = {}
        for key, val in PROV_N_MAP.items():
            PROV_CLS_MAP[key.uri] = val
        for key, val in ADDITIONAL_N_MAP.items():
            PROV_CLS_MAP[key.uri] = val
        other_attributes = {}
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
                except AttributeError, e:
                    prov_obj = None
                if id not in ids and prov_obj:
                    ids[id] = prov_obj
--------->                    formal_attributes[id] = prov_obj.FORMAL_ATTRIBUTES
                else:
                    if id not in other_attributes:
                        other_attributes[id] = []
                    other_attributes[id].append((pm.PROV['type'], obj))
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
            #logger.debug((id, pred, obj)) #dbg
            id = unicode(id)
            if id not in other_attributes:
                other_attributes[id] = []
            if pred == RDF.type:
                continue
            if pred == URIRef(PROV['alternateOf'].uri):
                bundle.alternate(id, unicode(obj))
            elif pred == URIRef(PROV['wasAssociatedWith'].uri):
                bundle.association(id, unicode(obj))
            elif id in ids:
                #logger.debug((id, pred, obj)) #dbg
                obj1 = self.decode_rdf_representation(obj)
                #logger.debug(('decoded:', id, pred, obj1)) #dbg
                if pred == RDFS.label:
                    if hasattr(ids[id], '__call__'):
                        other_attributes[id].append((pm.PROV['label'], obj1))
                    else:
                        ids[id].add_attributes([(pm.PROV['label'], obj1)])
                elif pred == URIRef(PROV['atLocation'].uri):
                    ids[id].add_attributes([(pm.PROV['location'], obj1)])
                else:
                    if 'hadRole' in pred:
                        pred = PROV_ROLE
                    if 'hadPlan' in pred:
                        pred = pm.PROV_ATTR_PLAN
                    if 'hadActivity' in pred:
                        pred = pm.PROV_ATTR_ACTIVITY
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
                                other_attributes[id].append((pred, obj1))
                        elif ids[id].__name__ == 'attribution':
                            if 'agent' in unicode(pred):
                                if id not in formal_attributes:
                                    formal_attributes[id] = {'agent': obj1}
                                else:
                                    associd = bundle.attribution(formal_attributes[id]['entity'],
                                                      obj1, identifier=unicode(id))
                                    ids[id] = associd
                                    if other_attributes[id]:
                                        associd.add_attributes(other_attributes[id])
                                        other_attributes[id] = []
                            else:
                                other_attributes[id].append((pred, obj1))
                        elif ids[id].__name__ == 'communication':
                            if 'activity' in unicode(pred):
                                if id not in formal_attributes:
                                    formal_attributes[id] = {'informant': obj1}
                                else:
                                    commid = bundle.communication(formal_attributes[id]['informed'],
                                                                   obj1, identifier=unicode(id))
                                    ids[id] = commid
                                    if other_attributes[id]:
                                        commid.add_attributes(other_attributes[id])
                                        other_attributes[id] = []
                            else:
                                other_attributes[id].append((pred, obj1))
                    else:
                        ids[id].add_attributes([(unicode(pred), obj1)])
            local_key = unicode(obj)
            if local_key in ids:
                #print obj #dbg
                if pred == URIRef(PROV['qualifiedAssociation'].uri):
                    if hasattr(ids[local_key], '__call__'):
                        aid = ids[local_key](id, identifier=local_key)
                        if other_attributes[id]:
                            aid.add_attributes(other_attributes[id])
                            other_attributes[id] = []
                        ids[local_key] = aid
                    else:
                        ids[local_key].add_attributes([(pm.PROV_ATTR_ACTIVITY,
                                                           id)])
                if pred == URIRef(PROV['qualifiedAttribution'].uri):
                    if local_key not in formal_attributes:
                        formal_attributes[local_key] = {'entity': id}
                    else:
                        associd = bundle.attribution(id,
                                                 formal_attributes[local_key]['agent'],
                                                 identifier=local_key)
                        ids[local_key] = associd
                        if other_attributes[local_key]:
                            associd.add_attributes(other_attributes[local_key])
                            other_attributes[local_key] = []
                if pred == URIRef(PROV['qualifiedCommunication'].uri):
                    if local_key not in formal_attributes:
                        formal_attributes[local_key] = {'informed': id}
                    else:
                        commid = bundle.communication(id,
                                                 formal_attributes[local_key]['informant'],
                                                 identifier=local_key)
                        ids[local_key] = commid
                        if other_attributes[local_key]:
                            commid.add_attributes(other_attributes[local_key])
                            other_attributes[local_key] = []

            #print other_attributes #dbg
        for key, val in other_attributes.items():
            if val:
                ids[key].add_attributes(val)


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
