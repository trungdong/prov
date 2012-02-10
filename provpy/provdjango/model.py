import datetime
import json

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
)

PROV_RECORD_LITERALS = (
    # Literal properties
    (PROV_ATTR_TIME, u'prov:time'),
    (PROV_ATTR_STARTTIME, u'prov:startTime'),
    (PROV_ATTR_ENDTIME, u'prov:endTime'),
)


class Literal(object):
    def __init__(self, value, datatype):
        self.value = value
        self.datatype = datatype
        
    def __str__(self):
        return '"s"^^"s"' % (self.value, self.datatype)
    
    def get_value(self):
        return self.value
    
    def get_datatype(self):
        return self.datatype


class Identifier(object):
    def __init__(self, uri):
        self.uri = uri
        
    def get_uri(self):
        return self.uri
    
    def __str__(self):
        return self.uri
    
    def __eq__(self, other):
        return self.get_uri() == other.get_uri() if isinstance(other, Identifier) else False
    
    def __hash__(self):
        return hash(self.get_uri())
    

class QName(Identifier):
    def __init__(self, namespace, localpart):
        self.namespace = namespace
        self.localpart = localpart
        
    def get_uri(self):
        return ''.join(self.namespace, self.localpart)
    
    def __str__(self):
        return ':'.join(self.namespace.prefix, self.localpart)
    

class Namespace(object):
    def __init__(self, prefix, uri):
        self.prefix = prefix
        self.uri = uri
        
    def get_uri(self):
        return self.uri
    
    def __getitem__(self, localpart):
        return QName(self, localpart)
    
XSD = Namespace("xsd",'http://www.w3.org/2001/XMLSchema-datatypes#')
PROV = Namespace("prov",'http://www.w3.org/ns/prov-dm/')
    

class ProvException(Exception):
    """Base class for exceptions in this module."""
    pass


class ProvRecord(object):
    """Base class for PROV records."""
    def __init__(self, container, identifier, attributes, other_attributes):
        self.container = container
        self.identifier = identifier
        self.attributes = attributes
        self.other_attributes = other_attributes
        
    def get_type(self):
        pass


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


class ProvAgent(ProvElement):
    def get_type(self):
        return PROV_REC_AGENT

    
class ProvNote(ProvElement):
    def get_type(self):
        return PROV_REC_NOTE

    
class ProvGeneration(ProvRelation):
    def get_type(self):
        return PROV_REC_GENERATION


class ProvUsage(ProvRelation):
    def get_type(self):
        return PROV_REC_USAGE
    
    
PROV_REC_CLS = {
    PROV_REC_ENTITY                 : ProvEntity,
    PROV_REC_ACTIVITY               : ProvActivity,
    PROV_REC_AGENT                  : ProvAgent,
    PROV_REC_NOTE                   : ProvNote,
#    PROV_REC_ACCOUNT                : 10
    PROV_REC_GENERATION             : ProvGeneration,
    PROV_REC_USAGE                  : ProvUsage,
#    PROV_REC_ACTIVITY_ASSOCIATION   = 13
#    PROV_REC_START                  = 14
#    PROV_REC_END                    = 15
#    PROV_REC_RESPONSIBILITY         = 16
#    PROV_REC_DERIVATION             = 17
#    PROV_REC_ALTERNATE              = 18
#    PROV_REC_SPECIALIZATION         = 19
#    PROV_REC_ANNOTATION             = 99
    }
class ProvContainter(object):
    def __init__(self):
        self.records = list()
        self.namespaces = dict()
        
    class ProvJSONEncoder(json.JSONEncoder):
        def default(self, o):
            return json.JSONEncoder.default(self, o)
            
    class ProvJSONDecoder(json.JSONDecoder):
        def decode(self, s):
            return json.JSONDecoder.decode(self, s)
        
    def add_record(self, record_type, identifier, attributes=None, other_attributes=None):
        new_record = PROV_REC_CLS[record_type](self, identifier, attributes, other_attributes)
        return new_record
    
    def add_element(self, record_type, identifier, attributes=None, other_attributes=None):
        return self.add_record(record_type, identifier, attributes, other_attributes)
        
    def entity(self, identifier, other_attributes):
        return self.add_element(PROV_REC_ENTITY, identifier, None, other_attributes)
    
    def activity(self, identifier, startTime=None, endTime=None, other_attributes=None):
        return self.add_element(PROV_REC_ACTIVITY, identifier, None, other_attributes)
    
    def agent(self, identifier, other_attributes):
        return self.add_element(PROV_REC_AGENT, identifier, None, other_attributes=None)
    
    def note(self, identifier, other_attributes):
        return self.add_element(PROV_REC_NOTE, identifier, None, other_attributes=None)
    
    def generation(self, identifier, entity, activity, time=None, other_attributes=None):
        attributes = {}
        return self.add_record(PROV_REC_GENERATION, identifier, attributes, other_attributes)
    
    def usage(self, identifier, activity, entity, time=None, other_attributes=None):
        attributes = {}
        return self.add_record(PROV_REC_GENERATION, identifier, attributes, other_attributes)
    
    # Aliases
    wasGeneratedBy = generation
    used = usage