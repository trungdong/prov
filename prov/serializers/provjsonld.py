from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from rdflib.graph import ConjunctiveGraph

import datetime
import io
import json

from prov.serializers import Serializer, Error
from prov.constants import *
from prov.model import Literal, Identifier, QualifiedName, ProvDocument, first

__author__ = 'Trung Dong Huynh'
__email__ = 'trungdong@donggiang.com'


class ProvJSONLDException(Error):
    pass


class AnonymousIDGenerator:
    def __init__(self):
        self._cache = {}
        self._count = 0

    def get_anon_id(self, obj, local_prefix='id'):
        if obj not in self._cache:
            self._count += 1
            self._cache[obj] = Identifier(
                '_:%s%d' % (local_prefix, self._count)
            )
        return self._cache[obj]


# Reverse map for prov.model.XSD_DATATYPE_PARSERS
LITERAL_XSDTYPE_MAP = {
    float: 'xsd:double',
    int: 'xsd:int'
    # boolean, string values are supported natively by PROV-JSON-LD
    # datetime values are converted separately
}

# Add long on Python 2
if six.integer_types[-1] not in LITERAL_XSDTYPE_MAP:
    LITERAL_XSDTYPE_MAP[six.integer_types[-1]] = 'xsd:long'


def qn_to_string(qn):
    return six.text_type(qn)


PROV_JSONLD_CONTEXT = "https://provenance.ecs.soton.ac.uk/prov.jsonld"


class ProvJSONLDSerializer(Serializer):
    """
    PROV-JSON-LD serializer for :class:`~prov.model.ProvDocument`
    """
    def serialize(self, stream, **kwargs):
        """
        Serializes a :class:`~prov.model.ProvDocument` instance to
        `PROV-JSON-LD <https://provenance.ecs.soton.ac.uk/prov-jsonld/>`_.

        :param stream: Where to save the output.
        """
        if six.PY2:
            buf = io.BytesIO()
            try:
                json.dump(self.document, buf, cls=ProvJSONLDEncoder,
                          **kwargs)
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
                json.dump(self.document, buf, cls=ProvJSONLDEncoder,
                          **kwargs)
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
        Deserialize from the `PROV JSON
        <https://provenance.ecs.soton.ac.uk/prov-json/>`_ representation to a
        :class:`~prov.model.ProvDocument` instance.

        :param stream: Input data.
        """
        return jsonld_trig_json(stream)


class ProvConvertException(Exception):
    def __init__(self, msg=None):
        self.msg = msg


def provconvert(content, toextension, fromextension='json'):
    import subprocess

    stderr = None
    try:
        p = subprocess.Popen(
                [
                    '/usr/local/bin/provconvert',
                    '-infile', '-', '-informat', fromextension,
                    '-outfile', '-', '-outformat', toextension
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
        )
        p.stdin.write(content.encode('utf8'))
        stdout, stderr = p.communicate()
        return stdout
    except IOError:
        # The output file cannot be read, reporting any error
        raise ProvConvertException(stderr)


def jsonld_trig_json(stream):
    if not isinstance(stream, io.TextIOBase):
        buf = io.StringIO(stream.read().decode('utf-8'))
        stream = buf
    jsonld_str = stream.read()

    g = ConjunctiveGraph().parse(data=jsonld_str, format='json-ld')
    g2 = ConjunctiveGraph(store=g.store)
    trig_content = g2.serialize(format='turtle')
    json_content = provconvert(trig_content, 'json', 'ttl')
    return ProvDocument.deserialize(content=json_content)


class ProvJSONLDEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ProvDocument):
            jsonld_document = encode_jsonld_document(o)
            return jsonld_document
        else:
            return super(ProvJSONLDEncoder, self).encode(o)


# Binary relations: connect the two arguments with the relation in the mappings
PROV_O_BINARY_RELATION_MAPPINGS = {
    PROV_ALTERNATE: PROV['alternateOf'],
    PROV_SPECIALIZATION: PROV['specializationOf'],
    PROV_MEMBERSHIP: PROV['hadMember']
}

PROV_O_SPECIAL_ATTRIBUTE_MAPPINGS = {
    PROV_LABEL: "label",
    PROV_ROLE: "hadRole",
    PROV_LOCATION: "atLocation"
}

# Mappings of properties in PROV-DM to those in PROV-O
PROV_JSONLD_ATTRIBUTE_MAPPINGS = {
    PROV_ENTITY: {  # No special mapping
    },
    PROV_AGENT: {  # No special mapping
    },
    PROV_ACTIVITY: {
        PROV_ATTR_STARTTIME: "startedAtTime",
        PROV_ATTR_ENDTIME: "endedAtTime",
    },
    PROV_USAGE: {
        PROV_ATTR_ACTIVITY: "activity_using",
        PROV_ATTR_ENTITY: "entity",
        PROV_ATTR_TIME: "atTime"
    },
    PROV_GENERATION: {
        PROV_ATTR_ENTITY: "entity_generated",
        PROV_ATTR_ACTIVITY: "activity",
        PROV_ATTR_TIME: "atTime"
    },
    PROV_START: {
        PROV_ATTR_ACTIVITY: "activity_started",
        PROV_ATTR_TRIGGER: "entity",
        PROV_ATTR_ENDER: "hadActivity",
        PROV_ATTR_TIME: "atTime"
    },
    PROV_END: {
        PROV_ATTR_ACTIVITY: "activity_ended",
        PROV_ATTR_TRIGGER: "entity",
        PROV_ATTR_ENDER: "hadActivity",
        PROV_ATTR_TIME: "atTime"
    },
    PROV_DERIVATION: {
        PROV_ATTR_GENERATED_ENTITY: "entity_derived",
        PROV_ATTR_USED_ENTITY: "entity",
        PROV_ATTR_ACTIVITY: "hadActivity",
        PROV_ATTR_GENERATION: "hadGeneration",
        PROV_ATTR_USAGE: "hadUsage"
    },
    PROV_COMMUNICATION: {
        PROV_ATTR_INFORMED: "informed",
        PROV_ATTR_INFORMANT: "activity"
    },
    PROV_INVALIDATION: {
        PROV_ATTR_ENTITY: "entity_invalidated",
        PROV_ATTR_ACTIVITY: "activity",
        PROV_ATTR_TIME: "atTime"
    },
    PROV_ATTRIBUTION: {
        PROV_ATTR_ENTITY: "entity_attributed",
        PROV_ATTR_AGENT: "agent"
    },
    PROV_ASSOCIATION: {
        PROV_ATTR_ACTIVITY: "activity_associated",
        PROV_ATTR_AGENT: "agent",
        PROV_ATTR_PLAN: "hadPlan"
    },
    PROV_DELEGATION: {
        PROV_ATTR_DELEGATE: "delegate",
        PROV_ATTR_RESPONSIBLE: "agent",
        PROV_ATTR_ACTIVITY: "hadActivity"
    },
    PROV_INFLUENCE: {
        PROV_ATTR_INFLUENCEE: "influencee",
        PROV_ATTR_INFLUENCER: "influencer"
    }
}
# Add the special mappings to all mappings
for mappings in PROV_JSONLD_ATTRIBUTE_MAPPINGS.values():
    mappings.update(PROV_O_SPECIAL_ATTRIBUTE_MAPPINGS)


# Encoding/decoding functions
def valid_qualified_name(bundle, value):
    if value is None:
        return None
    qualified_name = bundle.valid_qualified_name(value)
    return qualified_name


def encode_jsonld_document(document):
    container = encode_jsonld_container(document)
    graphs = [container]
    for bundle in document.bundles:
        #  encoding the sub-bundle
        bundle_json = encode_jsonld_container(bundle)
        graphs.append(bundle_json)
    return container if len(graphs) == 1 else graphs


def encode_jsonld_container(bundle):
    container = {
        "@context": [PROV_JSONLD_CONTEXT],
    }

    # If this is a bundle, set the graph ID
    if bundle.is_bundle():
        container["@id"] = qn_to_string(bundle.identifier)

    # Populate the context with registered namespaces
    # TODO: handle namespace inheritance
    prefixes = extract_prefixes(bundle)
    if prefixes:
        container["@context"].append(prefixes)

    record_list = []
    for record in bundle._records:
        record_json = {}
        record_type = record.get_type()

        # Binary or qualified relations?
        if record_type in PROV_O_BINARY_RELATION_MAPPINGS:
            pred = PROV_O_BINARY_RELATION_MAPPINGS[record_type]
            subj, obj = record.args  # expecting only two formal arguments
            record_json["@id"] = qn_to_string(subj)
            record_json[qn_to_string(pred)] = qn_to_string(obj)
        elif record_type in PROV_JSONLD_ATTRIBUTE_MAPPINGS:
            types = [record_type]  # collecting all the types in this list
            if record.identifier:
                record_json["@id"] = qn_to_string(record.identifier)
            json_ld_attr_mappings = PROV_JSONLD_ATTRIBUTE_MAPPINGS[record_type]
            if record._attributes:
                for (attr, values) in record._attributes.items():
                    if not values:
                        continue
                    attr_name = json_ld_attr_mappings[attr] if attr in json_ld_attr_mappings else qn_to_string(attr)
                    if attr in PROV_ATTRIBUTE_QNAMES:
                        # TODO: QName export
                        record_json[attr_name] = qn_to_string(first(values))
                    elif attr in PROV_ATTRIBUTE_LITERALS:
                        record_json[attr_name] = first(values).isoformat()
                    else:
                        if attr == PROV_TYPE:  # Special case for prov:type
                            prov_type_values = []  # list of non-Identifier types
                            for value in values:
                                if isinstance(value, Identifier):
                                    types.append(value)
                                else:
                                    prov_type_values.append(value)
                            if prov_type_values:
                                values = prov_type_values
                            else:
                                continue
                        record_json[attr_name] = encode_multiple_jsonld_values(values)
            record_json["@type"] = encode_multiple_jsonld_values(types, expecting_iris=True)
        else:
            # TODO: Unsupported records
            raise
        record_list.append(record_json)

    container["@graph"] = record_list
    return container


def extract_prefixes(bundle):
    prefixes = {}

    for namespace in bundle._namespaces.get_registered_namespaces():
        prefixes[namespace.prefix] = namespace.uri
    if bundle._namespaces._default:
        prefixes["@base"] = bundle._namespaces._default.uri

    if bundle.document:
        parent_prefixes = extract_prefixes(bundle.document)
        parent_prefixes.update(prefixes)
        prefixes = parent_prefixes

    return prefixes


def encode_multiple_jsonld_values(values, expecting_iris=False):
    if len(values) == 1:
        return encode_jsonld_representation(first(values), expecting_iris)
    else:
        # multiple values
        return list(encode_jsonld_representation(value, expecting_iris) for value in values)


def encode_jsonld_representation(value, expecting_iris=False):
    if isinstance(value, Literal):
        return literal_jsonld_representation(value)
    elif isinstance(value, datetime.datetime):
        return {'@value': value.isoformat(), '@type': 'xsd:dateTime'}
    elif isinstance(value, QualifiedName):
        qn_str = qn_to_string(value)
        return qn_str if expecting_iris else {'@id': qn_str}
    elif isinstance(value, Identifier):
        return value.uri if expecting_iris else {'@id': value.uri}
    elif isinstance(value, int):
        return value
    elif isinstance(value, float) and not value.is_integer():
        return value
    elif type(value) in LITERAL_XSDTYPE_MAP:
        return {'@value': value, '@type': LITERAL_XSDTYPE_MAP[type(value)]}
    else:
        return value


def decode_json_representation(literal, bundle):
    if isinstance(literal, dict):
        # complex type
        value = literal['$']
        datatype = literal['type'] if 'type' in literal else None
        datatype = valid_qualified_name(bundle, datatype)
        langtag = literal['lang'] if 'lang' in literal else None
        if datatype == XSD_ANYURI:
            return Identifier(value)
        elif datatype == PROV_QUALIFIEDNAME:
            return valid_qualified_name(bundle, value)
        else:
            # The literal of standard Python types is not converted here
            # It will be automatically converted when added to a record by
            # _auto_literal_conversion()
            return Literal(value, datatype, langtag)
    else:
        # simple type, just return it
        return literal


def literal_jsonld_representation(literal):
    # TODO: QName export
    value, datatype, langtag = literal.value, literal.datatype, literal.langtag
    if langtag:
        return {'@value': value, '@language': langtag}
    else:
        return {'@value': value, 'type': qn_to_string(datatype)}
