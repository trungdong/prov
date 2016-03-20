"""PROV-RDF serializers for ProvDocument
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

__author__ = 'Satrajit S. Ghosh'
__email__ = 'satra@mit.edu'

import logging
logger = logging.getLogger('rdf')

from collections import defaultdict, OrderedDict
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

    def serialize(self, stream=None, rdf_format='trig', **kwargs):
        """
        Serializes a :class:`~prov.model.ProvDocument` instance to
        `Prov-O <https://www.w3.org/TR/prov-o/>`_.

        :param stream: Where to save the output.
        """
        container = self.encode_document(self.document)
        newargs = kwargs.copy()
        newargs['format'] = rdf_format

        if newargs['format'] == 'trig':
            gr = ConjunctiveGraph()
            gr.context_aware = True
            gr.parse(data=container.serialize(format='nquads'), format='nquads')
            for namespace in container.namespaces():
                if namespace not in list(gr.namespaces()):
                    gr.bind(namespace[0], namespace[1])
            container = gr

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

    def deserialize(self, stream, rdf_format='trig', **kwargs):
        """
        Deserialize from the `Prov-O <https://www.w3.org/TR/prov-o/>`_
        representation to a :class:`~prov.model.ProvDocument` instance.

        :param stream: Input data.
        """
        newargs = kwargs.copy()
        newargs['format'] = rdf_format
        logger.debug('starting parsing')
        container = ConjunctiveGraph()
        container.parse(stream, **newargs)
        logger.debug('parsed stream')
        document = ProvDocument()
        self.document = document
        self.decode_document(container, document)
        return document

    def valid_identifier(self, value):
        return self.document.valid_qualified_name(value)

    def encode_rdf_representation(self, value):
        if isinstance(value, URIRef):
            return value
        elif isinstance(value, Literal):
            return literal_rdf_representation(value)
        elif isinstance(value, datetime.datetime):
            return RDFLiteral(value.isoformat(), datatype=XSD['dateTime'])
        elif isinstance(value, QualifiedName):
            return URIRef(value.uri)
        elif isinstance(value, Identifier):
            return RDFLiteral(value.uri, datatype=XSD['anyURI'])
        elif type(value) in LITERAL_XSDTYPE_MAP:
            return RDFLiteral(value, datatype=LITERAL_XSDTYPE_MAP[type(value)])
        else:
            return RDFLiteral(value)

    def decode_rdf_representation(self, literal):
        if isinstance(literal, RDFLiteral):
            value = literal.value if literal.value is not None else literal
            datatype = literal.datatype if hasattr(literal, 'datatype') else None
            langtag = literal.language if hasattr(literal, 'language') else None
            if datatype and 'XMLLiteral' in datatype:
                value = literal
            if datatype and 'base64Binary' in datatype:
                value = base64.standard_b64encode(value)
            if datatype == XSD['QName']:
                return pm.Literal(literal, datatype=XSD_QNAME)
            if datatype == XSD['dateTime']:
                return dateutil.parser.parse(literal)
            else:
                # The literal of standard Python types is not converted here
                # It will be automatically converted when added to a record by _auto_literal_conversion()
                return Literal(value, self.valid_identifier(datatype), langtag)
        elif isinstance(literal, URIRef):
            return self.valid_identifier(literal)
        else:
            # simple type, just return it
            return literal

    def encode_document(self, document):
        container = self.encode_container(document)
        for item in document.bundles:
            #  encoding the sub-bundle
            bundle = self.encode_container(item, identifier=item.identifier.uri)
            container.addN(bundle.quads())
        return container

    def encode_container(self, bundle, container=None, identifier=None):
        if container is None:
            container = ConjunctiveGraph(identifier=identifier)
            nm = container.namespace_manager
            nm.bind('prov', PROV.uri)

        for namespace in bundle.namespaces:
            container.bind(namespace.prefix, namespace.uri)

        id_generator = AnonymousIDGenerator()
        real_or_anon_id = lambda record: record._identifier.uri if \
            record._identifier else id_generator.get_anon_id(record)

        for record in bundle._records:
            rec_type = record.get_type()
            if hasattr(record, 'identifier') and record.identifier:
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
                for attrid, (attr, value) in enumerate(list(record.formal_attributes)):
                    if (identifier is not None and value is not None) or \
                            (identifier is None and value is not None and attrid > 1):
                        formal_qualifiers = True
                has_qualifiers = len(record.extra_attributes) > 0 or formal_qualifiers
                for idx, (attr, value) in enumerate(all_attributes):
                    if record.is_relation():
                        if not printed:
                            printed = True
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
                                    obj_attr = URIRef(record.formal_attributes[1][0].uri)
                                except IndexError:
                                    obj_val = None
                                if obj_val and (rec_type not in [PROV_END,
                                                                PROV_START,
                                                                PROV_USAGE,
                                                                PROV_GENERATION,
                                                                PROV_DERIVATION,
                                                                PROV_INVALIDATION] or
                                                (valid_formal_indices == {0, 1} and
                                                 len(record.extra_attributes) == 0)):
                                    used_objects.append(record.formal_attributes[1][0])
                                    obj_val = self.encode_rdf_representation(obj_val)
                                    container.add((subj, pred, obj_val))
                                    if rec_type == PROV_MENTION:
                                        if record.formal_attributes[2][1]:
                                            used_objects.append(record.formal_attributes[2][0])
                                            obj_val = self.encode_rdf_representation(record.formal_attributes[2][1])
                                            container.add((subj, URIRef(PROV['asInBundle'].uri), obj_val))
                                        has_qualifiers = False
                            if rec_type in [PROV_ALTERNATE]: #, PROV_ASSOCIATION]:
                                continue
                            if subj and (has_qualifiers or identifier):  #and (len(record.extra_attributes) > 0 or                                                            identifier):
                                qualifier = rec_type._localpart
                                rec_uri = rec_type.uri
                                for attr_name, val in record.extra_attributes:
                                    if attr_name == PROV['type']:
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
                        if value is not None and attr not in used_objects:
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
                            if (rec_type in [PROV_END, PROV_START] and PROV['trigger'].uri in pred) or\
                                (rec_type in [PROV_USAGE] and PROV['used'].uri in pred):
                                pred = URIRef(PROV['entity'].uri)
                            if rec_type == PROV_DERIVATION:
                                if PROV['activity'].uri in pred:
                                    pred = URIRef(PROV['hadActivity'].uri)
                                if PROV['generation'].uri in pred:
                                    pred = URIRef(PROV['hadGeneration'].uri)
                                if PROV['usage'].uri in pred:
                                    pred = URIRef(PROV['hadUsage'].uri)
                                if PROV['usedEntity'].uri in pred:
                                    pred = URIRef(PROV['entity'].uri)
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
                    container.add((identifier, pred, obj))
        return container

    def decode_document(self, content, document):
        for prefix, url in content.namespaces():
            document.add_namespace(prefix, unicode(url))
        if hasattr(content, 'contexts'):
            for graph in content.contexts():
                if isinstance(graph.identifier, BNode):
                    self.decode_container(graph, document)
                else:
                    bundle_id = unicode(graph.identifier)
                    bundle = document.bundle(bundle_id)
                    self.decode_container(graph, bundle)
        else:
            self.decode_container(content, document)

    def decode_container(self, graph, bundle):
        ids = {}
        PROV_CLS_MAP = {}
        formal_attributes = {}
        unique_sets = {}
        for key, val in PROV_BASE_CLS.items():
            PROV_CLS_MAP[key.uri] = PROV_BASE_CLS[key]
        relation_mapper = {URIRef(PROV['alternateOf'].uri): 'alternate',
                           URIRef(PROV['actedOnBehalfOf'].uri): 'delegation',
                           URIRef(PROV['specializationOf'].uri): 'specialization',
                           URIRef(PROV['mentionOf'].uri): 'mention',
                           URIRef(PROV['wasAssociatedWith'].uri): 'association',
                           URIRef(PROV['wasAttributedTo'].uri): 'attribution',
                           URIRef(PROV['wasInformedBy'].uri): 'communication',
                           URIRef(PROV['wasGeneratedBy'].uri): 'generation',
                           URIRef(PROV['wasInfluencedBy'].uri): 'influence',
                           URIRef(PROV['wasInvalidatedBy'].uri): 'invalidation',
                           URIRef(PROV['wasEndedBy'].uri): 'end',
                           URIRef(PROV['wasStartedBy'].uri): 'start',
                           URIRef(PROV['hadMember'].uri): 'membership',
                           URIRef(PROV['used'].uri): 'usage',
                           }
        other_attributes = {}
        for stmt in graph.triples((None, RDF.type, None)):
            id = unicode(stmt[0])
            obj = unicode(stmt[2])
            #print obj, type(obj), obj in PROV_CLS_MAP #dbg
            if obj in PROV_CLS_MAP:
                #print 'obj_found' #dbg
                try:
                    prov_obj = PROV_CLS_MAP[obj]
                except AttributeError, e:
                    prov_obj = None
                if id not in ids and prov_obj:
                    ids[id] = prov_obj
                    klass = pm.PROV_REC_CLS[prov_obj]
                    formal_attributes[id] = OrderedDict([(key, None) for key in klass.FORMAL_ATTRIBUTES])
                    unique_sets[id] = OrderedDict([(key, []) for key in klass.FORMAL_ATTRIBUTES])
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
                other_attributes[id].append((pm.PROV['type'], obj))
        for id, pred, obj in graph:
            id = unicode(id)
            if id not in other_attributes:
                other_attributes[id] = []
            if pred == RDF.type:
                continue
            if pred in relation_mapper:
                if 'mentionOf' in pred:
                    mentionBundle = None
                    for stmt in graph.triples((URIRef(id), URIRef(pm.PROV['asInBundle'].uri), None)):
                        mentionBundle = stmt[2]
                    getattr(bundle, relation_mapper[pred])(id, unicode(obj), mentionBundle)
                else:
                    getattr(bundle, relation_mapper[pred])(id, unicode(obj))
            elif id in ids:
                obj1 = self.decode_rdf_representation(obj)
                if pred == RDFS.label:
                    other_attributes[id].append((pm.PROV['label'], obj1))
                elif pred == URIRef(PROV['atLocation'].uri):
                    other_attributes[id].append((pm.PROV['location'], obj1))
                elif 'hadRole' in pred:
                    other_attributes[id].append((PROV_ROLE, obj1))
                elif 'hadPlan' in pred:
                    other_attributes[id].append((pm.PROV_ATTR_PLAN, obj1))
                elif 'hadActivity' in pred:
                    other_attributes[id].append((pm.PROV_ATTR_ACTIVITY, obj1))
                elif ids[id] == PROV_COMMUNICATION and 'activity' in pred:
                    formal_attributes[id][PROV_ATTR_INFORMANT] = obj1
                elif ids[id] == PROV_DELEGATION and 'agent' in pred:
                    formal_attributes[id][PROV_ATTR_RESPONSIBLE] = obj1
                elif ids[id] == PROV_DERIVATION:
                    if 'hadUsage' in pred:
                        formal_attributes[id][PROV_ATTR_USAGE] = obj1
                    elif 'hadGeneration' in pred:
                        formal_attributes[id][PROV_ATTR_GENERATION] = obj1
                    elif 'entity' in pred:
                        formal_attributes[id][PROV_ATTR_USED_ENTITY] = obj1
                    elif unicode(pred) in formal_attributes[id]:
                        qname_key = self.valid_identifier(unicode(pred))
                        formal_attributes[id][qname_key] = obj1
                        unique_sets[id][qname_key].append(obj1)
                        if len(unique_sets[id][qname_key]) > 1:
                            formal_attributes[id][qname_key] = None
                    else:
                        if 'qualified' not in pred:
                            other_attributes[id].append((unicode(pred), obj1))
                elif ids[id] in [PROV_END, PROV_START] and 'entity' in pred:
                    formal_attributes[id][PROV_ATTR_TRIGGER] = obj1
                elif unicode(pred) in [val.uri for val in formal_attributes[id]]:
                    qname_key = self.valid_identifier(unicode(pred))
                    formal_attributes[id][qname_key] = obj1
                    unique_sets[id][qname_key].append(obj1)
                    if len(unique_sets[id][qname_key]) > 1:
                        formal_attributes[id][qname_key] = None
                else:
                    if 'qualified' not in pred:
                        other_attributes[id].append((unicode(pred), obj1))
            local_key = unicode(obj)
            if local_key in ids:
                if 'qualified' in pred:
                    formal_attributes[local_key][formal_attributes[local_key].keys()[0]] = id
        for id in ids:
            attrs = None
            if id in other_attributes:
                attrs = other_attributes[id]
            items_to_walk = []
            for qname, values in unique_sets[id].items():
                if values and len(values) > 1:
                    items_to_walk.append((qname, values))
            if items_to_walk:
                for subset in list(walk(items_to_walk)):
                    for key, value in subset.items():
                        formal_attributes[id][key] = value
                    temp_id = bundle.new_record(ids[id], id, formal_attributes[id],
                                                attrs)
            else:
                temp_id = bundle.new_record(ids[id], id, formal_attributes[id],
                                            attrs)
            ids[id] = None #temp_id
            if attrs is not None:
                other_attributes[id] = []
        for key, val in other_attributes.items():
            if val:
                ids[key].add_attributes(val)

def walk(children, level=0, path=None, usename=True):
    """Generate all the full paths in a tree, as a dict.

    Examples
    --------
    >>> from nipype.pipeline.engine.utils import walk
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

def literal_rdf_representation(literal):
    value = unicode(literal.value) if literal.value else literal
    if literal.langtag:
        #  a language tag can only go with prov:InternationalizedString
        return RDFLiteral(value, lang=str(literal.langtag))
    else:
        datatype = literal.datatype
        if 'base64Binary' in datatype.uri:
            value = base64.standard_b64encode(value)
        return RDFLiteral(value, datatype=datatype.uri)
