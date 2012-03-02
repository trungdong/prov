import logging
import datetime
import json
import re
from collections import OrderedDict, defaultdict
logger = logging.getLogger(__name__)

# Constants
PROV_REC_ENTITY                 = 1
PROV_REC_ACTIVITY               = 2
PROV_REC_AGENT                  = 3
PROV_REC_NOTE                   = 9
PROV_REC_ACCOUNT                = 10
PROV_REC_GENERATION             = 11
PROV_REC_USAGE                  = 12
PROV_REC_ACTIVITY_ASSOCIATION   = 13
PROV_REC_START                  = 14
PROV_REC_END                    = 15
PROV_REC_RESPONSIBILITY         = 16
PROV_REC_DERIVATION             = 17
PROV_REC_ALTERNATE              = 18
PROV_REC_SPECIALIZATION         = 19
PROV_REC_ANNOTATION             = 99

PROV_RECORD_TYPES = (
    (PROV_REC_ENTITY,               u'Entity'),
    (PROV_REC_ACTIVITY,             u'Activity'),
    (PROV_REC_AGENT,                u'Agent'),
    (PROV_REC_NOTE,                 u'Note'),
    (PROV_REC_ACCOUNT,              u'Account'),
    (PROV_REC_GENERATION,           u'Generation'),
    (PROV_REC_USAGE,                u'Usage'),
    (PROV_REC_ACTIVITY_ASSOCIATION, u'ActivityAssociation'),
    (PROV_REC_START,                u'Start'),
    (PROV_REC_END,                  u'End'),
    (PROV_REC_RESPONSIBILITY,       u'Responsibility'),
    (PROV_REC_DERIVATION,           u'Derivation'),
    (PROV_REC_ALTERNATE,            u'Alternate'),
    (PROV_REC_SPECIALIZATION,       u'Specialization'),
    (PROV_REC_ANNOTATION,           u'Annotation'),
)

PROV_ASN_MAP = {
    PROV_REC_ENTITY:               u'entity',
    PROV_REC_ACTIVITY:             u'activity',
    PROV_REC_AGENT:                u'agent',
    PROV_REC_NOTE:                 u'note',
    PROV_REC_ACCOUNT:              u'account',
    PROV_REC_GENERATION:           u'wasGeneratedBy',
    PROV_REC_USAGE:                u'used',
    PROV_REC_ACTIVITY_ASSOCIATION: u'wasAssociatedWith',
    PROV_REC_START:                u'wasStartedBy',
    PROV_REC_END:                  u'wasEndedBy',
    PROV_REC_RESPONSIBILITY:       u'actedOnBehalfOf',
    PROV_REC_DERIVATION:           u'wasDerivedFrom',
    PROV_REC_ALTERNATE:            u'alternateOf',
    PROV_REC_SPECIALIZATION:       u'specializationOf',
    PROV_REC_ANNOTATION:           u'hasAnnotation',
}

PROV_ATTR_RECORD                = 0
PROV_ATTR_ENTITY                = 1
PROV_ATTR_ACTIVITY              = 2
PROV_ATTR_AGENT                 = 3
PROV_ATTR_NOTE                  = 4
PROV_ATTR_PLAN                  = 5
PROV_ATTR_SUBORDINATE           = 6
PROV_ATTR_RESPONSIBLE           = 7
PROV_ATTR_GENERATED_ENTITY      = 8
PROV_ATTR_USED_ENTITY           = 9
PROV_ATTR_GENERATION            = 10
PROV_ATTR_USAGE                 = 11
PROV_ATTR_ALTERNATE             = 12
PROV_ATTR_SPECIALIZATION        = 13
# Literal properties
PROV_ATTR_TIME                  = 100
PROV_ATTR_STARTTIME             = 101
PROV_ATTR_ENDTIME               = 102

PROV_RECORD_ATTRIBUTES = (
    # Relations properties
    (PROV_ATTR_RECORD, u'prov:record'),
    (PROV_ATTR_ENTITY, u'prov:entity'),
    (PROV_ATTR_ACTIVITY, u'prov:activity'),
    (PROV_ATTR_AGENT, u'prov:agent'),
    (PROV_ATTR_NOTE, u'prov:note'),
    (PROV_ATTR_PLAN, u'prov:plan'),
    (PROV_ATTR_SUBORDINATE, u'prov:subordinate'),
    (PROV_ATTR_RESPONSIBLE, u'prov:responsible'),
    (PROV_ATTR_GENERATED_ENTITY, u'prov:generatedEntity'),
    (PROV_ATTR_USED_ENTITY, u'prov:usedEntity'),
    (PROV_ATTR_GENERATION, u'prov:generation'),
    (PROV_ATTR_USAGE, u'prov:usage'),
    (PROV_ATTR_ALTERNATE, u'prov:alternate'),
    (PROV_ATTR_SPECIALIZATION, u'prov:specialization'),
    # Literal properties
    (PROV_ATTR_TIME, u'prov:time'),
    (PROV_ATTR_STARTTIME, u'prov:startTime'),
    (PROV_ATTR_ENDTIME, u'prov:endTime'),
)

PROV_ATTRIBUTE_LITERALS = set([PROV_ATTR_TIME, PROV_ATTR_STARTTIME, PROV_ATTR_ENDTIME])

PROV_RECORD_IDS_MAP = dict((PROV_ASN_MAP[rec_type_id], rec_type_id) for rec_type_id in PROV_ASN_MAP)
PROV_ID_ATTRIBUTES_MAP = dict((prov_id, attribute) for (prov_id, attribute) in PROV_RECORD_ATTRIBUTES)
PROV_ATTRIBUTES_ID_MAP = dict((attribute, prov_id) for (prov_id, attribute) in PROV_RECORD_ATTRIBUTES)

# Datatypes
def parse_xsd_dateTime(s):
    """Returns datetime or None."""
    m = re.match(""" ^
    (?P<year>-?[0-9]{4}) - (?P<month>[0-9]{2}) - (?P<day>[0-9]{2})
    T (?P<hour>[0-9]{2}) : (?P<minute>[0-9]{2}) : (?P<second>[0-9]{2})
    (?P<microsecond>\.[0-9]{1,6})?
    (?P<tz>
      Z | (?P<tz_hr>[-+][0-9]{2}) : (?P<tz_min>[0-9]{2})
    )?
    $ """, s, re.X)
    if m is not None:
        values = m.groupdict()
    if values["microsecond"] is None:
        values["microsecond"] = 0
    else:
        values["microsecond"] = values["microsecond"][1:]
        values["microsecond"] += "0" * (6 - len(values["microsecond"]))
    values = dict((k, int(v)) for k, v in values.iteritems()
                  if not k.startswith("tz"))
    try:
        return datetime.datetime(**values)
    except ValueError:
        pass
    return None
    
class Literal(object):
    def __init__(self, value, datatype):
        self._value = value
        self._datatype = datatype
        
    def __str__(self):
        return '%s %%%% %s' % (str(self._value), str(self._datatype))
    
    def get_value(self):
        return self._value
    
    def get_datatype(self):
        return self._datatype
    
    def json_representation(self):
        return [str(self._value), str(self._datatype)]


class Identifier(object):
    def __init__(self, uri):
        self._uri = uri
        
    def get_uri(self):
        return self._uri
    
    def __str__(self):
        return self._uri
    
    def __eq__(self, other):
        return self.get_uri() == other.get_uri() if isinstance(other, Identifier) else False
    
    def __hash__(self):
        return hash(self.get_uri())
    
    def json_representation(self):
        return [str(self), u'xsd:anyURI']
    

class QName(Identifier):
    def __init__(self, namespace, localpart):
        self._namespace = namespace
        self._localpart = localpart
        
    def get_namespace(self):
        return self._namespace
    
    def get_localpart(self):
        return self._localpart
    
    def get_uri(self):
        return ''.join([self._namespace._uri, self._localpart])
    
    def __str__(self):
        return ':'.join([self._namespace._prefix, self._localpart])
    
    def json_representation(self):
        return [str(self), u'xsd:QName']
    

class Namespace(object):
    def __init__(self, prefix, uri):
        self._prefix = prefix
        self._uri = uri

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
            return QName(self, uri[len(self._uri),])
        else:
            return None
        
    def __eq__(self, other):
        return (self._uri == other._uri and self._prefix == other._prefix) if isinstance(other, Namespace) else False
    
    def __getitem__(self, localpart):
        return QName(self, localpart)
    
XSD = Namespace("xsd",'http://www.w3.org/2001/XMLSchema-datatypes#')
PROV = Namespace("prov",'http://www.w3.org/ns/prov-dm/')
    
# Exceptions
class ProvException(Exception):
    """Base class for exceptions in this module."""
    pass

# PROV records
class ProvRecord(object):
    """Base class for PROV _records."""
    def __init__(self, container, identifier, attributes=None, other_attributes=None):
        self._container = container
        self._identifier = identifier
        self._attributes = None
        self._extra_attributes = None
        if attributes or other_attributes:
            self.add_attributes(attributes, other_attributes)
        
    def get_type(self):
        pass
    
    def get_identifier(self):
        return self._identifier
    
    def add_attributes(self, attributes, extra_attributes):
        if attributes:
            if self._attributes is None:
                self._attributes = attributes
            else:
                self._attributes.update(attributes)
        if extra_attributes:
            if self._extra_attributes is None:
                self._extra_attributes = {}
            self._extra_attributes.update(extra_attributes)
    
    def get_attributes(self):
        return (self._attributes, self._extra_attributes)
    
    def required_record_type(self, record, cls):
        if record is None:
            return None
        elif isinstance(record, cls):
            return record
        else:
            # Check for an existing record in the container having the same identifier
            existing_record = self._container.get_record(record)
            if existing_record and isinstance(existing_record, cls):
                return existing_record
            else:
                # TODO added exception details
                raise ProvException
                
    def __eq__(self, other):
        if self.__class__ <> other.__class__:
            return False
        if self._identifier and not (self._identifier == other._identifier):
            return False
        if self._attributes and other._attributes:
            if len(self._attributes) <> len(other._attributes):
                return False
            for attr, value_a in self._attributes.items():
                value_b = other._attributes[attr]
                if isinstance(value_a, ProvRecord) and value_a._identifier:
                    if not (value_a._identifier == value_b._identifier):
                        return False
                elif value_a <> value_b:
                    return False
        elif self._attributes <> other._attributes:
            return False
        if self._extra_attributes <> other._extra_attributes:
            return False
        return True 
          
    def __str__(self):
        items = []
        if self._identifier:
            items.append(str(self._identifier))
        if self._attributes:
            for (attr, value) in self._attributes.items():
                if isinstance(value, ProvRecord):
                    record_id = value.get_identifier()
                    items.append(str(record_id) if record_id is not None else self._container.get_anon_id(value))
                else:
                    # Assuming this is a datetime value
                    items.append(value.isoformat() if value is not None else '')
        
        extra = []
        if self._extra_attributes:
            for (attr, value) in self._extra_attributes.items():
                extra.append('%s="%s"' % (str(attr), '%s %%%% xsd:dateTime' % value.isoformat() if isinstance(value, datetime.datetime) else str(value)))
        
        return '%s(%s, [%s])' % (PROV_ASN_MAP[self.get_type()], ', '.join(items), ', '.join(extra))


class ProvElement(ProvRecord):
    pass


class ProvRelation(ProvRecord):
    pass


class ProvEntity(ProvElement):
    def get_type(self):
        return PROV_REC_ENTITY
    

class ProvActivity(ProvElement):
    def get_type(self):
        return PROV_REC_ACTIVITY
    
    def add_attributes(self, attributes, extra_attributes):
        startTime = attributes[PROV_ATTR_STARTTIME] if PROV_ATTR_STARTTIME in attributes else None 
        endTime = attributes[PROV_ATTR_ENDTIME] if PROV_ATTR_ENDTIME in attributes else None
        if startTime and not isinstance(startTime, datetime.datetime):
            #TODO Raise error value here
            pass
        if endTime and not isinstance(endTime, datetime.datetime):
            #TODO Raise error value here
            pass
        if startTime and endTime and startTime > endTime:
            #TODO Raise logic exception here
            pass
        attributes = OrderedDict()
        attributes[PROV_ATTR_STARTTIME]= startTime
        attributes[PROV_ATTR_ENDTIME]= endTime
            
        ProvElement.add_attributes(self, attributes, extra_attributes)


class ProvAgent(ProvElement):
    def get_type(self):
        return PROV_REC_AGENT

    
class ProvNote(ProvElement):
    def get_type(self):
        return PROV_REC_NOTE

    
class ProvGeneration(ProvRelation):
    def get_type(self):
        return PROV_REC_GENERATION
    
    def add_attributes(self, attributes, extra_attributes):
        # Required attributes
        entity = self.required_record_type(attributes[PROV_ATTR_ENTITY], ProvEntity) 
        activity = self.required_record_type(attributes[PROV_ATTR_ACTIVITY], ProvActivity)
        if not activity or not entity:
            raise ProvException
        # Optional attributes
        time = attributes[PROV_ATTR_TIME] if PROV_ATTR_TIME in attributes else None
        if time and not isinstance(time, datetime.datetime):
            raise ProvException
        
        attributes = OrderedDict()
        attributes[PROV_ATTR_ENTITY] = entity 
        attributes[PROV_ATTR_ACTIVITY] = activity
        attributes[PROV_ATTR_TIME] = time
        
        ProvRelation.add_attributes(self, attributes, extra_attributes)


class ProvUsage(ProvRelation):
    def get_type(self):
        return PROV_REC_USAGE
    
    def add_attributes(self, attributes, extra_attributes):
        # Required attributes
        activity = self.required_record_type(attributes[PROV_ATTR_ACTIVITY], ProvActivity) 
        entity = self.required_record_type(attributes[PROV_ATTR_ENTITY], ProvEntity)
        if not activity or not entity:
            raise ProvException
        # Optional attributes
        time = attributes[PROV_ATTR_TIME] if PROV_ATTR_TIME in attributes else None 
        if time and not isinstance(time, datetime.datetime):
            raise ProvException
        
        attributes = OrderedDict()
        attributes[PROV_ATTR_ACTIVITY]= activity
        attributes[PROV_ATTR_ENTITY]= entity
        attributes[PROV_ATTR_TIME]= time
        ProvRelation.add_attributes(self, attributes, extra_attributes)
    
class ProvActivityAssociation(ProvRelation):
    def get_type(self):
        return PROV_REC_ACTIVITY_ASSOCIATION
    
    def add_attributes(self, attributes, extra_attributes):
        # Required attributes
        activity = self.required_record_type(attributes[PROV_ATTR_ACTIVITY], ProvActivity) 
        agent = self.required_record_type(attributes[PROV_ATTR_AGENT], ProvAgent)
        if not activity or not agent:
            raise ProvException
        # Optional attributes
        plan = self.required_record_type(attributes[PROV_ATTR_PLAN], ProvEntity) if PROV_ATTR_PLAN in attributes else None
        
        attributes = OrderedDict()
        attributes[PROV_ATTR_ACTIVITY]= activity
        attributes[PROV_ATTR_AGENT]= agent
        attributes[PROV_ATTR_PLAN]= plan
        ProvRelation.add_attributes(self, attributes, extra_attributes)
    
class ProvDerivation(ProvRelation):
    def get_type(self):
        return PROV_REC_DERIVATION
    
    def add_attributes(self, attributes, extra_attributes):
        # Required attributes
        generatedEntity = self.required_record_type(attributes[PROV_ATTR_GENERATED_ENTITY], ProvEntity)
        usedEntity = self.required_record_type(attributes[PROV_ATTR_USED_ENTITY], ProvEntity)
        if not generatedEntity or not usedEntity:
            raise ProvException
        # Optional attributes
        #TODO Check for PROV-DM's constraints and the validity of input variables here
        activity = self.required_record_type(attributes[PROV_ATTR_ACTIVITY], ProvActivity) if PROV_ATTR_ACTIVITY in attributes else None 
        generation = self.required_record_type(attributes[PROV_ATTR_GENERATION], ProvGeneration) if PROV_ATTR_GENERATION in attributes else None
        usage = self.required_record_type(attributes[PROV_ATTR_USAGE], ProvUsage) if PROV_ATTR_USAGE in attributes else None
        time = attributes[PROV_ATTR_TIME] if PROV_ATTR_TIME in attributes else None
        if time and not isinstance(time, datetime.datetime):
            raise ProvException
        # Check time's validity usedEntity <= derivation <= generatedEntity
        
        attributes = OrderedDict()
        attributes[PROV_ATTR_GENERATED_ENTITY]= generatedEntity
        attributes[PROV_ATTR_USED_ENTITY]= usedEntity
        #TODO Check for PROV-DM's constraints and the validity of input variables here
        if activity is not None:
            attributes[PROV_ATTR_ACTIVITY]= activity
        if generation is not None:
            attributes[PROV_ATTR_GENERATION] = generation
        if usage is not None:
            attributes[PROV_ATTR_USAGE] = usage
        if time is not None:
            attributes[PROV_ATTR_TIME]= time
        ProvRelation.add_attributes(self, attributes, extra_attributes)
    
PROV_REC_CLS = {
    PROV_REC_ENTITY                 : ProvEntity,
    PROV_REC_ACTIVITY               : ProvActivity,
    PROV_REC_AGENT                  : ProvAgent,
    PROV_REC_NOTE                   : ProvNote,
#    PROV_REC_ACCOUNT                : 10
    PROV_REC_GENERATION             : ProvGeneration,
    PROV_REC_USAGE                  : ProvUsage,
    PROV_REC_ACTIVITY_ASSOCIATION   : ProvActivityAssociation,
#    PROV_REC_START                  = 14
#    PROV_REC_END                    = 15
#    PROV_REC_RESPONSIBILITY         = 16
    PROV_REC_DERIVATION             : ProvDerivation
#    PROV_REC_ALTERNATE              = 18
#    PROV_REC_SPECIALIZATION         = 19
#    PROV_REC_ANNOTATION             = 99
    }


# Container
class NamespaceManager(dict):
    def __init__(self, default_namespaces={}, default=None):
        self._default_namespaces = {}
        self._default_namespaces.update(default_namespaces)
        self._namespaces = {}
        self.update(self._default_namespaces)
        self._default = default
        # TODO check if default is in the default namespaces
        self._anon_id_count = 0 
        self._rename_map = {}
        
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
            # no need to do anything
            return
        if namespace in self._rename_map:
            # already renamed and added
            return
        
        prefix = namespace.get_prefix()
        if prefix in self:
            # Conflicting prefix
            new_prefix = self._get_unused_prefix(prefix)
            new_namespace = Namespace(new_prefix, namespace.get_uri())
            self._rename_map[namespace] = new_namespace
            prefix = new_prefix
            namespace = new_namespace
        self._namespaces[prefix] = namespace
        self[prefix] = namespace
    
    def get_valid_identifier(self, identifier):
        if not identifier:
            return None
        if isinstance(identifier, Identifier):
            if isinstance(identifier, QName):
                # Register the namespace if it has not been registered before
                namespace = identifier.get_namespace() 
                if namespace not in self.values():
                    self.add_namespace(namespace)
            # return the original identifier
            return identifier
        elif isinstance(identifier, (str, unicode)):
            if identifier.startswith('_:'):
                return None
            elif ':' in identifier:
                # check if the identifier contains a registered prefix
                prefix, local_part = identifier.split(':', 1)
                if prefix in self:
                    # return a new QName
                    return self[prefix][local_part]
                else:
                    # treat as a URI (with the first part as its scheme)
                    # check if the URI can be compacted
                    for namespace in self.values():
                        if identifier.startswith(namespace.get_uri()):
                            # create a QName with the namespace
                            return namespace[identifier.replace(namespace.get_uri(), '')] 
                    # return an Identifier with the given URI
                    return Identifier(identifier)
            else:
                # create and return an identifier in the default namespace
                return self._default[identifier]
    
    def get_anonymous_identifier(self, local_prefix='id'):
        self._anon_id_count += 1
        return Identifier('_:%s%d' % (local_prefix, self._anon_id_count))
    
    def _get_unused_prefix(self, original_prefix):
        if original_prefix not in self:
            return original_prefix
        count = 1
        while True:
            new_prefix = '_'.join((original_prefix, count))
            if new_prefix in self:
                count += 1
            else:
                return new_prefix
        

class ProvContainer(object):
    def __init__(self):
        self._records = list()
        self._id_map = dict()
        self._namespaces = NamespaceManager({ PROV.get_prefix(): PROV, XSD.get_prefix(): XSD}, PROV)
        
    # Container configurations
    def set_default_namespace(self, uri):
        self._namespaces.set_default_namespace(uri)
        
    def get_default_namespace(self):
        return self._namespaces.get_default_namespace()
        
    def add_namespace(self, namespace):
        self._namespaces.add_namespace(namespace)

    def get_registered_namespaces(self):
        return self._namespaces.get_registered_namespaces()
        
    def valid_identifier(self, identifier):
        return self._namespaces.get_valid_identifier(identifier) 
        
    def get_anon_id(self, record):
        #TODO Implement a dict of self-generated anon ids for records without identifier
        return self._namespaces.get_anonymous_identifier()
    
    def get_records(self):
        return self._records
    
    def get_record(self, identifier):
        try:
            return self._id_map[identifier]
        except:
            return None
        
    # PROV-JSON serialization/deserialization    
    class JSONEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, ProvContainer):
                return o._encode_JSON_container()
            else:
                # Use the default encoder instead
                return json.JSONEncoder.default(self, o)
            
    class JSONDecoder(json.JSONDecoder):
        def decode(self, s):
            json_container = json.JSONDecoder.decode(self, s)
            result = ProvContainer()
            result._decode_JSON_container(json_container)
            return result
    
    def _encode_json_representation(self, value):
        try:
            return value.json_representation()
        except AttributeError:
            if isinstance(value, datetime.datetime):
                return [value.isoformat(), u'xsd:dateTime']
            else:
                return str(value)
    
    def _decode_json_representation(self, value):
        if isinstance(value, list):
            number = len(value)
            if number == 2:
                datatype = value[1]
                if datatype == u'xsd:anyURI':
                    return Identifier(value[0])
                elif datatype == u'xsd:QName':
                    return self.valid_identifier(value[0])
                elif datatype == u'xsd:dateTime':
                    return parse_xsd_dateTime(value[0])
                else:
                    return Literal(value[0], self.valid_identifier(value[1]))
            else:
                # TODO Deal with multiple values here
                pass
        else:
            return value
        
    def _encode_JSON_container(self):
        container = defaultdict(dict)
        prefixes = {}
        for namespace in self._namespaces.get_registered_namespaces():
            prefixes[namespace.get_prefix()] = namespace.get_uri()
        container[u'prefix'] = prefixes
        ids = {}
        # generating/mapping all record identifiers 
        for record in self._records:
            ids[record] = record._identifier if record._identifier else self.get_anon_id(record)
        for record in self._records:
            rec_type = PROV_ASN_MAP[record.get_type()]
            identifier = str(ids[record])
            
            record_json = {}
            if record._attributes:
                for (attr, value) in record._attributes.items():
                    if isinstance(value, ProvRecord):
                        attr_record_id = ids[value]
                        record_json[PROV_ID_ATTRIBUTES_MAP[attr]] = str(attr_record_id) 
                    elif value is not None:
                        # Assuming this is a datetime value
                        record_json[PROV_ID_ATTRIBUTES_MAP[attr]] = [value.isoformat(), 'xsd:dateTime']
            if record._extra_attributes:
                for (attr, value) in record._extra_attributes.items():
                    record_json[str(attr)] = self._encode_json_representation(value)
            container[rec_type][identifier] = record_json
        
        return container
    
    def _decode_JSON_container(self, jc):
        if u'prefix' in jc:
            prefixes = jc[u'prefix']
            for prefix, uri in prefixes.items():
                self.add_namespace(Namespace(prefix, uri))
        records = sorted([(PROV_RECORD_IDS_MAP[rec_type], rec_id, jc[rec_type][rec_id])
                          for rec_type in jc if rec_type <> u'prefix'
                          for rec_id in jc[rec_type]],
                         key=lambda record: record[0])
        
        record_map = {}
        for (record_type, identifier, _) in records:
            record_map[identifier] = self.add_record(record_type, identifier, None, None)
        for (_, identifier, attributes) in records:
            record = record_map[identifier]
            prov_attributes = {}
            extra_attributes = {}
            # Splitting PROV attributes and the others
            for attr, value in attributes.items():
                if attr in PROV_ATTRIBUTES_ID_MAP:
                    prov_attributes[PROV_ATTRIBUTES_ID_MAP[attr]] = record_map[value] if (isinstance(value, (str, unicode)) and value in record_map) else self._decode_json_representation(value)
                else:
                    extra_attributes[self.valid_identifier(attr)] = self._decode_json_representation(value)
            record.add_attributes(prov_attributes, extra_attributes)
        
    # Miscellaneous functions
    def print_records(self):
        for namespace in self._namespaces.get_registered_namespaces():
            print 'prefix %s <%s>' % (namespace.get_prefix(), namespace.get_uri())
        print ''
        for record in self._records:
            print record
            
    def __eq__(self, other):
        this_records = set(self._records)
        other_records = set(other._records)
        if len(this_records) <> len(other_records):
            return False
        # check if all records for equality
        for record_a in this_records:
            if record_a._identifier:
                record_b = other.get_record(record_a._identifier)
                if record_b: 
                    if record_a == record_b:
                        other_records.remove(record_b)
                        continue
                    else:
                        logger.debug("Inequal PROV records:")
                        logger.debug("%s" % str(record_a))
                        logger.debug("%s" % str(record_b))
                        return False
                else:
                    logger.debug("Could not find a record with this identifier: %s" % str(record_a._identifier))
                    return False
            else:
                # Manually look for the record
                found = False
                for record_b in other_records:
                    if record_a == record_b:
                        other_records.remove(record_b)
                        found = True
                        break
                if not found:
                    logger.debug("Could not find this record: %s" % str(record_a))
                    return False
        return True
            
    # Provenance statements
    def add_record(self, record_type, identifier, attributes=None, other_attributes=None):
        new_record = PROV_REC_CLS[record_type](self, self.valid_identifier(identifier), attributes, other_attributes)
        self._records.append(new_record)
        if new_record._identifier:
            self._id_map[new_record._identifier] = new_record
        return new_record
    
    def add_element(self, record_type, identifier, attributes=None, other_attributes=None):
        return self.add_record(record_type, identifier, attributes, other_attributes)
        
    def entity(self, identifier, other_attributes=None):
        return self.add_element(PROV_REC_ENTITY, identifier, None, other_attributes)
    
    def activity(self, identifier, startTime=None, endTime=None, other_attributes=None):
        return self.add_element(PROV_REC_ACTIVITY, identifier, {PROV_ATTR_STARTTIME: startTime, PROV_ATTR_ENDTIME: endTime}, other_attributes)
    
    def agent(self, identifier, other_attributes):
        return self.add_element(PROV_REC_AGENT, identifier, None, other_attributes=None)
    
    def note(self, identifier, other_attributes):
        return self.add_element(PROV_REC_NOTE, identifier, None, other_attributes=None)
    
    def generation(self, identifier, entity, activity, time=None, other_attributes=None):
        return self.add_record(PROV_REC_GENERATION, identifier, {PROV_ATTR_ENTITY: entity, PROV_ATTR_ACTIVITY: activity, PROV_ATTR_TIME: time}, other_attributes)
    
    def usage(self, identifier, activity, entity, time=None, other_attributes=None):
        return self.add_record(PROV_REC_USAGE, identifier, {PROV_ATTR_ACTIVITY: activity, PROV_ATTR_ENTITY: entity, PROV_ATTR_TIME: time}, other_attributes)
    
    def activityAssociation(self, identifier, activity, agent, plan=None, other_attributes=None):
        return self.add_record(PROV_REC_ACTIVITY_ASSOCIATION, identifier, {PROV_ATTR_ACTIVITY: activity, PROV_ATTR_AGENT: agent, PROV_ATTR_PLAN: plan}, other_attributes)
    
    def derivation(self, identifier, generatedEntity, usedEntity, activity=None, generation=None, usage=None, time=None, other_attributes=None):
        attributes = {PROV_ATTR_GENERATED_ENTITY: generatedEntity,
                      PROV_ATTR_USED_ENTITY: usedEntity,
                      PROV_ATTR_ACTIVITY: activity,
                      PROV_ATTR_GENERATION: generation,
                      PROV_ATTR_USAGE: usage}
        return self.add_record(PROV_REC_DERIVATION, identifier, attributes, other_attributes)
    
    # Aliases
    wasGeneratedBy = generation
    used = usage
    wasDerivedFrom = derivation
    wasAssociatedWith = activityAssociation
    

# Tests

def w3c_publication_1():
    
    # prefix ex  <http://example.org/>
    ex = Namespace('ex', 'http://example.org/')
    # prefix w3  <http://www.w3.org/>
    w3 = Namespace('w3', 'http://www.w3.org/')
    # prefix tr  <http://www.w3.org/TR/2011/>
    tr = Namespace('tr', 'http://www.w3.org/TR/2011/')
    #prefix pr  <http://www.w3.org/2005/10/Process-20051014/tr.html#>
    pr = Namespace('pr', 'http://www.w3.org/2005/10/Process-20051014/tr.html#')
    
    #prefix ar1 <https://lists.w3.org/Archives/Member/chairs/2011OctDec/>
    ar1 = Namespace('ar1', 'https://lists.w3.org/Archives/Member/chairs/2011OctDec/')
    #prefix ar2 <https://lists.w3.org/Archives/Member/w3c-archive/2011Oct/>
    ar2 = Namespace('ar3', 'https://lists.w3.org/Archives/Member/w3c-archive/2011Oct/')
    #prefix ar3 <https://lists.w3.org/Archives/Member/w3c-archive/2011Dec/>
    ar3 = Namespace('ar2', 'https://lists.w3.org/Archives/Member/w3c-archive/2011Dec/')
    
    
    g = ProvContainer()
    
    g.entity(tr['WD-prov-dm-20111018'], {PROV['type']: pr['RecsWD']})
    g.entity(tr['WD-prov-dm-20111215'], {PROV['type']: pr['RecsWD']})
    g.entity(pr['rec-advance'], {PROV['type']: PROV['Plan']})
    
    
    g.entity(ar1['0004'], {PROV['type']: Identifier("http://www.w3.org/2005/08/01-transitions.html#transreq")})
    g.entity(ar2['0141'], {PROV['type']: Identifier("http://www.w3.org/2005/08/01-transitions.html#pubreq")})
    g.entity(ar3['0111'], {PROV['type']: Identifier("http://www.w3.org/2005/08/01-transitions.html#pubreq")})
    
    
    g.wasDerivedFrom(None, tr['WD-prov-dm-20111215'], tr['WD-prov-dm-20111018'])
    
    
    g.activity(ex['pub1'], other_attributes={PROV['type']: "publish"})
    g.activity(ex['pub2'], other_attributes={PROV['type']: "publish"})
    
    
    g.wasGeneratedBy(None, tr['WD-prov-dm-20111018'], ex['pub1'])
    g.wasGeneratedBy(None, tr['WD-prov-dm-20111215'], ex['pub2'])
    
    g.used(None, ex['pub1'], ar1['0004'])
    g.used(None, ex['pub1'], ar2['0141'])
    g.used(None, ex['pub2'], ar3['0111'])
    
    g.agent(w3['Consortium'], {PROV['type']: PROV['Organization']})
    
    g.wasAssociatedWith(None, ex['pub1'], w3['Consortium'], pr['rec-advance'])
    g.wasAssociatedWith(None, ex['pub2'], w3['Consortium'], pr['rec-advance'])

    return g

def test():
    FOAF = Namespace("foaf","http://xmlns.com/foaf/0.1/")
    EX = Namespace("ex","http://www.example.com/")
    DCTERMS = Namespace("dcterms","http://purl.org/dc/terms/")
    
    # create a provenance _container
    g = ProvContainer()
    
    # Set the default _namespace name
    g.set_default_namespace(EX)
    
    # add entities, first define the _attributes in a dictionary
    e0_attrs = {PROV["type"]: "File",
                EX["path"]: "/shared/crime.txt",
                EX["creator"]: "Alice"}
    # then create the entity
    # If you give the id as a string, it will be treated as a localname
    # under the default _namespace
    e0 = g.entity(EX["e0"], e0_attrs)
    
    # define the _attributes for the next entity
    lit0 = Literal("2011-11-16T16:06:00", XSD["dateTime"])
    attrdict ={PROV["type"]: EX["File"],
               EX["path"]: "/shared/crime.txt",
               DCTERMS["creator"]: FOAF['Alice'],
               EX["content"]: "",
               DCTERMS["create"]: lit0}
    # create the entity, note this time we give the id as a PROVQname
    e1 = g.entity(FOAF['Foo'], attrdict)
    
    # add activities
    # You can give the _attributes during the creation if there are not many
    a0 = g.activity(EX['a0'], datetime.datetime(2008, 7, 6, 5, 4, 3), None, {PROV["type"]: EX["create-file"]})
    
    g0 = g.wasGeneratedBy("g0", e0, a0, None, {EX["fct"]: "create"})
    
    attrdict={EX["fct"]: "load",
              EX["typeexample"] : Literal("MyValue", EX["MyType"])}
    u0 = g.used("u0", a0, e1, None, attrdict)
    
    # The id for a relation is an optional argument, The system will generate one
    # if you do not specify it 
    g.wasDerivedFrom(None, e0, e1, a0, g0, u0)

    return g
    
    
# Testing code
logging.basicConfig(level=logging.DEBUG)
g1 = w3c_publication_1()
print '-------------------------------------- Original graph in ASN'
g1.print_records()
json_str = json.dumps(g1, cls=ProvContainer.JSONEncoder, indent=4)
print '-------------------------------------- Original graph in JSON'
print json_str
g2 = json.loads(json_str, cls=ProvContainer.JSONDecoder)
print '-------------------------------------- Graph decoded from JSON' 
g2.print_records()
print 'g1 == g2: %s' % (g1 == g2)