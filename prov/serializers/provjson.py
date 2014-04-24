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
from prov.contants import *
from prov.model import Literal, Identifier, QName, Namespace, ProvRecord, ProvDocument


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


class ProvJSONSerializer(Serializer):
    def serialize(self, stream, **kwargs):
        container = self.encode_document(self.document)
        json.dump(container, stream, **kwargs)

    def deserialize(self, stream, **kwargs):
        container = json.load(stream, **kwargs)
        document = ProvDocument()
        self.document = document
        self.decode_document(container, document)
        return document

    def valid_identifier(self, value):
        return self.document.valid_identifier(value)

    def encode_json_representation(self, value):
        if isinstance(value, Literal):
            return literal_json_representation(value)
        elif isinstance(value, datetime.datetime):
            return {'$': value.isoformat(), 'type': u'xsd:dateTime'}
        elif isinstance(value, QName):
            # TODO Manage prefix in the whole structure consistently
            return {'$': str(value), 'type': u'prov:QualifiedName'}
        elif isinstance(value, Identifier):
            return {'$': value.uri, 'type': u'xsd:anyURI'}
        else:
            return value

    def decode_json_representation(self, literal):
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
        container = defaultdict(dict)
        prefixes = {}
        for namespace in bundle._namespaces.get_registered_namespaces():
            prefixes[namespace.prefix] = namespace.uri
        if bundle._namespaces._default:
            prefixes['default'] = bundle._namespaces._default.uri
        if prefixes:
            container[u'prefix'] = prefixes

        id_generator = AnonymousIDGenerator()
        real_or_anon_id = lambda record: record._identifier if record._identifier else id_generator.get_anon_id(record)

        for record in bundle._records:
            rec_type = record.get_type()
            rec_label = PROV_N_MAP[rec_type]
            identifier = unicode(real_or_anon_id(record))

            record_json = {}
            if record._attributes:
                for (attr, value) in record._attributes.items():
                    if isinstance(value, ProvRecord):
                        attr_record_id = real_or_anon_id(value)
                        record_json[PROV_ID_ATTRIBUTES_MAP[attr]] = unicode(attr_record_id)
                    elif value is not None:
                        #  Assuming this is a datetime value
                        record_json[PROV_ID_ATTRIBUTES_MAP[attr]] = value.isoformat() if isinstance(value, datetime.datetime) else unicode(value)
            if record._extra_attributes:
                for (attr, value) in record._extra_attributes:
                    attr_id = unicode(attr)
                    value_json = self.encode_json_representation(value)
                    if attr_id in record_json:
                        #  Multi-value attribute
                        existing_value = record_json[attr_id]
                        try:
                            #  Add the value to the current list of values
                            existing_value.append(value_json)
                        except:
                            #  But if the existing value is not a list, it'll fail
                            #  create the list for the existing value and the second value
                            record_json[attr_id] = [existing_value, value_json]
                    else:
                        record_json[attr_id] = value_json
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
                if rec_type == PROV_REC_BUNDLE:
                    raise ProvJSONException('A bundle cannot have nested bundles')
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
                                        if rec_type == PROV_REC_MEMBERSHIP and attr_id == PROV_ATTR_ENTITY:
                                            # This is a membership relation with multiple entities
                                            # HACK: create multiple membership relations, one for each entity
                                            membership_extra_members = value[1:]  # Store all the extra entities
                                            value = value[0]  # Create the first membership relation as normal for the first entity
                                        else:
                                            error_msg = 'The prov package does not support PROV attributes having multiple values.'
                                            logger.error(error_msg)
                                            raise ProvJSONException(error_msg)
                                prov_attributes[attr_id] =\
                                    self.valid_identifier(value) if attr_id not in PROV_ATTRIBUTE_LITERALS else \
                                    self.decode_json_representation(value)
                            else:
                                attr_id = self.valid_identifier(attr)
                                if isinstance(value, list):
                                    #  Parsing multi-value attribute
                                    extra_attributes.extend(
                                        (attr_id, self.decode_json_representation(value_single))
                                        for value_single in value
                                    )
                                else:
                                    #  add the single-value attribute
                                    extra_attributes.append((attr_id, self.decode_json_representation(value)))
                        bundle.add_record(rec_type, rec_id, prov_attributes, extra_attributes)
                        # HACK: creating extra (unidentified) membership relations
                        if membership_extra_members:
                            collection = prov_attributes[PROV_ATTR_COLLECTION]
                            for member in membership_extra_members:
                                bundle.membership(collection, self.valid_identifier(member))


def literal_json_representation(literal):
    if literal._langtag:
        #  a language tag can only go with prov:InternationalizedString
        return {'$': unicode(literal._value), 'lang': literal._langtag}
    else:
        if isinstance(literal._datatype, QName):
            return {'$': unicode(literal._value), 'type': unicode(literal._datatype)}
        else:
            #  Assuming it is a valid identifier
            return {'$': unicode(literal._value), 'type': literal._datatype.get_uri()}
