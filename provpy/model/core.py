import datetime
#from lxml.cssselect import ident

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

class PROVIdentifier(object):
    
    def __init__(self,name):
        self.name = name
        
    def uri(self):
        return self.name

class PROVQname(PROVIdentifier):
    
    def __init__(self,name,prefix=None,namespacename=None,localname=None):
        PROVIdentifier.__init__(self, name)
        self.namespacename = namespacename
        self.localname = localname
        self.prefix = prefix
        
    def __str__(self):
        return self.name
    
    def __eq__(self,other):
        if not isinstance(other,PROVQname):
            return False
        else:
            return self.name == other.name
    
    def __hash__(self):
        return id(self)
    
    def qname(self,nsdict):
        rt = self.name
        for prefix,namespacename in nsdict.items():
            if self.namespacename == namespacename:
                if prefix <> 'default':
                    if self.localname is not None:
                        rt = ":".join((prefix, self.localname))
                else:
                    rt = self.localname
        if not self.namespacename in nsdict.values():
            if self.prefix is not None:
                rt = ":".join((self.prefix, self.localname))
        return rt
    
    def to_provJSON(self,nsdict):
        qname = self.qname(nsdict)
        if self.name == qname:
            rt = [qname,"xsd:anyURI"]
        else:
            rt = [qname,"xsd:QName"]
        return rt


class PROVNamespace(PROVIdentifier):
    
    def __init__(self,prefix,namespacename):
        self.prefix = prefix
        self.namespacename = namespacename
        
    def __getitem__(self,localname):
        return PROVQname(self.namespacename+localname,self.prefix,self.namespacename,localname)

        
xsd = PROVNamespace("xsd",'http://www.w3.org/2001/XMLSchema-datatypes#')
prov = PROVNamespace("prov",'http://www.w3.org/ns/prov-dm/')


class Record(object):

    def __init__(self, identifier=None, attributes=None, account=None):
        if identifier is not None:
            if isinstance(identifier, PROVQname):
                self.identifier = identifier
            elif isinstance(identifier, (str, unicode)):
                self.identifier = PROVQname(identifier, localname=identifier)
            else:
                raise PROVGraph_Error("The identifier of PROV record must be given as a string or an PROVQname")
        else:
            self.identifier = None
        
        
        self._record_attributes = {}

        #TODO Remove the following code. It is here to maintain compatibility with the current JSON export code            
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes

        self.account = account
        
    def __str__(self):
        if self.identifier is not None:
            return str(self.identifier)
        #TODO should we return None here?
        return None
        
#    def __getattr__(self, attr):
#        if attr in self._attributes:
#            return self._attributes[attr]
#        # If no attribute could be found, raise the standard error
#        raise AttributeError, attr
    
    def _get_type_JSON(self,value):
        datatype = None
        if isinstance(value,str) or isinstance(value,bool):
            datatype = None
        if isinstance(value,float):
            datatype = xsd["float"]
        if isinstance(value,datetime.datetime):
            datatype = xsd["dateTime"]
        if isinstance(value,int):
            datatype = xsd["integer"]
        if isinstance(value,list):
            datatype = prov["array"]
        return datatype
        
    def _convert_value_JSON(self,value,nsdict):
        valuetojson = value
        if isinstance(value,PROVLiteral): 
            valuetojson=value.to_provJSON(nsdict)
        elif isinstance(value,PROVQname):
            valuetojson=value.to_provJSON(nsdict)
        else:
            datatype = self._get_type_JSON(value)
            if datatype is not None:
                if not datatype == prov["array"]:
                    valuetojson=[str(value),datatype.qname(nsdict)]
                else:
                    newvalue = []
                    islist = False
                    for item in value:
                        if isinstance(item,list):
                            islist = True
                        newvalue.append(self._convert_value_JSON(item, nsdict))
                    if islist is False:
                        valuetojson=[newvalue,datatype.qname(nsdict)]
        return valuetojson
    
    def get_prov_type(self):
        return self.prov_type

    def get_record_id(self):
        return self.identifier
    
    def get_record_attributes(self):
        return dict()
    
    def get_other_attributes(self):
        # It might be needed to return an immutable copy to avoid accidental modifications
        return self.attributes
    
    def get_all_attributes(self):
        attributes = self.get_record_attributes()
        attributes.update(self.attributes) 
        return attributes

class Element(Record):
    
    def __init__(self, identifier=None, attributes=None, account=None):
        if identifier is None:
            raise PROVGraph_Error("An element is always required to have an identifier")
        Record.__init__(self, identifier, attributes, account)
        
        self._json = {}
        self._provcontainer = {}
        self._idJSON = None
        self._attributelist = [self.identifier, self.account, self.attributes]
        
    def to_provJSON(self,nsdict):
        if isinstance(self.identifier,PROVQname):
            self._idJSON = self.identifier.qname(nsdict)
        elif self.identifier is None:
            if self._idJSON is None:
                self._idJSON = 'NoID'
        self._json[self._idJSON]=self.attributes.copy()
        for attribute in self._json[self._idJSON].keys():
            if isinstance(attribute, PROVQname):
                attrtojson = attribute.qname(nsdict)
                self._json[self._idJSON][attrtojson] = self._json[self._idJSON][attribute]
                del self._json[self._idJSON][attribute]
        for attribute,value in self._json[self._idJSON].items():
            valuetojson = self._convert_value_JSON(value,nsdict)
            if valuetojson is not None:
                self._json[self._idJSON][attribute] = valuetojson
        return self._json


class Entity(Element):

    def __init__(self, identifier=None, attributes=None, account=None):
        Element.__init__(self, identifier, attributes, account)
        self.prov_type = PROV_REC_ENTITY
        
    def to_provJSON(self,nsdict):
        Element.to_provJSON(self,nsdict)
        self._provcontainer['entity']=self._json
        return self._provcontainer
    

class Activity(Element):
    
    def __init__(self, identifier=None, starttime=None, endtime=None, attributes=None, account=None):
        Element.__init__(self, identifier, attributes, account)
        self.prov_type = PROV_REC_ACTIVITY
        
        self.starttime=starttime
        self.endtime=endtime
        self._attributelist.extend([self.starttime,self.endtime])
        
    def get_record_attributes(self):
        record_attributes = {}
        if self.starttime is not None:
            record_attributes['startTime'] = self.starttime
        if self.endtime is not None:
            record_attributes['endTime'] = self.endtime
        return record_attributes
        
    def to_provJSON(self,nsdict):
        Element.to_provJSON(self,nsdict)
        if self.starttime is not None:
            self._json[self._idJSON]['prov:starttime']=self._convert_value_JSON(self.starttime,nsdict)
        if self.endtime is not None:
            self._json[self._idJSON]['prov:endtime']=self._convert_value_JSON(self.endtime,nsdict)
        self._provcontainer['activity']=self._json
        return self._provcontainer


class Agent(Entity):

    def __init__(self, identifier=None, attributes=None, account=None):
        Entity.__init__(self, identifier, attributes, account)
        self.prov_type = PROV_REC_AGENT
        
    def to_provJSON(self,nsdict):
        Element.to_provJSON(self,nsdict)
        self._provcontainer['entity']=self._json
        #TODO: How to mark an Agent?
        return self._provcontainer
        

class Note(Element):

    def __init__(self, identifier=None, attributes=None, account=None):
        Element.__init__(self, identifier, attributes, account)
        self.prov_type = PROV_REC_NOTE
        
    def to_provJSON(self,nsdict):
        Element.to_provJSON(self,nsdict)
        self._provcontainer['note']=self._json
        return self._provcontainer


class Relation(Record):

    def __init__(self, identifier=None, attributes=None, account=None):
        Record.__init__(self, identifier, attributes, account)

        self._json = {}
        self._provcontainer = {}
        self._idJSON = None
        self._attributelist = [self.identifier,self.account,self.attributes]
    
    def to_provJSON(self,nsdict):
        if isinstance(self.identifier,PROVQname):
            self._idJSON = self.identifier.qname(nsdict)
        elif self.identifier is None:
            if self._idJSON is None:
                self._idJSON = 'NoID'
        self._json[self._idJSON]=self.attributes.copy()
        for attribute in self._json[self._idJSON].keys():
            if isinstance(attribute, PROVQname):
                attrtojson = attribute.qname(nsdict)
                self._json[self._idJSON][attrtojson] = self._json[self._idJSON][attribute]
                del self._json[self._idJSON][attribute]
        for attribute,value in self._json[self._idJSON].items():
            valuetojson = self._convert_value_JSON(value,nsdict)
            if valuetojson is not None:
                self._json[self._idJSON][attribute] = valuetojson
        return self._json
        
    

class wasGeneratedBy(Relation):
    
    def __init__(self, entity, activity, identifier=None, time=None, attributes=None, account=None):
        Relation.__init__(self, identifier, attributes, account)
        self.prov_type = PROV_REC_GENERATION
        self.entity=entity
        self.activity=activity
        self.time = time
        self._attributelist.extend([self.entity,self.activity,self.time])
        
    def get_record_attributes(self):
        record_attributes = {}
        record_attributes['entity'] = self.entity
        record_attributes['activity'] = self.activity
        if self.time is not None:
            record_attributes['time'] = self.time
        return record_attributes
    
    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:entity']=self.entity._idJSON
        self._json[self._idJSON]['prov:activity']=self.activity._idJSON
        if self.time is not None:
            self._json[self._idJSON]['prov:time']=self._convert_value_JSON(self.time,nsdict)
        self._provcontainer['wasGeneratedBy']=self._json
        return self._provcontainer
    

class Used(Relation):
    
    def __init__(self,activity,entity,identifier=None,time=None,attributes=None,account=None):
        Relation.__init__(self,identifier,attributes,account)
        self.prov_type = PROV_REC_USAGE
        self.entity=entity
        self.activity=activity
        self.time = time
        self._attributelist.extend([self.entity,self.activity,self.time])
        
    def get_record_attributes(self):
        record_attributes = {}
        record_attributes['entity'] = self.entity
        record_attributes['activity'] = self.activity
        if self.time is not None:
            record_attributes['time'] = self.time
        return record_attributes

        
    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:entity']=self.entity._idJSON
        self._json[self._idJSON]['prov:activity']=self.activity._idJSON
        if self.time is not None:
            self._json[self._idJSON]['prov:time']=self._convert_value_JSON(self.time,nsdict)
        self._provcontainer['used']=self._json
        return self._provcontainer
    

class wasAssociatedWith(Relation):
    
    def __init__(self, activity, agent, identifier=None, attributes=None, account=None):
        Relation.__init__(self,identifier,attributes,account)
        self.prov_type = PROV_REC_ACTIVITY_ASSOCIATION
        self.activity=activity
        self.agent=agent
        self._attributelist.extend([self.agent,self.activity])
        
    def get_record_attributes(self):
        record_attributes = {}
        record_attributes['agent'] = self.agent
        record_attributes['activity'] = self.activity
        return record_attributes

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:activity']=self.activity._idJSON
        self._json[self._idJSON]['prov:agent']=self.agent._idJSON
        self._provcontainer['wasAssociatedWith']=self._json
        return self._provcontainer
    

class wasStartedBy(Relation):
    
    def __init__(self,activity,agent,identifier=None,attributes=None,account=None):
        Relation.__init__(self,identifier,attributes,account)
        self.prov_type = PROV_REC_START
        self.activity=activity
        self.agent=agent
        self._attributelist.extend([self.agent,self.activity])
        
    def get_record_attributes(self):
        record_attributes = {}
        record_attributes['entity'] = self.entity
        record_attributes['activity'] = self.activity
        return record_attributes

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:activity']=self.activity._idJSON
        self._json[self._idJSON]['prov:agent']=self.agent._idJSON
        self._provcontainer['wasStartedBy']=self._json
        return self._provcontainer
    

class wasEndedBy(Relation):
    
    def __init__(self,activity,agent,identifier=None,attributes=None,account=None):
        Relation.__init__(self,identifier,attributes,account)
        self.prov_type = PROV_REC_END
        self.activity=activity
        self.agent=agent
        self._attributelist.extend([self.agent,self.activity])
        
    def get_record_attributes(self):
        record_attributes = {}
        record_attributes['entity'] = self.entity
        record_attributes['activity'] = self.activity
        return record_attributes
        
    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:activity']=self.activity._idJSON
        self._json[self._idJSON]['prov:agent']=self.agent._idJSON
        self._provcontainer['wasEndedBy']=self._json
        return self._provcontainer
        

class actedOnBehalfOf(Relation):
    
    def __init__(self, subordinate, responsible, identifier=None, attributes=None, account=None):
        Relation.__init__(self, identifier, attributes, account)
        self.prov_type = PROV_REC_RESPONSIBILITY
        self.subordinate = subordinate
        self.responsible = responsible
        self._attributelist.extend([self.subordinate,self.responsible])
        
    def get_record_attributes(self):
        record_attributes = {}
        record_attributes['subordinate'] = self.subordinate
        record_attributes['responsible'] = self.responsible
        return record_attributes

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:subordinate']=self.subordinate._idJSON
        self._json[self._idJSON]['prov:responsible']=self.responsible._idJSON
        self._provcontainer['actedOnBehalfOf']=self._json
        return self._provcontainer
    

class wasDerivedFrom(Relation):
    
    def __init__(self, generatedentity, usedentity, identifier=None, activity=None, generation=None, usage=None, attributes=None, account=None):
        #TODO Enforce mandatory attributes as required by PROV-DM
        Relation.__init__(self,identifier,attributes,account)
        self.prov_type = PROV_REC_DERIVATION
        self.generatedentity = generatedentity
        self.usedentity = usedentity
        self.activity = activity
        self.generation = generation
        self.usage = usage
        self._attributelist.extend([self.generatedentity,self.usedentity,self.activity,self.generation,self.usage])
        
    def get_record_attributes(self):
        record_attributes = {}
        record_attributes['generatedEntity'] = self.generatedentity
        record_attributes['usedEntity'] = self.usedentity
        if self.activity is not None:
            record_attributes['activity'] = self.activity
        if self.generation is not None:
            record_attributes['generation'] = self.generation
        if self.usage is not None:
            record_attributes['usage'] = self.usage
        return record_attributes


    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:generatedentity']=self.generatedentity._idJSON
        self._json[self._idJSON]['prov:usedentity']=self.usedentity._idJSON
        if self.activity is not None:
            self._json[self._idJSON]['prov:activity']=self.activity._idJSON
        if self.generation is not None:
            self._json[self._idJSON]['prov:generation']=self.generation._idJSON
        if self.usage is not None:
            self._json[self._idJSON]['prov:usage']=self.usage._idJSON
        self._provcontainer['wasDerivedFrom']=self._json
        return self._provcontainer
                        

class alternateOf(Relation):
    
    def __init__(self,subject,alternate,identifier=None,attributes=None,account=None):
        Relation.__init__(self,identifier,attributes,account)
        self.prov_type = PROV_REC_ALTERNATE
        self.subject = subject
        self.alternate = alternate
        self._attributelist.extend([self.subject,self.alternate])
        
    def get_record_attributes(self):
        record_attributes = {}
        record_attributes['subject'] = self.subject
        record_attributes['alternate'] = self.alternate
        return record_attributes


    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:subject']=self.subject._idJSON
        self._json[self._idJSON]['prov:alternate']=self.alternate._idJSON
        self._provcontainer['alternateOf']=self._json
        return self._provcontainer
 
 
class specializationOf(Relation):
    
    def __init__(self,subject,specialization,identifier=None,attributes=None,account=None):
        Relation.__init__(self,identifier,attributes,account)
        self.prov_type = PROV_REC_SPECIALIZATION
        self.subject = subject
        self.specialization = specialization
        self._attributelist.extend([self.subject,self.specialization])
        
    def get_record_attributes(self):
        record_attributes = {}
        record_attributes['subject'] = self.subject
        record_attributes['specialization'] = self.specialization
        return record_attributes

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:subject']=self.subject._idJSON
        self._json[self._idJSON]['prov:specialization']=self.specialization._idJSON
        self._provcontainer['specializationOf']=self._json
        return self._provcontainer
               

class hasAnnotation(Relation):
    
    def __init__(self, record, note, identifier=None, attributes=None, account=None):
        Relation.__init__(self, identifier, attributes, account)
        self.prov_type = PROV_REC_ANNOTATION
        self.record=record
        self.note=note
        self._attributelist.extend([self.record, self.note])

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:record']=self.record._idJSON
        self._json[self._idJSON]['prov:note']=self.note._idJSON
        self._provcontainer['hasAnnotation']=self._json
        return self._provcontainer
    

class PROVLiteral():
    
    def __init__(self, value, datatype):
        self.value = value
        self.datatype = datatype
        self._json = []
        
    def __str__(self):
        return 'Not supported yet'
        
    def to_provJSON(self,nsdict):
        self._json = []
        if isinstance(self.value, PROVQname):
            self._json.append(self.value.qname(nsdict))
        else:
            self._json.append(self.value)
        if isinstance(self.datatype, PROVQname):
            self._json.append(self.datatype.qname(nsdict))
        else:
            self._json.append(self.datatype)
        return self._json


class Bundle():
    
    def __init__(self):
        self._provcontainer = {}
        self._elementlist = []
        self._relationlist = []
        self._namespacedict = {}
        self._implicitnamespace = {'prov':'http://www.w3.org/ns/prov-dm/',
                                   'xsd' :'http://www.w3.org/2001/XMLSchema-datatypes#'}
        self._accountlist = []
        self._elementkey = 0
        self._relationkey = 0
        self._auto_ns_key = 0
        if self.identifier is None:
            self.identifier = PROVQname("default", localname="default")
        self._idJSON = None
   
    def add(self,record):
        if isinstance(record,Element):
            self._validate_record(record)
            if record.account is None:
                self._elementlist.append(record)
                record.account = self
            elif not record.account.identifier == self.identifier:
                record.account.add(record)
            elif not record in self._elementlist:
                self._elementlist.append(record)
        elif isinstance(record,Relation):
            self._validate_record(record)
            if record.account is None:
                self._relationlist.append(record)
                record.account = self
            elif not record.account.identifier == self.identifier:
                record.account.add(record)
            elif not record in self._elementlist:
                self._relationlist.append(record)
        elif isinstance(record,Account):
            if record.parentaccount is None:
                self._accountlist.append(record)
                record.parentaccount = self
            elif not record.parentaccount.identifier == self.identifier:
                record.account.add(record)
            elif not record in self._accountlist:
                self._accountlist.append(record)
            
    def to_provJSON(self,nsdict):
        self._generate_idJSON(nsdict)
        for element in self._elementlist:
            if isinstance(element,Agent):
                if not 'agent' in self._provcontainer.keys():
                    self._provcontainer['agent']=[]
                self._provcontainer['agent'].append(element.identifier)
            jsondict = element.to_provJSON(nsdict)
            for key in jsondict:
                if not key in self._provcontainer.keys():
                    self._provcontainer[key]={}
                self._provcontainer[key].update(jsondict[key])
        for relation in self._relationlist:
            jsondict = relation.to_provJSON(nsdict)
            for key in jsondict:
                if not key in self._provcontainer.keys():
                    self._provcontainer[key]={}
                self._provcontainer[key].update(jsondict[key])
        for account in self._accountlist:
            if not 'account' in self._provcontainer.keys():
                self._provcontainer['account']={}
            if not account._idJSON in self._provcontainer['account'].keys():
                self._provcontainer['account'][account._idJSON]={}
            self._provcontainer['account'][account._idJSON].update(account.to_provJSON(nsdict))
        return self._provcontainer

    def _generate_idJSON(self,nsdict):
        for element in self._elementlist:
            if element.identifier is None:
                element._idJSON = self._generate_elem_identifier()
            else:
                print "generate idJSON for %s" % str(element.identifier)
                element._idJSON = element.identifier.qname(nsdict)
        for relation in self._relationlist:
            if relation.identifier is None:
                relation._idJSON = self._generate_rlat_identifier()
            else:
                print "generate idJSON for %s" % str(relation.identifier)
                relation._idJSON = relation.identifier.qname(nsdict)
        for account in self._accountlist:
            print "generate idJSON for %s" % str(account.identifier)
            account._idJSON = account.identifier.qname(nsdict)
            account._generate_idJSON(nsdict)
                    
    def add_namespace(self, prefix, uri):
        #TODO: add prefix validation here
        if prefix is "default":
            raise PROVGraph_Error("The namespace prefix 'default' is a reserved by provpy library")
        else:
            self._namespacedict[prefix] = uri
#            self._apply_namespace(prefix, url)

    def get_namespaces(self):
        return self._namespacedict 
    
    def _generate_rlat_identifier(self):
        identifier = "_:RLAT"+str(self._relationkey)
        self._relationkey = self._relationkey + 1
        if self._validate_id(identifier) is False:
            identifier = self._generate_rlat_identifier()
        return identifier

    def _generate_elem_identifier(self):
        identifier = "_:ELEM"+str(self._elementkey)
        self._elementkey = self._elementkey + 1
        if self._validate_id(identifier) is False:
            identifier = self._generate_elem_identifier()
        return identifier
        
    def _validate_id(self, identifier):
        valid = True
        for element in self._elementlist:
            if element._idJSON == identifier:
                valid = False
        for relation in self._relationlist:
            if relation._idJSON == identifier:
                valid = False
        return valid

    def add_entity(self,identifier=None,attributes=None,account=None):
        if self._validate_id(identifier) is False:
            raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            element=Entity(identifier,attributes,account)
            self.add(element)
            return element
    
    def add_activity(self,identifier=None,starttime=None,endtime=None,attributes=None,account=None):
        if self._validate_id(identifier) is False:
            raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            element=Activity(identifier,starttime,endtime,attributes,account=account)
            self.add(element)
            return element
    
    def add_agent(self,identifier=None,attributes=None,account=None):
        if self._validate_id(identifier) is False:
            raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            element=Agent(identifier,attributes,account=account)
            self.add(element)
            return element
    
    def add_note(self,identifier=None,attributes=None,account=None):
        if self._validate_id(identifier) is False:
            raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            element=Note(identifier,attributes,account=account)
            self.add(element)
            return element

    def add_wasGeneratedBy(self,entity,activity,identifier=None,time=None,attributes=None,account=None):
        if identifier is not None:
            if self._validate_id(identifier) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=wasGeneratedBy(entity,activity,identifier,time,attributes,account=account)
            self.add(relation)
            return relation

    def add_used(self,activity,entity,identifier=None,time=None,attributes=None,account=None):
        if identifier is not None:
            if self._validate_id(identifier) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=Used(activity,entity,identifier,time,attributes,account=account)
            self.add(relation)
            return relation

    def add_wasAssociatedWith(self,activity,agent,identifier=None,attributes=None,account=None):
        if identifier is not None:
            if self._validate_id(identifier) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=wasAssociatedWith(activity,agent,identifier,attributes,account=account)
            self.add(relation)
            return relation

    def add_wasStartedBy(self,activity,agent,identifier=None,attributes=None,account=None):
        if identifier is not None:
            if self._validate_id(identifier) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=wasStartedBy(activity,agent,identifier,attributes,account=account)
            self.add(relation)
            return relation

    def add_wasEndedBy(self,activity,agent,identifier=None,attributes=None,account=None):
        if identifier is not None:
            if self._validate_id(identifier) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=wasEndedBy(activity,agent,identifier,attributes,account=account)
            self.add(relation)
            return relation

    def add_actedOnBehalfOf(self,subordinate,responsible,identifier=None,attributes=None,account=None):
        if identifier is not None:
            if self._validate_id(identifier) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=actedOnBehalfOf(subordinate,responsible,identifier,attributes,account=account)
            self.add(relation)
            return relation
      
    def add_wasDerivedFrom(self,generatedentity,usedentity,identifier=None,activity=None,generation=None,usage=None,attributes=None,account=None):
        if identifier is not None:
            if self._validate_id(identifier) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=wasDerivedFrom(generatedentity,usedentity,identifier,activity,generation,usage,attributes,account=account)
            self.add(relation)
            return relation
    
    def add_alternateOf(self,subject,alternate,identifier=None,attributes=None,account=None):
        if identifier is not None:
            if self._validate_id(identifier) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=alternateOf(subject,alternate,identifier,attributes,account=account)
            self.add(relation)
            return relation

    def add_specializationOf(self,subject,specialization,identifier=None,attributes=None,account=None):
        if identifier is not None:
            if self._validate_id(identifier) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=specializationOf(subject,specialization,identifier,attributes,account=account)
            self.add(relation)
            return relation
    
    def add_hasAnnotation(self,record,note,identifier=None,attributes=None,account=None):
        if identifier is not None:
            if self._validate_id(identifier) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=hasAnnotation(record,note,identifier,attributes,account=account)
            self.add(relation)
            return relation

    def add_account(self,identifier,parentaccount=None):
        acc = Account(identifier,parentaccount)
        self.add(acc)

    def _validate_record(self,record):
        pass # Put possible record validation here

    def _validate_qname(self,qname):
        pass # Put possible Qname validation here
    
    def get_records(self):
        records = []
        records.extend(self._elementlist)
        records.extend(self._relationlist)
        records.extend(self._accountlist)
        return records
            

class PROVContainer(Bundle):
    
    def __init__(self,defaultnamespace=None):
        self.defaultnamespace=defaultnamespace
        self.identifier = None
        Bundle.__init__(self)
        self._visitedrecord = []
        self._nsdict = {}
        
    def set_default_namespace(self,defaultnamespace):
        self.defaultnamespace = defaultnamespace
        
    def get_default_namespace(self):
        return self.defaultnamespace

    def _create_nsdict(self):
        self._auto_ns_key = 0
        if not self.defaultnamespace is None:
            self._nsdict = {'default':self.defaultnamespace}
        self._nsdict.update(self._implicitnamespace)
        self._nsdict.update(self._namespacedict)
        self._visitedrecord = []
        self._merge_namespace(self)
        for prefix,namespacename in self._nsdict.items():
            if namespacename == self.defaultnamespace:
                if not prefix == "default":
                    del self._nsdict[prefix]
        return self._nsdict

    def _merge_namespace(self,obj):
        self._visitedrecord.append(obj)
        if isinstance(obj,Bundle):
            for prefix,namespacename in obj._namespacedict.items():
                tempqname = PROVQname(namespacename,prefix,namespacename,None)
                self._merge_namespace(tempqname)
            for element in obj._elementlist:
                for attr in element._attributelist:
                    if not attr in self._visitedrecord:
                        self._merge_namespace(attr)
            for relation in obj._relationlist:
                for attr in relation._attributelist:
                    if not attr in self._visitedrecord:
                        self._merge_namespace(attr)
            for account in obj._accountlist:
                if not account in self._visitedrecord:
                    self._merge_namespace(account)
        if isinstance(obj,PROVQname):
            if not obj.prefix is None:
                if obj.prefix in self._nsdict.keys():
                    if not obj.namespacename == self._nsdict[obj.prefix]:
                        if not self._nsdict["default"] == obj.namespacename:
                            newprefix = self._generate_prefix()
                            self._nsdict[newprefix] = obj.namespacename
                elif not obj.namespacename in self._nsdict:
                    self._nsdict[obj.prefix] = obj.namespacename
        if isinstance(obj,list):
            for item in obj:
                self._merge_namespace(item)
        if isinstance(obj,dict):
            for key,value in obj.items():
                self._merge_namespace(key)
                self._merge_namespace(value)

    def _generate_prefix(self):
        prefix = "ns" + str(self._auto_ns_key)
        self._auto_ns_key = self._auto_ns_key + 1
        if prefix in self._nsdict.keys():
            prefix = self._generate_prefix()
        return prefix 

    def to_provJSON(self):
        nsdict = self._create_nsdict()
        Bundle.to_provJSON(self,nsdict)
        self._provcontainer['prefix']={}
        for prefix,url in nsdict.items():
            self._provcontainer['prefix'][prefix]=url

        if self.defaultnamespace is not None:
            if not "default" in self._provcontainer['prefix'].keys():
                self._provcontainer['prefix']['default']=self.defaultnamespace
            else:
                pass # TODO: what if a namespace with prefix 'default' is already defined
        return self._provcontainer


class Account(Record,Bundle):
    
    def __init__(self, identifier, asserter, parentaccount=None, attributes=None):
        if identifier is None:
            raise PROVGraph_Error("The identifier of PROV account record must be given as a string or an PROVQname")
        Record.__init__(self, identifier, attributes, parentaccount)
        self.prov_type = PROV_REC_ACCOUNT

        Bundle.__init__(self)
            
        if isinstance(asserter,PROVQname):
            self.asserter = asserter
        elif isinstance(asserter, (str, unicode)):
            self.asserter = PROVQname(identifier, localname=identifier)
        else:
            raise PROVGraph_Error("The asserter of PROV account record must be given as a string or an PROVQname")
        
        self.asserter = asserter
        self._record_attributes = asserter
        self.parentaccount=parentaccount
        
    def get_record_attributes(self):
        record_attributes = {}
        record_attributes['asserter'] = self.asserter
        return record_attributes
    
    def get_asserter(self):
        return self.asserter
    
    def to_provJSON(self,nsdict):
        Bundle.to_provJSON(self,nsdict)
        self._provcontainer['asserter']=self.asserter.qname(nsdict)
        for attribute,value in self.attributes.items():
            attrtojson = attribute
            if isinstance(attribute, PROVQname):
                attrtojson = attribute.qname(nsdict)
            valuetojson = value
            if isinstance(value, PROVQname):
                valuetojson = value.qname(nsdict)
            self._provcontainer[attrtojson] = valuetojson
        for attribute in self._provcontainer.keys():
            if isinstance(attribute, PROVQname):
                attrtojson = attribute.qname(nsdict)
                self._provcontainer[attrtojson] = self._provcontainer[attribute]
                del self._provcontainer[attribute]
        return self._provcontainer
    

class PROVGraph_Error(Exception):
    def __init__(self, error_message):
        self.error_message = error_message
    def __str__(self):
        return repr(self.error_message)