import datetime
import json
from collections import OrderedDict

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

PROV_ID_ATTRIBUTES_MAP = dict((prov_id, attribute) for (prov_id, attribute) in PROV_RECORD_ATTRIBUTES)
PROV_ATTRIBUTES_ID_MAP = dict((attribute, prov_id) for (prov_id, attribute) in PROV_RECORD_ATTRIBUTES)


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
    

class Namespace(object):
    def __init__(self, prefix, uri):
        self._prefix = prefix
        self._uri = uri

    def get_prefix(self):
        return self._prefix
            
    def get_uri(self):
        return self._uri
    
    def __getitem__(self, localpart):
        return QName(self, localpart)
    
XSD = Namespace("xsd",'http://www.w3.org/2001/XMLSchema-datatypes#')
PROV = Namespace("prov",'http://www.w3.org/ns/prov-dm/')
    

class ProvException(Exception):
    """Base class for exceptions in this module."""
    pass


class ProvRecord(object):
    """Base class for PROV _records."""
    def __init__(self, container, identifier, attributes, other_attributes):
        self._container = container
        self._identifier = identifier
        self._attributes = attributes
        self._extra_attributes = other_attributes
        
    def get_type(self):
        pass
    
    def get_identifier(self):
        return self._identifier
    
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
                    items.append(str(value) if value is not None else '')
        
        extra = []
        if self._extra_attributes:
            for (attr, value) in self._extra_attributes.items():
                extra.append('%s="%s"' % (str(attr), str(value)))
        
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


class ProvContainer(object):
    def __init__(self):
        self._records = list()
        self._namespaces = { PROV.get_prefix(): PROV, XSD.get_prefix(): XSD}
        self._default_namespace = PROV
        
    # Container configurations
    def set_default_namespace(self, namespace):
        self._default_namespace = namespace
        self._namespaces.update({namespace.get_prefix(): namespace})
        
    def add_namespace(self, namespace):
        prefix = namespace.get_prefix()
        if prefix not in self._namespaces:
            self._namespaces[prefix] = namespace

    def valid_identifier(self, identifier):
        if identifier is None:
            return None
        if isinstance(identifier, Identifier):
            if isinstance(identifier, QName):
                # Register the namespace if it has not been registered before
                namespace = identifier.get_namespace() 
                if namespace not in self._namespaces.values():
                    self.add_namespace(namespace)
            # return the original identifier
            return identifier
        elif isinstance(identifier, (str, unicode)):
            if ':' in identifier:
                # create and return an Identifier with the given uri
                return Identifier(identifier)
            else:
                # create and return an identifier in the default namespace
                return self._default_namespace[identifier] 
        
    def get_anon_id(self, record):
        #TODO Implement a dict of self-generated anon ids for records without identifier
        return "Anon ID"
    
    # PROV-JSON serialization/deserialization    
    class ProvJSONEncoder(json.JSONEncoder):
        def default(self, o):
            return json.JSONEncoder.default(self, o)
            
    class ProvJSONDecoder(json.JSONDecoder):
        def decode(self, s):
            return json.JSONDecoder.decode(self, s)
    
    # Miscellaneous functions
    def print_records(self):
        for (prefix, namespace) in self._namespaces.items():
            print 'prefix %s: %s' % (prefix, namespace.get_uri())
        print ''
        for record in self._records:
            print record
            
    # Provenance statements
    def add_record(self, record_type, identifier, attributes=None, other_attributes=None):
        new_record = PROV_REC_CLS[record_type](self, self.valid_identifier(identifier), attributes, other_attributes)
        self._records.append(new_record)
        return new_record
    
    def add_element(self, record_type, identifier, attributes=None, other_attributes=None):
        return self.add_record(record_type, identifier, attributes, other_attributes)
        
    def entity(self, identifier, other_attributes=None):
        return self.add_element(PROV_REC_ENTITY, identifier, None, other_attributes)
    
    def activity(self, identifier, startTime=None, endTime=None, other_attributes=None):
        return self.add_element(PROV_REC_ACTIVITY, identifier,
                                {PROV_ATTR_STARTTIME: startTime, PROV_ATTR_ENDTIME: endTime},
                                other_attributes)
    
    def agent(self, identifier, other_attributes):
        return self.add_element(PROV_REC_AGENT, identifier, None, other_attributes=None)
    
    def note(self, identifier, other_attributes):
        return self.add_element(PROV_REC_NOTE, identifier, None, other_attributes=None)
    
    def generation(self, identifier, entity, activity, time=None, other_attributes=None):
        if not isinstance(entity, ProvEntity) or not isinstance(activity, ProvActivity):
            # TODO Specify exception details
            raise ProvException
        attributes = OrderedDict()
        attributes[PROV_ATTR_ENTITY]= entity
        attributes[PROV_ATTR_ACTIVITY]= activity
        attributes[PROV_ATTR_TIME]= time
        return self.add_record(PROV_REC_GENERATION, identifier, attributes, other_attributes)
    
    def usage(self, identifier, activity, entity, time=None, other_attributes=None):
        if not isinstance(entity, ProvEntity) or not isinstance(activity, ProvActivity):
            # TODO Specify exception details
            raise ProvException
        attributes = OrderedDict()
        attributes[PROV_ATTR_ACTIVITY]= activity
        attributes[PROV_ATTR_ENTITY]= entity
        attributes[PROV_ATTR_TIME]= time
        return self.add_record(PROV_REC_USAGE, identifier, attributes, other_attributes)
    
    # Aliases
    wasGeneratedBy = generation
    used = usage
    

# Tests

def test():
    FOAF = Namespace("foaf","http://xmlns.com/foaf/0.1/")
    EX = Namespace("ex","http://www.example.com/")
    DCTERMS = Namespace("dcterms","http://purl.org/dc/terms/")
    
    # create a provenance _container
    g = ProvContainer()
    
    # Set the default _namespace name
    g.set_default_namespace(EX)
    
    # add the other _namespaces with their prefixes into the _container
    # You can do this any time before you output the JSON serialization
    # of the _container
    # Note for each _namespace name, if a _prefix given here is different to the
    # one carried in the PROVNamespace instance defined previously, the _prefix
    # HERE will be used in the JSON serialization.
    g.add_namespace(DCTERMS)
    g.add_namespace(FOAF)
    
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
    a0 = g.activity(EX['a0'], datetime.datetime(2008, 7, 6, 5, 4, 3), None, {PROV["plan"]: EX["create-file"]})
    
    attrdict = {EX["fct"]: "create"}
    g0 = g.wasGeneratedBy("g0", e0, a0, None, attrdict)
    
    attrdict={EX["fct"]: "load",
              EX["typeexample"] : Literal("MyValue", EX["MyType"])}
    u0 = g.used("u0", a0, e1, None, attrdict)
    
#    # The id for a relation is an optional argument, The system will generate one
#    # if you do not specify it 
#    d0=wasDerivedFrom(e0,e1,activity=a0,generation=g0,usage=u0,_attributes=None)
#    g.add(d0)

    g.print_records()
    
test()