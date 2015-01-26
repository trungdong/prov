from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

__author__ = 'Trung Dong Huynh'
__email__ = 'trungdong@donggiang.com'

import logging
logger = logging.getLogger(__name__)

from collections import defaultdict
import datetime
import io
import json
import six

from prov.serializers import Serializer, Error
from prov.constants import *
from prov.model import Literal, Identifier, QualifiedName, XSDQName, Namespace, ProvDocument, ProvBundle, \
    first, parse_xsd_datetime


class ProvJSONException(Error):
    pass


class AnonymousIDGenerator():
    def __init__(self):
        self._cache = {}
        self._count = 0

    def get_anon_id(self, obj, local_prefix="id"):
        if obj not in self._cache:
            self._count += 1
            self._cache[obj] = Identifier('_:%s%d' % (local_prefix, self._count))
        return self._cache[obj]


# Reverse map for prov.model.XSD_DATATYPE_PARSERS
LITERAL_XSDTYPE_MAP = {
    float: u"xsd:double",
    int: u"xsd:int"
    # boolean, string values are supported natively by PROV-JSON
    # datetime values are converted separately
}

# Add long on Python 2
if six.integer_types[-1] not in LITERAL_XSDTYPE_MAP:
   LITERAL_XSDTYPE_MAP[six.integer_types[-1]] = u"xsd:long"


class ProvJSONSerializer(Serializer):
    """
    PROV-JSON serializer for :class:`~prov.model.ProvDocument`
    """
    def serialize(self, stream, **kwargs):
        """
        Serializes a :class:`~prov.model.ProvDocument` instance to
        `PROV-JSON <https://provenance.ecs.soton.ac.uk/prov-json/>`_.

        :param stream: Where to save the output.
        """
        buf = io.BytesIO()
        try:
            json.dump(self.document, buf, cls=ProvJSONEncoder,
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

    def deserialize(self, stream, **kwargs):
        """
        Deserialize from the `PROV JSON <https://provenance.ecs.soton.ac.uk/prov-json/>`_ representation to a
        :class:`~prov.model.ProvDocument` instance.

        :param stream: Input data.
        """
        return json.load(stream, cls=ProvJSONDecoder, **kwargs)


class ProvJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ProvDocument):
            return encode_json_document(o)
        else:
            return super(ProvJSONEncoder, self).encode(o)


class ProvJSONDecoder(json.JSONDecoder):
    def decode(self, s, *args, **kwargs):
        container = super(ProvJSONDecoder, self).decode(s, *args, **kwargs)
        document = ProvDocument()
        decode_json_document(container, document)
        return document


# Encoding/decoding functions
def valid_qualified_name(bundle, value, xsd_qname=False):
    if value is None:
        return None
    qualified_name = bundle.valid_qualified_name(value)
    return qualified_name if not xsd_qname else XSDQName(qualified_name)


def encode_json_document(document):
    container = encode_json_container(document)
    for bundle in document.bundles:
        #  encoding the sub-bundle
        bundle_json = encode_json_container(bundle)
        container['bundle'][six.text_type(bundle.identifier)] = bundle_json
    return container


def encode_json_container(bundle):
    container = defaultdict(dict)
    prefixes = {}
    for namespace in bundle._namespaces.get_registered_namespaces():
        prefixes[namespace.prefix] = namespace.uri
    if bundle._namespaces._default:
        prefixes['default'] = bundle._namespaces._default.uri
    if prefixes:
        container[u'prefix'] = prefixes

    id_generator = AnonymousIDGenerator()
    real_or_anon_id = lambda r: r._identifier if r._identifier else id_generator.get_anon_id(r)

    for record in bundle._records:
        rec_type = record.get_type()
        rec_label = PROV_N_MAP[rec_type]
        identifier = six.text_type(real_or_anon_id(record))

        record_json = {}
        if record._attributes:
            for (attr, values) in record._attributes.items():
                if not values:
                    continue
                attr_name = six.text_type(attr)
                if attr in PROV_ATTRIBUTE_QNAMES:
                    record_json[attr_name] = six.text_type(first(values))  # TODO: QName export
                elif attr in PROV_ATTRIBUTE_LITERALS:
                    record_json[attr_name] = first(values).isoformat()
                else:
                    if len(values) == 1:
                        # single value
                        record_json[attr_name] = encode_json_representation(first(values))
                    else:
                        # multiple values
                        record_json[attr_name] = list(
                            encode_json_representation(value) for value in values
                        )
        # Check if the container already has the id of the record
        if identifier not in container[rec_label]:
            # this is the first instance, just put in the new record
            container[rec_label][identifier] = record_json
        else:
            # the container already has some record(s) of the same identifier
            # check if this is the second instance
            current_content = container[rec_label][identifier]
            if hasattr(current_content, 'items'):
                # this is a dict, make it a singleton list
                container[rec_label][identifier] = [current_content]
            # now append the new record to the list
            container[rec_label][identifier].append(record_json)

    return container


def decode_json_document(content, document):
    bundles = dict()
    if u'bundle' in content:
        bundles = content[u'bundle']
        del content[u'bundle']

    decode_json_container(content, document)

    for bundle_id, bundle_content in bundles.items():
        bundle = ProvBundle(document=document)
        decode_json_container(bundle_content, bundle)
        document.add_bundle(bundle, bundle.valid_qualified_name(bundle_id))


def decode_json_container(jc, bundle):
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
            if hasattr(content, 'items'):  # it is a dict
                #  There is only one element, create a singleton list
                elements = [content]
            else:
                # expect it to be a list of dictionaries
                elements = content

            for element in elements:
                attributes = dict()
                other_attributes = []
                membership_extra_members = None  # this is for the multiple-entity membership hack to come
                for attr_name, values in element.items():
                    attr = PROV_ATTRIBUTES_ID_MAP[attr_name] if attr_name in PROV_ATTRIBUTES_ID_MAP \
                        else valid_qualified_name(bundle, attr_name)
                    if attr in PROV_ATTRIBUTES:
                        if isinstance(values, list):
                            # only one value is allowed
                            if len(values) > 1:
                                # unless it is the membership hack
                                if rec_type == PROV_MEMBERSHIP and attr == PROV_ATTR_ENTITY:
                                    # This is a membership relation with multiple entities
                                    # HACK: create multiple membership relations, one for each entity
                                    membership_extra_members = values[1:]  # Store all the extra entities
                                    # Create the first membership relation as normal for the first entity
                                    value = values[0]
                                else:
                                    error_msg = 'The prov package does not support PROV attributes ' \
                                                'having multiple values.'
                                    logger.error(error_msg)
                                    raise ProvJSONException(error_msg)
                            else:
                                value = values[0]
                        else:
                            value = values
                        value = valid_qualified_name(bundle, value) if attr in PROV_ATTRIBUTE_QNAMES else \
                            parse_xsd_datetime(value)
                        attributes[attr] = value
                    else:
                        if isinstance(values, list):
                            other_attributes.extend(
                                (attr, decode_json_representation(value, bundle))
                                for value in values
                            )
                        else:
                            # single value
                            other_attributes.append((attr, decode_json_representation(values, bundle)))
                bundle.new_record(rec_type, rec_id, attributes, other_attributes)
                # HACK: creating extra (unidentified) membership relations
                if membership_extra_members:
                    collection = attributes[PROV_ATTR_COLLECTION]
                    for member in membership_extra_members:
                        bundle.membership(collection, valid_qualified_name(bundle, member))


def encode_json_representation(value):
    if isinstance(value, Literal):
        return literal_json_representation(value)
    elif isinstance(value, datetime.datetime):
        return {'$': value.isoformat(), 'type': u'xsd:dateTime'}
    elif isinstance(value, XSDQName):
        # Process XSDQName before QualifiedName because it is a subclass of QualifiedName
        # TODO QName export
        return {'$': str(value), 'type': u'xsd:QName'}
    elif isinstance(value, QualifiedName):
        # TODO Manage prefix in the whole structure consistently
        # TODO QName export
        return {'$': str(value), 'type': u'prov:QualifiedName'}
    elif isinstance(value, Identifier):
        return {'$': value.uri, 'type': u'xsd:anyURI'}
    elif type(value) in LITERAL_XSDTYPE_MAP:
        return {'$': value, 'type': LITERAL_XSDTYPE_MAP[type(value)]}
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
        elif datatype == XSD_QNAME:
            return valid_qualified_name(bundle, value, xsd_qname=True)
        elif datatype == PROV_QUALIFIEDNAME:
            return valid_qualified_name(bundle, value)
        else:
            # The literal of standard Python types is not converted here
            # It will be automatically converted when added to a record by _auto_literal_conversion()
            return Literal(value, datatype, langtag)
    else:
        # simple type, just return it
        return literal


def literal_json_representation(literal):
    # TODO: QName export
    value, datatype, langtag = literal.value, literal.datatype, literal.langtag
    if langtag:
        return {'$': value, 'lang': langtag, 'type': six.text_type(datatype)}
    else:
        return {'$': value, 'type': six.text_type(datatype)}
