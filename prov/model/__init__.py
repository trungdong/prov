"""Python implementation of the W3C Provenance Data Model (PROV-DM), including support for PROV-JSON import/export

References:

PROV-DM: http://www.w3.org/TR/prov-dm/
PROV-JSON: https://provenance.ecs.soton.ac.uk/prov-json/

@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2014
"""

import logging
import datetime
import json
import dateutil.parser
from collections import defaultdict, Iterable
from copy import deepcopy
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
logger = logging.getLogger(__name__)

#  # PROV record constants - PROV-DM LC
#  C1. Entities/Activities
PROV_REC_ENTITY = 1
PROV_REC_ACTIVITY = 2
PROV_REC_GENERATION = 11
PROV_REC_USAGE = 12
PROV_REC_COMMUNICATION = 13
PROV_REC_START = 14
PROV_REC_END = 15
PROV_REC_INVALIDATION = 16

#  C2. Derivations
PROV_REC_DERIVATION = 21

#  C3. Agents/Responsibility
PROV_REC_AGENT = 3
PROV_REC_ATTRIBUTION = 31
PROV_REC_ASSOCIATION = 32
PROV_REC_DELEGATION = 33
PROV_REC_INFLUENCE = 34
#  C4. Bundles
PROV_REC_BUNDLE = 4  # This is the lowest value, so bundle(s) in JSON will be decoded first
#  C5. Alternate
PROV_REC_ALTERNATE = 51
PROV_REC_SPECIALIZATION = 52
PROV_REC_MENTION = 53
#  C6. Collections
PROV_REC_MEMBERSHIP = 61

PROV_RECORD_TYPES = (
    (PROV_REC_ENTITY, u'Entity'),
    (PROV_REC_ACTIVITY, u'Activity'),
    (PROV_REC_GENERATION, u'Generation'),
    (PROV_REC_USAGE, u'Usage'),
    (PROV_REC_COMMUNICATION, u'Communication'),
    (PROV_REC_START, u'Start'),
    (PROV_REC_END, u'End'),
    (PROV_REC_INVALIDATION, u'Invalidation'),
    (PROV_REC_DERIVATION, u'Derivation'),
    (PROV_REC_AGENT, u'Agent'),
    (PROV_REC_ATTRIBUTION, u'Attribution'),
    (PROV_REC_ASSOCIATION, u'Association'),
    (PROV_REC_DELEGATION, u'Delegation'),
    (PROV_REC_INFLUENCE, u'Influence'),
    (PROV_REC_BUNDLE, u'Bundle'),
    (PROV_REC_ALTERNATE, u'Alternate'),
    (PROV_REC_SPECIALIZATION, u'Specialization'),
    (PROV_REC_MENTION, u'Mention'),
    (PROV_REC_MEMBERSHIP, u'Membership'),
)

PROV_N_MAP = {
    PROV_REC_ENTITY:               u'entity',
    PROV_REC_ACTIVITY:             u'activity',
    PROV_REC_GENERATION:           u'wasGeneratedBy',
    PROV_REC_USAGE:                u'used',
    PROV_REC_COMMUNICATION:        u'wasInformedBy',
    PROV_REC_START:                u'wasStartedBy',
    PROV_REC_END:                  u'wasEndedBy',
    PROV_REC_INVALIDATION:         u'wasInvalidatedBy',
    PROV_REC_DERIVATION:           u'wasDerivedFrom',
    PROV_REC_AGENT:                u'agent',
    PROV_REC_ATTRIBUTION:          u'wasAttributedTo',
    PROV_REC_ASSOCIATION:          u'wasAssociatedWith',
    PROV_REC_DELEGATION:           u'actedOnBehalfOf',
    PROV_REC_INFLUENCE:            u'wasInfluencedBy',
    PROV_REC_ALTERNATE:            u'alternateOf',
    PROV_REC_SPECIALIZATION:       u'specializationOf',
    PROV_REC_MENTION:              u'mentionOf',
    PROV_REC_MEMBERSHIP:           u'hadMember',
    PROV_REC_BUNDLE:               u'bundle',
}

#  # Identifiers for PROV's attributes
PROV_ATTR_ENTITY = 1
PROV_ATTR_ACTIVITY = 2
PROV_ATTR_TRIGGER = 3
PROV_ATTR_INFORMED = 4
PROV_ATTR_INFORMANT = 5
PROV_ATTR_STARTER = 6
PROV_ATTR_ENDER = 7
PROV_ATTR_AGENT = 8
PROV_ATTR_PLAN = 9
PROV_ATTR_DELEGATE = 10
PROV_ATTR_RESPONSIBLE = 11
PROV_ATTR_GENERATED_ENTITY = 12
PROV_ATTR_USED_ENTITY = 13
PROV_ATTR_GENERATION = 14
PROV_ATTR_USAGE = 15
PROV_ATTR_SPECIFIC_ENTITY = 16
PROV_ATTR_GENERAL_ENTITY = 17
PROV_ATTR_ALTERNATE1 = 18
PROV_ATTR_ALTERNATE2 = 19
PROV_ATTR_BUNDLE = 20
PROV_ATTR_INFLUENCEE = 21
PROV_ATTR_INFLUENCER = 22
PROV_ATTR_COLLECTION = 23

#  Literal properties
PROV_ATTR_TIME = 100
PROV_ATTR_STARTTIME = 101
PROV_ATTR_ENDTIME = 102

PROV_RECORD_ATTRIBUTES = (
    #  Relations properties
    (PROV_ATTR_ENTITY, u'prov:entity'),
    (PROV_ATTR_ACTIVITY, u'prov:activity'),
    (PROV_ATTR_TRIGGER, u'prov:trigger'),
    (PROV_ATTR_INFORMED, u'prov:informed'),
    (PROV_ATTR_INFORMANT, u'prov:informant'),
    (PROV_ATTR_STARTER, u'prov:starter'),
    (PROV_ATTR_ENDER, u'prov:ender'),
    (PROV_ATTR_AGENT, u'prov:agent'),
    (PROV_ATTR_PLAN, u'prov:plan'),
    (PROV_ATTR_DELEGATE, u'prov:delegate'),
    (PROV_ATTR_RESPONSIBLE, u'prov:responsible'),
    (PROV_ATTR_GENERATED_ENTITY, u'prov:generatedEntity'),
    (PROV_ATTR_USED_ENTITY, u'prov:usedEntity'),
    (PROV_ATTR_GENERATION, u'prov:generation'),
    (PROV_ATTR_USAGE, u'prov:usage'),
    (PROV_ATTR_SPECIFIC_ENTITY, u'prov:specificEntity'),
    (PROV_ATTR_GENERAL_ENTITY, u'prov:generalEntity'),
    (PROV_ATTR_ALTERNATE1, u'prov:alternate1'),
    (PROV_ATTR_ALTERNATE2, u'prov:alternate2'),
    (PROV_ATTR_BUNDLE, u'prov:bundle'),
    (PROV_ATTR_INFLUENCEE, u'prov:influencee'),
    (PROV_ATTR_INFLUENCER, u'prov:influencer'),
    (PROV_ATTR_COLLECTION, u'prov:collection'),
    #  Literal properties
    (PROV_ATTR_TIME, u'prov:time'),
    (PROV_ATTR_STARTTIME, u'prov:startTime'),
    (PROV_ATTR_ENDTIME, u'prov:endTime'),
)

PROV_ATTRIBUTE_LITERALS = {PROV_ATTR_TIME, PROV_ATTR_STARTTIME, PROV_ATTR_ENDTIME}

PROV_RECORD_IDS_MAP = dict((PROV_N_MAP[rec_type_id], rec_type_id) for rec_type_id in PROV_N_MAP)
PROV_ID_ATTRIBUTES_MAP = dict((prov_id, attribute) for (prov_id, attribute) in PROV_RECORD_ATTRIBUTES)
PROV_ATTRIBUTES_ID_MAP = dict((attribute, prov_id) for (prov_id, attribute) in PROV_RECORD_ATTRIBUTES)


# Converting an attribute to the normal form for comparison purposes
_normalise_attributes = lambda attr: (unicode(attr[0]), unicode(attr[1]))


# Data Types
def _ensure_datetime(value):
    if isinstance(value, basestring):
        return dateutil.parser.parse(value)
    else:
        return value


def parse_xsd_dateTime(value):
    try:
        return dateutil.parser.parse(value)
    except ValueError:
        pass
    return None

DATATYPE_PARSERS = {
    datetime.datetime: parse_xsd_dateTime,
}


def _parse_datatype(value, datatype):
    if datatype in DATATYPE_PARSERS:
        #  found the required parser
        return DATATYPE_PARSERS[datatype](value)
    else:
        #  No parser found for the given data type
        raise Exception(u'No parser found for the data type <%s>' % unicode(datatype))


# Mappings for XSD datatypes to Python standard types
XSD_DATATYPE_PARSERS = {
    u"xsd:string": unicode,
    u"xsd:double": float,
    u"xsd:long": long,
    u"xsd:int": int,
    u"xsd:boolean": bool,
    u"xsd:dateTime": parse_xsd_dateTime,
}


def parse_xsd_types(value, datatype):
    # if the datatype is a QName, convert it to a Unicode string
    datatype = unicode(datatype)
    return XSD_DATATYPE_PARSERS[datatype](value) if datatype in XSD_DATATYPE_PARSERS else None


def _ensure_multiline_string_triple_quoted(s):
    format_str = u'"""%s"""' if isinstance(s, basestring) and '\n' in s else u'"%s"'
    return format_str % s


def encoding_PROV_N_value(value):
    if isinstance(value, basestring):
        return _ensure_multiline_string_triple_quoted(value)
    elif isinstance(value, datetime.datetime):
        return value.isoformat()
    elif isinstance(value, float):
        return u'"%f" %%%% xsd:float' % value
    else:
        return unicode(value)


class AnonymousIDGenerator():
    def __init__(self):
        self._cache = {}
        self._count = 0

    def get_anon_id(self, obj, local_prefix="id"):
        if obj not in self._cache:
            self._count += 1
            self._cache[obj] = Identifier('_:%s%d' % (local_prefix, self._count))
        return self._cache[obj]


class Literal(object):
    def __init__(self, value, datatype=None, langtag=None):
        self._value = value
        if langtag:
            if datatype is None:
                logger.debug('Assuming prov:InternationalizedString as the type of "%s"@%s' % (value, langtag))
                datatype = PROV["InternationalizedString"]
            elif datatype != PROV["InternationalizedString"]:
                logger.warn('Invalid data type (%s) for "%s"@%s, overridden as prov:InternationalizedString.' % (value, langtag))
                datatype = PROV["InternationalizedString"]
        self._datatype = datatype
        self._langtag = langtag

    def __unicode__(self):
        return self.provn_representation()

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __eq__(self, other):
        return self._value == other._value and self._datatype == other._datatype and self._langtag == other._langtag if isinstance(other, Literal) else False

    def __hash__(self):
        return hash((self._value, self._datatype, self._langtag))

    def get_value(self):
        return self._value

    def get_datatype(self):
        return self._datatype

    def get_langtag(self):
        return self._langtag

    def has_no_langtag(self):
        return self._langtag is None

    def provn_representation(self):
        if self._langtag:
            #  a language tag can only go with prov:InternationalizedString
            return u'%s@%s' % (_ensure_multiline_string_triple_quoted(self._value), unicode(self._langtag))
        else:
            return u'%s %%%% %s' % (_ensure_multiline_string_triple_quoted(self._value), unicode(self._datatype))

    def json_representation(self):
        if self._langtag:
            #  a language tag can only go with prov:InternationalizedString
            return {'$': unicode(self._value), 'lang': self._langtag}
        else:
            if isinstance(self._datatype, QName):
                return {'$': unicode(self._value), 'type': unicode(self._datatype)}
            else:
                #  Assuming it is a valid identifier
                return {'$': unicode(self._value), 'type': self._datatype.get_uri()}


class Identifier(object):
    def __init__(self, uri):
        self._uri = unicode(uri)  # Ensure this is a unicode string

    def get_uri(self):
        return self._uri

    def __unicode__(self):
        return self._uri

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __eq__(self, other):
        return self.get_uri() == other.get_uri() if isinstance(other, Identifier) else False

    def __hash__(self):
        return hash(self.get_uri())

    def provn_representation(self):
        return u'"%s" %%%% xsd:anyURI' % self._uri

    def json_representation(self):
        return {'$': self._uri, 'type': u'xsd:anyURI'}


class QName(Identifier):
    def __init__(self, namespace, localpart):
        self._namespace = namespace
        self._localpart = localpart
        self._str = u':'.join([namespace._prefix, localpart]) if namespace._prefix else localpart

    def get_namespace(self):
        return self._namespace

    def get_localpart(self):
        return self._localpart

    def get_uri(self):
        return u''.join([self._namespace._uri, self._localpart])

    def __unicode__(self):
        return self._str

    def __str__(self):
        return unicode(self).encode('utf-8')

    def provn_representation(self):
        return u"'%s'" % self._str

    def json_representation(self):
        return {'$': self._str, 'type': u'prov:QualifiedName'}


class Namespace(object):
    def __init__(self, prefix, uri):
        self._prefix = prefix
        self._uri = uri
        self._cache = dict()

    def get_prefix(self):
        return self._prefix

    def get_uri(self):
        return self._uri

    def contains(self, identifier):
        uri = identifier if isinstance(identifier, (str, unicode)) else (identifier.get_uri() if isinstance(identifier, Identifier) else None)
        return uri.startswith(self._uri) if uri else False

    def qname(self, identifier):
        uri = identifier if isinstance(identifier, (str, unicode)) else (identifier.get_uri() if isinstance(identifier, Identifier) else None)
        if uri and uri.startswith(self._uri):
            return QName(self, uri[len(self._uri):])
        else:
            return None

    def __eq__(self, other):
        return (self._uri == other._uri and self._prefix == other._prefix) if isinstance(other, Namespace) else False

    def __hash__(self):
        return hash((self._uri, self._prefix))

    def __getitem__(self, localpart):
        if localpart in self._cache:
            return self._cache[localpart]
        else:
            qname = QName(self, localpart)
            self._cache[localpart] = qname
            return qname

XSD = Namespace('xsd', 'http://www.w3.org/2001/XMLSchema#')
PROV = Namespace('prov', 'http://www.w3.org/ns/prov#')


# Exceptions
class ProvException(Exception):
    """Base class for exceptions in this module."""
    pass


class ProvExceptionMissingRequiredAttribute(ProvException):
    def __init__(self, record_type, attribute_id):
        self.record_type = record_type
        self.attribute_id = attribute_id
        self.args += (PROV_N_MAP[record_type], attribute_id)

    def __str__(self):
        return 'Missing the required attribute "%s" in %s' % (PROV_ID_ATTRIBUTES_MAP[self.attribute_id], PROV_N_MAP[self.record_type])


class ProvExceptionNotValidAttribute(ProvException):
    def __init__(self, record_type, attribute, attribute_types):
        self.record_type = record_type
        self.attribute = attribute
        self.attribute_types = attribute_types
        self.args += (PROV_N_MAP[record_type], unicode(attribute), attribute_types)

    def __str__(self):
        return 'Invalid attribute value: %s. %s expected' % (self.attribute, self.attribute_types)


class ProvExceptionCannotUnifyAttribute(ProvException):
    def __init__(self, identifier, record_type1, record_type2):
        self.identifier = identifier
        self.record_type1 = record_type1
        self.record_type2 = record_type2
        self.args += (identifier, PROV_N_MAP[record_type1], PROV_N_MAP[record_type2])

    def __str__(self):
        return 'Cannot unify two records of type %s and %s with same identifier (%s)' % (self.identifier, PROV_N_MAP[self.record_type1], PROV_N_MAP[self.record_type2])


class ProvExceptionContraint(ProvException):
    def __init__(self, record_type, attribute1, attribute2, msg):
        self.record_type = record_type
        self.attribute1 = attribute1
        self.attribute2 = attribute2
        self.args += (PROV_N_MAP[record_type], attribute1, attribute2, msg)
        self.msg = msg


#  PROV records
class ProvRecord(object):
    """Base class for PROV _records."""
    def __init__(self, bundle, identifier, attributes=None, other_attributes=None):
        self._bundle = bundle
        self._identifier = identifier
        self._attributes = None
        self._extra_attributes = None
        if attributes or other_attributes:
            self.add_attributes(attributes, other_attributes)

    def get_type(self):
        """Returning the numeric type of the record"""
        pass

    def get_prov_type(self):
        """Returning the Qualified Name for the prov: class"""
        pass

    def get_asserted_types(self):
        if self._extra_attributes:
            prov_type = PROV['type']
            return set([value for attr, value in self._extra_attributes if attr == prov_type])
        return set()

    def add_asserted_type(self, type_identifier):
        asserted_types = self.get_asserted_types()
        if type_identifier not in asserted_types:
            if self._extra_attributes is None:
                self._extra_attributes = set()
            self._extra_attributes.add((PROV['type'], type_identifier))

    def get_attribute(self, attr_name):
        attr_name = self._bundle.valid_identifier(attr_name)
        if not self._extra_attributes:
            return []
        results = [value for attr, value in self._extra_attributes if attr == attr_name]
        return results

    def get_identifier(self):
        return self._identifier

    def get_label(self):
        label = None
        if self._extra_attributes:
            for attribute in self._extra_attributes:
                if attribute[0]:
                    if attribute[0] == PROV['label']:
                        label = attribute[1]
                        #  use the first label found
                        break
        return label if label else self._identifier

    def get_value(self):
        return self.get_attribute(PROV['value'])

    def _auto_literal_conversion(self, literal):
        # This method normalise datatype for literals
        if isinstance(literal, basestring):
            return unicode(literal)

        if isinstance(literal, Literal) and literal.has_no_langtag():
            # try convert generic Literal object to Python standard type if possible
            # this is to match JSON decoding's literal conversion
            value = parse_xsd_types(literal.get_value(), literal.get_datatype())
            if value is not None:
                return value

        # No conversion here, return the original value
        return literal

    def parse_extra_attributes(self, extra_attributes):
        if isinstance(extra_attributes, dict):
            #  Converting the dictionary into a list of tuples (i.e. attribute-value pairs)
            extra_attributes = extra_attributes.items()
        attr_set = set((self._bundle.valid_identifier(attribute), self._auto_literal_conversion(value)) for attribute, value in extra_attributes)
        return attr_set

    def add_extra_attributes(self, extra_attributes):
        if extra_attributes:
            if self._extra_attributes is None:
                self._extra_attributes = set()
            #  Check attributes for valid qualified names
            attr_set = self.parse_extra_attributes(extra_attributes)
            self._extra_attributes.update(attr_set)

    def add_attributes(self, attributes, extra_attributes):
        if attributes:
            if self._attributes is None:
                self._attributes = attributes
            else:
                self._attributes.update(dict((k, v) for k, v in attributes.iteritems() if v is not None))
        self.add_extra_attributes(extra_attributes)

    def get_attributes(self):
        return (self._attributes, self._extra_attributes)

    def get_bundle(self):
        return self._bundle

    def _parse_attribute(self, attribute, attribute_types):
        if attribute_types is QName:
            # Expecting a qualified name
            qname = attribute.get_identifier() if isinstance(attribute, ProvRecord) else attribute
            return self._bundle.valid_identifier(qname)

        # putting all the types in to a tuple:
        if not isinstance(attribute_types, Iterable):
            attribute_types = (attribute_types,)

        #  Try to parse it with known datatype parsers
        for datatype in attribute_types:
            data = _parse_datatype(attribute, datatype)
            if data is not None:
                return data
        return None

    def _validate_attribute(self, attribute, attribute_types):
        if isinstance(attribute, attribute_types):
            #  The attribute is of a required type
            #  Return it
            return attribute
        else:
            #  The attribute is not of a valid type
            #  Attempt to parse it
            parsed_value = self._parse_attribute(attribute, attribute_types)
            if parsed_value is None:
                raise ProvExceptionNotValidAttribute(self.get_type(), attribute, attribute_types)
            return parsed_value

    def required_attribute(self, attributes, attribute_id, attribute_types):
        if attribute_id not in attributes:
            #  Raise an exception about the missing attribute
            raise ProvExceptionMissingRequiredAttribute(self.get_type(), attribute_id)
        #  Found the required attribute
        attribute = attributes.get(attribute_id)
        return self._validate_attribute(attribute, attribute_types)

    def optional_attribute(self, attributes, attribute_id, attribute_types):
        if not attributes or attribute_id not in attributes:
            #  Because this is optional, return nothing
            return None
        #  Found the optional attribute
        attribute = attributes.get(attribute_id)
        if attribute is None:
            return None
        #  Validate its type
        return self._validate_attribute(attribute, attribute_types)

    def __eq__(self, other):
        if self.get_prov_type() != other.get_prov_type():
            return False
        if self._identifier and not (self._identifier == other._identifier):
            return False
        if self._attributes and other._attributes:
            if len(self._attributes) != len(other._attributes):
                return False
            for attr, value_a in self._attributes.items():
                value_b = other._attributes[attr]
                if not (value_a == value_b):
                    return False
        elif other._attributes and not self._attributes:
            other_attrs = [(key, value) for key, value in other._attributes.items() if value is not None]
            if other_attrs:
                #  the other's attributes set is not empty.
                return False
        elif self._attributes and not other._attributes:
            my_attrs = [(key, value) for key, value in self._attributes.items() if value is not None]
            if my_attrs:
                #  my attributes set is not empty.
                return False
        sattr = sorted(self._extra_attributes, key=_normalise_attributes) if self._extra_attributes else None
        oattr = sorted(other._extra_attributes, key=_normalise_attributes) if other._extra_attributes else None
        if sattr != oattr:
            if logger.isEnabledFor(logging.DEBUG):
                for spair, opair in zip(sattr, oattr):
                    # Log the first unequal pair of attributes
                    if spair != opair:
                        logger.debug("Equality (ProvRecord): unequal attribute-value pairs - %s = %s - %s = %s",
                                     spair[0], spair[1], opair[0], opair[1])
                        break
            return False
        return True

    def __unicode__(self):
        return self.get_provn()

    def __str__(self):
        return unicode(self).encode('utf-8')

    def get_provn(self, _indent_level=0):
        items = []
        if self._identifier:
            items.append(unicode(self._identifier))
        if self._attributes:
            for (attr, value) in self._attributes.items():
                if value is None:
                    items.append(u'-')
                else:
                    if isinstance(value, ProvRecord):
                        record_id = value.get_identifier()
                        items.append(unicode(record_id))
                    else:
                        #  Assuming this is a datetime or QName value
                        items.append(value.isoformat() if isinstance(value, datetime.datetime) else unicode(value))

        if self._extra_attributes:
            extra = []
            for (attr, value) in self._extra_attributes:
                try:
                    #  try if there is a prov-n representation defined
                    provn_represenation = value.provn_representation()
                except:
                    provn_represenation = encoding_PROV_N_value(value)
                extra.append(u'%s=%s' % (unicode(attr), provn_represenation))
            if extra:
                items.append(u'[%s]' % u', '.join(extra))
        prov_n = u'%s(%s)' % (PROV_N_MAP[self.get_type()], u', '.join(items))
        return prov_n

    def is_element(self):
        return False

    def is_relation(self):
        return False


# Abstract classes for elements and relations
class ProvElement(ProvRecord):
    def is_element(self):
        return True


class ProvRelation(ProvRecord):
    def is_relation(self):
        return True


#  ## Component 1: Entities and Activities

class ProvEntity(ProvElement):
    def get_type(self):
        return PROV_REC_ENTITY

    def get_prov_type(self):
        return PROV['Entity']


class ProvActivity(ProvElement):
    def get_type(self):
        return PROV_REC_ACTIVITY

    def get_prov_type(self):
        return PROV['Activity']

    def add_attributes(self, attributes, extra_attributes):
        startTime = self.optional_attribute(attributes, PROV_ATTR_STARTTIME, datetime.datetime)
        endTime = self.optional_attribute(attributes, PROV_ATTR_ENDTIME, datetime.datetime)
        if startTime and endTime and startTime > endTime:
            #  TODO Raise logic exception here
            pass
        attributes = OrderedDict()
        attributes[PROV_ATTR_STARTTIME] = startTime
        attributes[PROV_ATTR_ENDTIME] = endTime

        ProvElement.add_attributes(self, attributes, extra_attributes)

    #  Convenient methods
    def set_time(self, startTime=None, endTime=None):
        #  The _attributes dict should have been initialised
        if startTime is not None:
            self._attributes[PROV_ATTR_STARTTIME] = startTime
        if endTime is not None:
            self._attributes[PROV_ATTR_ENDTIME] = endTime

    def get_startTime(self):
        return self._attributes[PROV_ATTR_STARTTIME]

    def get_endTime(self):
        return self._attributes[PROV_ATTR_ENDTIME]


class ProvGeneration(ProvRelation):
    def get_type(self):
        return PROV_REC_GENERATION

    def get_prov_type(self):
        return PROV['Generation']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        entity = self.required_attribute(attributes, PROV_ATTR_ENTITY, QName)
        #  Optional attributes
        activity = self.optional_attribute(attributes, PROV_ATTR_ACTIVITY, QName)
        time = self.optional_attribute(attributes, PROV_ATTR_TIME, datetime.datetime)

        attributes = OrderedDict()
        attributes[PROV_ATTR_ENTITY] = entity
        attributes[PROV_ATTR_ACTIVITY] = activity
        attributes[PROV_ATTR_TIME] = time

        ProvRelation.add_attributes(self, attributes, extra_attributes)


class ProvUsage(ProvRelation):
    def get_type(self):
        return PROV_REC_USAGE

    def get_prov_type(self):
        return PROV['Usage']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        activity = self.required_attribute(attributes, PROV_ATTR_ACTIVITY, QName)
        #  Optional attributes
        entity = self.optional_attribute(attributes, PROV_ATTR_ENTITY, QName)
        time = self.optional_attribute(attributes, PROV_ATTR_TIME, datetime.datetime)

        attributes = OrderedDict()
        attributes[PROV_ATTR_ACTIVITY] = activity
        attributes[PROV_ATTR_ENTITY] = entity
        attributes[PROV_ATTR_TIME] = time
        ProvRelation.add_attributes(self, attributes, extra_attributes)


class ProvCommunication(ProvRelation):
    def get_type(self):
        return PROV_REC_COMMUNICATION

    def get_prov_type(self):
        return PROV['Communication']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        informed = self.required_attribute(attributes, PROV_ATTR_INFORMED, QName)
        informant = self.required_attribute(attributes, PROV_ATTR_INFORMANT, QName)

        attributes = OrderedDict()
        attributes[PROV_ATTR_INFORMED] = informed
        attributes[PROV_ATTR_INFORMANT] = informant
        ProvRelation.add_attributes(self, attributes, extra_attributes)


class ProvStart(ProvRelation):
    def get_type(self):
        return PROV_REC_START

    def get_prov_type(self):
        return PROV['Start']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        activity = self.required_attribute(attributes, PROV_ATTR_ACTIVITY, QName)
        #  Optional attributes
        trigger = self.optional_attribute(attributes, PROV_ATTR_TRIGGER, QName)
        starter = self.optional_attribute(attributes, PROV_ATTR_STARTER, QName)
        time = self.optional_attribute(attributes, PROV_ATTR_TIME, datetime.datetime)

        attributes = OrderedDict()
        attributes[PROV_ATTR_ACTIVITY] = activity
        attributes[PROV_ATTR_TRIGGER] = trigger
        attributes[PROV_ATTR_STARTER] = starter
        attributes[PROV_ATTR_TIME] = time
        ProvRelation.add_attributes(self, attributes, extra_attributes)


class ProvEnd(ProvRelation):
    def get_type(self):
        return PROV_REC_END

    def get_prov_type(self):
        return PROV['End']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        activity = self.required_attribute(attributes, PROV_ATTR_ACTIVITY, QName)
        #  Optional attributes
        trigger = self.optional_attribute(attributes, PROV_ATTR_TRIGGER, QName)
        ender = self.optional_attribute(attributes, PROV_ATTR_ENDER, QName)
        time = self.optional_attribute(attributes, PROV_ATTR_TIME, datetime.datetime)

        attributes = OrderedDict()
        attributes[PROV_ATTR_ACTIVITY] = activity
        attributes[PROV_ATTR_TRIGGER] = trigger
        attributes[PROV_ATTR_ENDER] = ender
        attributes[PROV_ATTR_TIME] = time
        ProvRelation.add_attributes(self, attributes, extra_attributes)


class ProvInvalidation(ProvRelation):
    def get_type(self):
        return PROV_REC_INVALIDATION

    def get_prov_type(self):
        return PROV['Invalidation']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        entity = self.required_attribute(attributes, PROV_ATTR_ENTITY, QName)
        #  Optional attributes
        activity = self.optional_attribute(attributes, PROV_ATTR_ACTIVITY, QName)
        time = self.optional_attribute(attributes, PROV_ATTR_TIME, datetime.datetime)

        attributes = OrderedDict()
        attributes[PROV_ATTR_ENTITY] = entity
        attributes[PROV_ATTR_ACTIVITY] = activity
        attributes[PROV_ATTR_TIME] = time
        ProvRelation.add_attributes(self, attributes, extra_attributes)


#  ## Component 2: Derivations

class ProvDerivation(ProvRelation):
    def get_type(self):
        return PROV_REC_DERIVATION

    def get_prov_type(self):
        return PROV['Derivation']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        generatedEntity = self.required_attribute(attributes, PROV_ATTR_GENERATED_ENTITY, QName)
        usedEntity = self.required_attribute(attributes, PROV_ATTR_USED_ENTITY, QName)
        #  Optional attributes
        activity = self.optional_attribute(attributes, PROV_ATTR_ACTIVITY, QName)
        generation = self.optional_attribute(attributes, PROV_ATTR_GENERATION, QName)
        usage = self.optional_attribute(attributes, PROV_ATTR_USAGE, QName)

        attributes = OrderedDict()
        attributes[PROV_ATTR_GENERATED_ENTITY] = generatedEntity
        attributes[PROV_ATTR_USED_ENTITY] = usedEntity
        attributes[PROV_ATTR_ACTIVITY] = activity
        attributes[PROV_ATTR_GENERATION] = generation
        attributes[PROV_ATTR_USAGE] = usage
        ProvRelation.add_attributes(self, attributes, extra_attributes)


#  ## Component 3: Agents, Responsibility, and Influence

class ProvAgent(ProvElement):
    def get_type(self):
        return PROV_REC_AGENT

    def get_prov_type(self):
        return PROV['Agent']


class ProvAttribution(ProvRelation):
    def get_type(self):
        return PROV_REC_ATTRIBUTION

    def get_prov_type(self):
        return PROV['Attribution']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        entity = self.required_attribute(attributes, PROV_ATTR_ENTITY, QName)
        agent = self.required_attribute(attributes, PROV_ATTR_AGENT, QName)

        attributes = OrderedDict()
        attributes[PROV_ATTR_ENTITY] = entity
        attributes[PROV_ATTR_AGENT] = agent
        ProvRelation.add_attributes(self, attributes, extra_attributes)


class ProvAssociation(ProvRelation):
    def get_type(self):
        return PROV_REC_ASSOCIATION

    def get_prov_type(self):
        return PROV['Association']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        activity = self.required_attribute(attributes, PROV_ATTR_ACTIVITY, QName)
        #  Optional attributes
        agent = self.optional_attribute(attributes, PROV_ATTR_AGENT, QName)
        plan = self.optional_attribute(attributes, PROV_ATTR_PLAN, QName)

        attributes = OrderedDict()
        attributes[PROV_ATTR_ACTIVITY] = activity
        attributes[PROV_ATTR_AGENT] = agent
        attributes[PROV_ATTR_PLAN] = plan
        ProvRelation.add_attributes(self, attributes, extra_attributes)


class ProvDelegation(ProvRelation):
    def get_type(self):
        return PROV_REC_DELEGATION

    def get_prov_type(self):
        return PROV['Delegation']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        delegate = self.required_attribute(attributes, PROV_ATTR_DELEGATE, QName)
        responsible = self.required_attribute(attributes, PROV_ATTR_RESPONSIBLE, QName)
        #  Optional attributes
        activity = self.optional_attribute(attributes, PROV_ATTR_ACTIVITY, QName)

        attributes = OrderedDict()
        attributes[PROV_ATTR_DELEGATE] = delegate
        attributes[PROV_ATTR_RESPONSIBLE] = responsible
        attributes[PROV_ATTR_ACTIVITY] = activity
        ProvRelation.add_attributes(self, attributes, extra_attributes)


class ProvInfluence(ProvRelation):
    def get_type(self):
        return PROV_REC_INFLUENCE

    def get_prov_type(self):
        return PROV['Influence']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        influencee = self.required_attribute(attributes, PROV_ATTR_INFLUENCEE, QName)
        influencer = self.required_attribute(attributes, PROV_ATTR_INFLUENCER, QName)

        attributes = OrderedDict()
        attributes[PROV_ATTR_INFLUENCEE] = influencee
        attributes[PROV_ATTR_INFLUENCER] = influencer
        ProvRelation.add_attributes(self, attributes, extra_attributes)


#  ## Component 4: Bundles

#  See below

#  ## Component 5: Alternate Entities

class ProvSpecialization(ProvRelation):
    def get_type(self):
        return PROV_REC_SPECIALIZATION

    def get_prov_type(self):
        return PROV['Specialization']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        specificEntity = self.required_attribute(attributes, PROV_ATTR_SPECIFIC_ENTITY, QName)
        generalEntity = self.required_attribute(attributes, PROV_ATTR_GENERAL_ENTITY, QName)

        attributes = OrderedDict()
        attributes[PROV_ATTR_SPECIFIC_ENTITY] = specificEntity
        attributes[PROV_ATTR_GENERAL_ENTITY] = generalEntity
        ProvRelation.add_attributes(self, attributes, extra_attributes)


class ProvAlternate(ProvRelation):
    def get_type(self):
        return PROV_REC_ALTERNATE

    def get_prov_type(self):
        return PROV['Alternate']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        alternate1 = self.required_attribute(attributes, PROV_ATTR_ALTERNATE1, QName)
        alternate2 = self.required_attribute(attributes, PROV_ATTR_ALTERNATE2, QName)

        attributes = OrderedDict()
        attributes[PROV_ATTR_ALTERNATE1] = alternate1
        attributes[PROV_ATTR_ALTERNATE2] = alternate2
        ProvRelation.add_attributes(self, attributes, extra_attributes)


class ProvMention(ProvSpecialization):
    def get_type(self):
        return PROV_REC_MENTION

    def get_prov_type(self):
        return PROV['Mention']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        specificEntity = self.required_attribute(attributes, PROV_ATTR_SPECIFIC_ENTITY, QName)
        generalEntity = self.required_attribute(attributes, PROV_ATTR_GENERAL_ENTITY, QName)
        bundle = self.required_attribute(attributes, PROV_ATTR_BUNDLE, QName)

        attributes = OrderedDict()
        attributes[PROV_ATTR_SPECIFIC_ENTITY] = specificEntity
        attributes[PROV_ATTR_GENERAL_ENTITY] = generalEntity
        attributes[PROV_ATTR_BUNDLE] = bundle
        ProvRelation.add_attributes(self, attributes, extra_attributes)


#  ## Component 6: Collections

class ProvMembership(ProvRelation):
    def get_type(self):
        return PROV_REC_MEMBERSHIP

    def get_prov_type(self):
        return PROV['Membership']

    def add_attributes(self, attributes, extra_attributes):
        #  Required attributes
        collection = self.required_attribute(attributes, PROV_ATTR_COLLECTION, QName)
        entity = self.required_attribute(attributes, PROV_ATTR_ENTITY, QName)

        attributes = OrderedDict()
        attributes[PROV_ATTR_COLLECTION] = collection
        attributes[PROV_ATTR_ENTITY] = entity
        ProvRelation.add_attributes(self, attributes, extra_attributes)

#  Class mappings from PROV record type
PROV_REC_CLS = {
    PROV_REC_ENTITY:         ProvEntity,
    PROV_REC_ACTIVITY:       ProvActivity,
    PROV_REC_GENERATION:     ProvGeneration,
    PROV_REC_USAGE:          ProvUsage,
    PROV_REC_COMMUNICATION:  ProvCommunication,
    PROV_REC_START:          ProvStart,
    PROV_REC_END:            ProvEnd,
    PROV_REC_INVALIDATION:   ProvInvalidation,
    PROV_REC_DERIVATION:     ProvDerivation,
    PROV_REC_AGENT:          ProvAgent,
    PROV_REC_ATTRIBUTION:    ProvAttribution,
    PROV_REC_ASSOCIATION:    ProvAssociation,
    PROV_REC_DELEGATION:     ProvDelegation,
    PROV_REC_INFLUENCE:      ProvInfluence,
    PROV_REC_SPECIALIZATION: ProvSpecialization,
    PROV_REC_ALTERNATE:      ProvAlternate,
    PROV_REC_MENTION:        ProvMention,
    PROV_REC_MEMBERSHIP:     ProvMembership,
}


DEFAULT_NAMESPACES = {'prov': PROV, 'xsd': XSD}


#  Bundle
class NamespaceManager(dict):
    def __init__(self, namespaces=None, default=None, parent=None):
        self._default_namespaces = DEFAULT_NAMESPACES
        self.update(self._default_namespaces)
        self._namespaces = {}

        if default is not None:
            self.set_default_namespace(default)
        else:
            self._default = None
        self.parent = parent
        #  TODO check if default is in the default namespaces
        self._anon_id_count = 0
        self._rename_map = {}
        self.add_namespaces(namespaces)

    def get_namespace(self, uri):
        for namespace in self.values():
            if uri == namespace._uri:
                return namespace
        return None

    def get_registered_namespaces(self):
        return self._namespaces.values()

    def set_default_namespace(self, uri):
        self._default = Namespace('', uri)
        self[''] = self._default

    def get_default_namespace(self):
        return self._default

    def add_namespace(self, namespace):
        if namespace in self.values():
            #  no need to do anything
            return
        if namespace in self._rename_map:
            #  already renamed and added
            return

        prefix = namespace.get_prefix()
        if prefix in self:
            #  Conflicting prefix
            new_prefix = self._get_unused_prefix(prefix)
            new_namespace = Namespace(new_prefix, namespace.get_uri())
            self._rename_map[namespace] = new_namespace
            prefix = new_prefix
            namespace = new_namespace
        self._namespaces[prefix] = namespace
        self[prefix] = namespace
        return namespace

    def add_namespaces(self, namespaces):
        if namespaces:
            for prefix, uri in namespaces.items():
                ns = Namespace(prefix, uri)
                self.add_namespace(ns)

    def get_valid_identifier(self, identifier):
        if not identifier:
            return None
        if isinstance(identifier, Identifier):
            if isinstance(identifier, QName):
                #  Register the namespace if it has not been registered before
                namespace = identifier._namespace
                prefix = namespace.get_prefix()
                if prefix in self and self[prefix] == namespace:
                    # No need to add the namespace
                    existing_ns = self[prefix]
                    if existing_ns is namespace:
                        return identifier
                    else:
                        return existing_ns[identifier._localpart]  # reuse the existing namespace
                else:
                    ns = self.add_namespace(deepcopy(namespace))  # Do not reuse the namespace object
                    return ns[identifier._localpart] # minting the same Qualified Name from the namespace's copy
            else:
                #  return the original identifier
                return identifier
        elif isinstance(identifier, (str, unicode)):
            if identifier.startswith('_:'):
                return None
            elif ':' in identifier:
                #  check if the identifier contains a registered prefix
                prefix, local_part = identifier.split(':', 1)
                if prefix in self:
                    #  return a new QName
                    return self[prefix][local_part]
                else:
                    #  treat as a URI (with the first part as its scheme)
                    #  check if the URI can be compacted
                    for namespace in self.values():
                        if identifier.startswith(namespace.get_uri()):
                            #  create a QName with the namespace
                            return namespace[identifier.replace(namespace.get_uri(), '')]
                    if self.parent is not None:
                        # try the parent namespace manager
                        return self.parent.get_valid_identifier(identifier)
                    else:
                        #  return an Identifier with the given URI
                        return Identifier(identifier)
            elif self._default:
                #  create and return an identifier in the default namespace
                return self._default[identifier]
            else:
                # This is not an identifier
                return None

    def get_anonymous_identifier(self, local_prefix='id'):
        self._anon_id_count += 1
        return Identifier('_:%s%d' % (local_prefix, self._anon_id_count))

    def _get_unused_prefix(self, original_prefix):
        if original_prefix not in self:
            return original_prefix
        count = 1
        while True:
            new_prefix = '_'.join((original_prefix, unicode(count)))
            if new_prefix in self:
                count += 1
            else:
                return new_prefix


class ProvBundle(object):
    def __init__(self, identifier=None, bundle=None, namespaces=None):
        #  Initializing bundle-specific attributes
        self._identifier = identifier
        self._records = list()
        self._id_map = defaultdict(list)
        self._bundles = dict()
        self._namespaces = NamespaceManager(namespaces, parent=(bundle._namespaces if bundle is not None else None))

    def get_identifier(self):
        return self._identifier

    #  Bundle configurations
    def set_default_namespace(self, uri):
        self._namespaces.set_default_namespace(uri)

    def get_default_namespace(self):
        return self._namespaces.get_default_namespace()

    def add_namespace(self, namespace_or_prefix, uri=None):
        if uri is None:
            self._namespaces.add_namespace(namespace_or_prefix)
        else:
            self._namespaces.add_namespace(Namespace(namespace_or_prefix, uri))

    def get_registered_namespaces(self):
        return self._namespaces.get_registered_namespaces()

    def valid_identifier(self, identifier):
        return self._namespaces.get_valid_identifier(identifier)

    def get_anon_id(self, record):
        #  TODO Implement a dict of self-generated anon ids for records without identifier
        return self._namespaces.get_anonymous_identifier()

    def get_records(self, class_or_type_or_tuple=None):
        results = list(self._records)
        if class_or_type_or_tuple:
            return filter(lambda rec: isinstance(rec, class_or_type_or_tuple), results)
        else:
            return results

    def get_record(self, identifier):
        # TODO: This will not work with the new _id_map, which is now a map of (QName, list(ProvRecord))
        if identifier is None:
            return None
        valid_id = self.valid_identifier(identifier)
        try:
            return self._id_map[valid_id]
        except:
            #  looking up the parent bundle
            if self._bundle is not None:
                return self._bundle.get_record(valid_id)
            else:
                return None

    def get_bundle(self, identifier):
        try:
            valid_id = self.valid_identifier(identifier)
            return self._bundles[valid_id]
        except:
            #  looking up the parent bundle
            if self._bundle is not None:
                return self._bundle.get_bundle(valid_id)
            else:
                return None

    #  PROV-JSON serialization/deserialization
    class JSONEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, ProvBundle):
                return o._encode_JSON_container()
            else:
                #  Use the default encoder instead
                return json.JSONEncoder.default(self, o)

    class JSONDecoder(json.JSONDecoder):
        def decode(self, s):
            json_container = json.JSONDecoder.decode(self, s)
            result = ProvDocument()
            result._decode_JSON_container(json_container)
            return result

    def _encode_json_representation(self, value):
        try:
            return value.json_representation()
        except AttributeError:
            if isinstance(value, datetime.datetime):
                return {'$': value.isoformat(), 'type': u'xsd:dateTime'}
            else:
                return value

    def _decode_json_representation(self, literal):
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

    def _encode_JSON_container(self):
        container = defaultdict(dict)

        if self.is_document():  # This is a document
            prefixes = {}
            for namespace in self._namespaces.get_registered_namespaces():
                prefixes[namespace.get_prefix()] = namespace.get_uri()
            if self._namespaces._default:
                prefixes['default'] = self._namespaces._default.get_uri()
            if prefixes:
                container[u'prefix'] = prefixes

        id_generator = AnonymousIDGenerator()
        real_or_anon_id = lambda record: record._identifier if record._identifier else id_generator.get_anon_id(record)

        for record in self._records:
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
                    value_json = self._encode_json_representation(value)
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
            container[rec_label][identifier] = record_json

            for bundle_id, bundle in self._bundles.items():
                #  encoding the sub-bundle
                bundle_json = bundle._encode_JSON_container()
                container['bundle'][unicode(bundle_id)] = bundle_json

        return container

    def _decode_JSON_container(self, jc):
        if u'prefix' in jc:
            prefixes = jc[u'prefix']
            for prefix, uri in prefixes.items():
                if prefix != 'default':
                    self.add_namespace(Namespace(prefix, uri))
                else:
                    self.set_default_namespace(uri)
        records = sorted([(PROV_RECORD_IDS_MAP[rec_type], rec_id, jc[rec_type][rec_id])
                          for rec_type in jc if rec_type != u'prefix'
                          for rec_id in jc[rec_type]],
                         key=lambda tuple_rec: tuple_rec[0])

        record_map = {}
        _parse_attr_value = lambda value: record_map[value] if (isinstance(value, basestring) and value in record_map) else self._decode_json_representation(value)
        #  Create all the records before setting their attributes
        for (record_type, identifier, content) in records:
            if record_type == PROV_REC_BUNDLE:
                bundle = self.bundle(identifier)
                bundle._decode_JSON_container(content)
            else:
                record_map[identifier] = self.add_record(record_type, identifier, None, None)
        for (record_type, identifier, attributes) in records:
            if record_type != PROV_REC_BUNDLE:
                record = record_map[identifier]

                if hasattr(attributes, 'items'):  # it is a dict
                    #  There is only one element, create a singleton list
                    elements = [attributes]
                else:
                    # expect it to be a list of dictionaries
                    elements = attributes

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
                                    if record.get_type() == PROV_REC_MEMBERSHIP and attr_id == PROV_ATTR_ENTITY:
                                        # This is a membership relation with multiple entities
                                        # HACK: create multiple membership relations, one for each entity
                                        membership_extra_members = value[1:]  # Store all the extra entities
                                        value = value[0]  # Create the first membership relation as normal for the first entity
                                    else:
                                        error_msg = 'The prov package does not support PROV attributes having multiple values.'
                                        logger.error(error_msg)
                                        raise ProvException(error_msg)
                            prov_attributes[attr_id] = _parse_attr_value(value)
                        else:
                            attr_id = self.valid_identifier(attr)
                            if isinstance(value, list):
                                #  Parsing multi-value attribute
                                extra_attributes.extend((attr_id, self._decode_json_representation(value_single)) for value_single in value)
                            else:
                                #  add the single-value attribute
                                extra_attributes.append((attr_id, self._decode_json_representation(value)))
                    record.add_attributes(prov_attributes, extra_attributes)
                    # HACK: creating extra (unidentified) membership relations
                    if membership_extra_members:
                        collection = prov_attributes[PROV_ATTR_COLLECTION]
                        for member in membership_extra_members:
                            self.membership(collection, _parse_attr_value(member), None, extra_attributes)

    #  Miscellaneous functions
    def is_document(self):
        return False

    def is_bundle(self):
        return True

    def get_provn(self, _indent_level=0):
        indentation = '' + ('  ' * _indent_level)
        newline = '\n' + ('  ' * (_indent_level + 1))

        #  if this is the document, start the document; otherwise, start the bundle
        lines = ['document'] if self.is_document() else ['bundle %s' % self._identifier]

        default_namespace = self._namespaces.get_default_namespace()
        if default_namespace:
            lines.append('default <%s>' % default_namespace.get_uri())

        registered_namespaces = self._namespaces.get_registered_namespaces()
        if registered_namespaces:
            lines.extend(['prefix %s <%s>' % (namespace.get_prefix(), namespace.get_uri()) for namespace in registered_namespaces])

        if default_namespace or registered_namespaces:
            #  a blank line between the prefixes and the assertions
            lines.append('')

        #  adding all the records
        lines.extend([record.get_provn(_indent_level + 1) for record in self._records])
        provn_str = newline.join(lines) + '\n'
        #  closing the structure
        provn_str += indentation + ('endDocument' if self.is_document() else 'endBundle')
        return provn_str

    def get_provjson(self, **kw):
        """Return the `PROV-JSON <http://www.w3.org/Submission/prov-json/>`_ representation for the bundle/document.

        Parameters for `json.dumps <http://docs.python.org/2/library/json.html#json.dumps>`_ like `indent=4` can be also passed as keyword arguments.
        """
        # Prevent overwriting the encoder class
        if 'cls' in kw:
            del kw['cls']
        json_content = json.dumps(self, cls=ProvBundle.JSONEncoder, **kw)
        return json_content

    @staticmethod
    def from_provjson(json_content, **kw):
        """Construct the bundle/document from the given `PROV-JSON <http://www.w3.org/Submission/prov-json/>`_
        representation.

        Parameters for `json.loads <http://docs.python.org/2/library/json.html#json.loads>`_ can be also passed as
        keyword arguments.
        """
        # Prevent overwriting the decoder class
        if 'cls' in kw:
            del kw['cls']
        return json.loads(json_content, cls=ProvBundle.JSONDecoder, **kw)

    def __eq__(self, other):
        if not isinstance(other, ProvBundle):
            return False
        other_records = set(other.get_records())
        this_records = set(self.get_records())
        if len(this_records) != len(other_records):
            return False
        #  check if all records for equality
        for record_a in this_records:
            #  Manually look for the record
            found = False
            for record_b in other_records:
                if record_a == record_b:
                    other_records.remove(record_b)
                    found = True
                    break
            if not found:
                logger.debug("Equality (ProvBundle): Could not find this record: %s", unicode(record_a))
                return False
        return True

    #  Provenance statements
    def _add_record(self, record):
        # TODO Keep bundles and records separated
        # TODO Build a map of records (by their identifier for fast lookup)
        self._records.append(record)

    def add_record(self, record_type, identifier, attributes=None, other_attributes=None):
        new_record = PROV_REC_CLS[record_type](self, self.valid_identifier(identifier), attributes, other_attributes)
        self._add_record(new_record)
        return new_record

    def entity(self, identifier, other_attributes=None):
        return self.add_record(PROV_REC_ENTITY, identifier, None, other_attributes)

    def activity(self, identifier, startTime=None, endTime=None, other_attributes=None):
        return self.add_record(
            PROV_REC_ACTIVITY, identifier, {
                PROV_ATTR_STARTTIME: _ensure_datetime(startTime),
                PROV_ATTR_ENDTIME: _ensure_datetime(endTime)
            },
            other_attributes
        )

    def generation(self, entity, activity=None, time=None, identifier=None, other_attributes=None):
        return self.add_record(
            PROV_REC_GENERATION, identifier, {
                PROV_ATTR_ENTITY: entity,
                PROV_ATTR_ACTIVITY: activity,
                PROV_ATTR_TIME: _ensure_datetime(time)
            },
            other_attributes
        )

    def usage(self, activity, entity=None, time=None, identifier=None, other_attributes=None):
        return self.add_record(
            PROV_REC_USAGE, identifier, {
                PROV_ATTR_ACTIVITY: activity,
                PROV_ATTR_ENTITY: entity,
                PROV_ATTR_TIME: _ensure_datetime(time)},
            other_attributes
        )

    def start(self, activity, trigger=None, starter=None, time=None, identifier=None, other_attributes=None):
        return self.add_record(
            PROV_REC_START, identifier, {
                PROV_ATTR_ACTIVITY: activity,
                PROV_ATTR_TRIGGER: trigger,
                PROV_ATTR_STARTER: starter,
                PROV_ATTR_TIME: _ensure_datetime(time)
            },
            other_attributes
        )

    def end(self, activity, trigger=None, ender=None, time=None, identifier=None, other_attributes=None):
        return self.add_record(
            PROV_REC_END, identifier, {
                PROV_ATTR_ACTIVITY: activity,
                PROV_ATTR_TRIGGER: trigger,
                PROV_ATTR_ENDER: ender,
                PROV_ATTR_TIME: _ensure_datetime(time)
            },
            other_attributes
        )

    def invalidation(self, entity, activity=None, time=None, identifier=None, other_attributes=None):
        return self.add_record(
            PROV_REC_INVALIDATION, identifier, {
                PROV_ATTR_ENTITY: entity,
                PROV_ATTR_ACTIVITY: activity,
                PROV_ATTR_TIME: _ensure_datetime(time)
            },
            other_attributes
        )

    def communication(self, informed, informant, identifier=None, other_attributes=None):
        return self.add_record(
            PROV_REC_COMMUNICATION, identifier, {
                PROV_ATTR_INFORMED: informed,
                PROV_ATTR_INFORMANT: informant
            },
            other_attributes
        )

    def agent(self, identifier, other_attributes=None):
        return self.add_record(PROV_REC_AGENT, identifier, None, other_attributes)

    def attribution(self, entity, agent, identifier=None, other_attributes=None):
        return self.add_record(
            PROV_REC_ATTRIBUTION, identifier, {
                PROV_ATTR_ENTITY: entity,
                PROV_ATTR_AGENT: agent
            },
            other_attributes
        )

    def association(self, activity, agent=None, plan=None, identifier=None, other_attributes=None):
        return self.add_record(
            PROV_REC_ASSOCIATION, identifier, {
                PROV_ATTR_ACTIVITY: activity,
                PROV_ATTR_AGENT: agent,
                PROV_ATTR_PLAN: plan
            },
            other_attributes
        )

    def delegation(self, delegate, responsible, activity=None, identifier=None, other_attributes=None):
        return self.add_record(
            PROV_REC_DELEGATION, identifier, {
                PROV_ATTR_DELEGATE: delegate,
                PROV_ATTR_RESPONSIBLE: responsible,
                PROV_ATTR_ACTIVITY: activity
            },
            other_attributes
        )

    def influence(self, influencee, influencer, identifier=None, other_attributes=None):
        return self.add_record(
            PROV_REC_INFLUENCE, identifier, {
                PROV_ATTR_INFLUENCEE: influencee,
                PROV_ATTR_INFLUENCER: influencer
            },
            other_attributes
        )

    def derivation(self, generatedEntity, usedEntity, activity=None, generation=None, usage=None,
                   identifier=None, other_attributes=None):
        attributes = {PROV_ATTR_GENERATED_ENTITY: generatedEntity,
                      PROV_ATTR_USED_ENTITY: usedEntity,
                      PROV_ATTR_ACTIVITY: activity,
                      PROV_ATTR_GENERATION: generation,
                      PROV_ATTR_USAGE: usage}
        return self.add_record(PROV_REC_DERIVATION, identifier, attributes, other_attributes)

    def revision(self, generatedEntity, usedEntity, activity=None, generation=None, usage=None,
                 identifier=None, other_attributes=None):
        record = self.derivation(generatedEntity, usedEntity, activity, generation, usage, identifier, other_attributes)
        record.add_asserted_type(PROV['Revision'])
        return record

    def quotation(self, generatedEntity, usedEntity, activity=None, generation=None, usage=None,
                  identifier=None, other_attributes=None):
        record = self.derivation(generatedEntity, usedEntity, activity, generation, usage, identifier, other_attributes)
        record.add_asserted_type(PROV['Quotation'])
        return record

    def primary_source(self, generatedEntity, usedEntity, activity=None, generation=None, usage=None,
                       identifier=None, other_attributes=None):
        record = self.derivation(generatedEntity, usedEntity, activity, generation, usage, identifier, other_attributes)
        record.add_asserted_type(PROV['PrimarySource'])
        return record

    def specialization(self, specificEntity, generalEntity):
        return self.add_record(
            PROV_REC_SPECIALIZATION, None, {
                PROV_ATTR_SPECIFIC_ENTITY: specificEntity,
                PROV_ATTR_GENERAL_ENTITY: generalEntity
            }
        )

    def alternate(self, alternate1, alternate2):
        return self.add_record(
            PROV_REC_ALTERNATE, None, {
                PROV_ATTR_ALTERNATE1: alternate1,
                PROV_ATTR_ALTERNATE2: alternate2
            },
        )

    def mention(self, specificEntity, generalEntity, bundle,):
        return self.add_record(
            PROV_REC_MENTION, None, {
                PROV_ATTR_SPECIFIC_ENTITY: specificEntity,
                PROV_ATTR_GENERAL_ENTITY: generalEntity,
                PROV_ATTR_BUNDLE: bundle
            }
        )

    def collection(self, identifier, other_attributes=None):
        record = self.add_record(PROV_REC_ENTITY, identifier, None, other_attributes)
        record.add_asserted_type(PROV['Collection'])
        return record

    def membership(self, collection, entity):
        return self.add_record(
            PROV_REC_MEMBERSHIP, None, {
                PROV_ATTR_COLLECTION: collection,
                PROV_ATTR_ENTITY: entity
            }
        )

    #  Aliases
    wasGeneratedBy = generation
    used = usage
    wasStartedBy = start
    wasEndedBy = end
    wasInvalidatedBy = invalidation
    wasInformedBy = communication
    wasAttributedTo = attribution
    wasAssociatedWith = association
    actedOnBehalfOf = delegation
    wasInfluencedBy = influence
    wasDerivedFrom = derivation
    wasRevisionOf = revision
    wasQuotedFrom = quotation
    hadPrimarySource = primary_source
    alternateOf = alternate
    specializationOf = specialization
    mentionOf = mention
    hadMember = membership


class ProvDocument(ProvBundle):
    def __init__(self, namespaces=None):
        ProvBundle.__init__(self, None, namespaces)

    def is_document(self):
        return True

    def is_bundle(self):
        return False

    def add_bundle(self, bundle, identifier=None):
        """Add a bundle to the current document
        """
        if identifier is None:
            identifier = bundle.get_identifier()

        if not identifier:
            raise ProvException(u"The added bundle has no identifier")

        valid_id = self.valid_identifier(identifier)
        bundle._identifier = valid_id

        if valid_id in self._bundles:
            raise ProvException(u"A bundle with that identifier already exists")

        if len(bundle._bundles) > 0:
            raise ProvException(u"A bundle may not contain bundles")

        self._bundles[valid_id] = bundle

        # TODO Set parent namespace for the bundle

        bundle._bundle = self

    def bundle(self, identifier):
        if identifier is None:
            raise ProvException('An identifier is required. Cannot create an unnamed bundle.')
        valid_id = self.valid_identifier(identifier)
        b = ProvBundle()
        self.add_bundle(b, valid_id)
        return b

