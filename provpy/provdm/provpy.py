import datetime


class PROVIdentifier(object):
    
    def __init__(self,name):
        self.name = name


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
                if not prefix == 'default':
                    if not self.localname is None:
                        rt = ":".join((prefix, self.localname))
                else:
                    rt = self.localname
        if not self.namespacename in nsdict.values():
            if not self.prefix is None:
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


class Record:

    def __init__(self):
        pass
    
    def _get_type_JSON(self,value):
        type = None
        if isinstance(value,str) or isinstance(value,bool):
            type = None
        if isinstance(value,float):
            type = xsd["float"]
        if isinstance(value,datetime.datetime):
            type = xsd["dateTime"]
        if isinstance(value,int):
            type = xsd["integer"]
        if isinstance(value,list):
            type = prov["array"]
        return type
        
    def _convert_value_JSON(self,value,nsdict):
        valuetojson = value
        if isinstance(value,PROVLiteral): 
            valuetojson=value.to_provJSON(nsdict)
        elif isinstance(value,PROVQname):
            valuetojson=value.to_provJSON(nsdict)
        else:
            type = self._get_type_JSON(value)
            if not type is None:
                if not type == prov["array"]:
                    valuetojson=[str(value),type.qname(nsdict)]
                else:
                    newvalue = []
                    islist = False
                    for item in value:
                        if isinstance(item,list):
                            islist = True
                        newvalue.append(self._convert_value_JSON(item, nsdict))
                    if islist is False:
                        valuetojson=[newvalue,type.qname(nsdict)]
        return valuetojson


class Element(Record):
    
    def __init__(self,id=None,attributes=None,account=None):
        if not id is None:
            if isinstance(id,PROVQname):
                self.identifier = id
            elif isinstance(id,str):
                self.identifier = PROVQname(id,None,None,id)
            else:
                raise PROVGraph_Error("The identifier of PROV record must be given as a string or an PROVQname")
        else:
            self.identifier = id
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes
        self.account=account
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
            if not valuetojson is None:
                self._json[self._idJSON][attribute] = valuetojson
        return self._json


class Entity(Element):

    def __init__(self,id=None,attributes=None,account=None):
        Element.__init__(self,id,attributes,account)
        
    def to_provJSON(self,nsdict):
        Element.to_provJSON(self,nsdict)
        self._provcontainer['entity']=self._json
        return self._provcontainer
    

class Activity(Element):
    
    def __init__(self,id=None,starttime=None,endtime=None,attributes=None,account=None):
        Element.__init__(self,id,attributes,account)
        self.starttime=starttime
        self.endtime=endtime
        self._attributelist.extend([self.starttime,self.endtime])
        
    def to_provJSON(self,nsdict):
        Element.to_provJSON(self,nsdict)
        if self.starttime is not None:
            self._json[self._idJSON]['prov:starttime']=self._convert_value_JSON(self.starttime,nsdict)
        if self.endtime is not None:
            self._json[self._idJSON]['prov:endtime']=self._convert_value_JSON(self.endtime,nsdict)
        self._provcontainer['activity']=self._json
        return self._provcontainer


class Agent(Entity):

    def __init__(self,id=None,attributes=None,account=None):
        Entity.__init__(self,id,attributes,account)
        
    def to_provJSON(self,nsdict):
        Element.to_provJSON(self,nsdict)
        self._provcontainer['entity']=self._json
        #TODO: How to mark an Agent?
        return self._provcontainer
        

class Note(Element):

    def __init__(self,id=None,attributes=None,account=None):
        Element.__init__(self,id,attributes,account)
        
    def to_provJSON(self,nsdict):
        Element.to_provJSON(self,nsdict)
        self._provcontainer['note']=self._json
        return self._provcontainer


class Relation(Record):

    def __init__(self,id,attributes=None,account=None):
        if id is None:
            self.identifier = id
        elif isinstance(id,PROVQname):
            self.identifier = id
        elif isinstance(id,str):
            self.identifier = PROVQname(id,None,None,id)
        else:
            raise PROVGraph_Error("The identifier of PROV record must be given as a string or an PROVQname")
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes
        self.account=account
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
            if not valuetojson is None:
                self._json[self._idJSON][attribute] = valuetojson
        return self._json
        
    

class wasGeneratedBy(Relation):
    
    def __init__(self,entity,activity,id=None,time=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.entity=entity
        self.activity=activity
        self.time = time
        self._attributelist.extend([self.entity,self.activity,self.time])
        
    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:entity']=self.entity._idJSON
        self._json[self._idJSON]['prov:activity']=self.activity._idJSON
        if self.time is not None:
            self._json[self._idJSON]['prov:time']=self._convert_value_JSON(self.time)
        self._provcontainer['wasGeneratedBy']=self._json
        return self._provcontainer
    

class Used(Relation):
    
    def __init__(self,activity,entity,id=None,time=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.entity=entity
        self.activity=activity
        self.time = time
        self._attributelist.extend([self.entity,self.activity,self.time])
        
    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:entity']=self.entity._idJSON
        self._json[self._idJSON]['prov:activity']=self.activity._idJSON
        if self.time is not None:
            self._json[self._idJSON]['prov:time']=self._convert_value_JSON(self.time)
        self._provcontainer['used']=self._json
        return self._provcontainer
    

class wasAssociatedWith(Relation):
    
    def __init__(self,activity,agent,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.activity=activity
        self.agent=agent
        self._attributelist.extend([self.agent,self.activity])

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:activity']=self.activity._idJSON
        self._json[self._idJSON]['prov:agent']=self.agent._idJSON
        self._provcontainer['wasAssociatedWith']=self._json
        return self._provcontainer
    

class wasStartedBy(Relation):
    
    def __init__(self,activity,agent,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.activity=activity
        self.agent=agent
        self._attributelist.extend([self.agent,self.activity])

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:activity']=self.activity._idJSON
        self._json[self._idJSON]['prov:agent']=self.agent._idJSON
        self._provcontainer['wasStartedBy']=self._json
        return self._provcontainer
    

class wasEndedBy(Relation):
    
    def __init__(self,activity,agent,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.activity=activity
        self.agent=agent
        self._attributelist.extend([self.agent,self.activity])
        
    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:activity']=self.activity._idJSON
        self._json[self._idJSON]['prov:agent']=self.agent._idJSON
        self._provcontainer['wasEndedBy']=self._json
        return self._provcontainer
    

class hadPlan(Relation):
    
    def __init__(self,agent,entity,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.entity=entity
        self.agent=agent
        self._attributelist.extend([self.agent,self.entity])

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:entity']=self.entity._idJSON
        self._json[self._idJSON]['prov:agent']=self.agent._idJSON
        self._provcontainer['hadPlan']=self._json
        return self._provcontainer
    

class actedOnBehalfOf(Relation):
    
    def __init__(self,subordinate,responsible,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.subordinate=subordinate
        self.responsible=responsible
        self._attributelist.extend([self.subordinate,self.responsible])

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:subordinate']=self.subordinate._idJSON
        self._json[self._idJSON]['prov:responsible']=self.responsible._idJSON
        self._provcontainer['actedOnBehalfOf']=self._json
        return self._provcontainer
    

class wasDerivedFrom(Relation):
    
    def __init__(self,generatedentity,usedentity,id=None,activity=None,generation=None,usage=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.generatedentity=generatedentity
        self.usedentity=usedentity
        self.activity=activity
        self.generation=generation
        self.usage=usage
        self._attributelist.extend([self.generatedentity,self.usedentity,self.activity,self.generation,self.usage])

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
    
    def __init__(self,subject,alternate,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.subject=subject
        self.alternate=alternate
        self._attributelist.extend([self.subject,self.alternate])

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:subject']=self.subject._idJSON
        self._json[self._idJSON]['prov:alternate']=self.alternate._idJSON
        self._provcontainer['alternateOf']=self._json
        return self._provcontainer
 
 
class specializationOf(Relation):
    
    def __init__(self,subject,specialization,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.subject=subject
        self.specialization=specialization
        self._attributelist.extend([self.subject,self.specialization])

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:subject']=self.subject._idJSON
        self._json[self._idJSON]['prov:specialization']=self.specialization._idJSON
        self._provcontainer['specializationOf']=self._json
        return self._provcontainer
               

class hasAnnotation(Relation):
    
    def __init__(self,record,note,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.record=record
        self.note=note
        self._attributelist.extend([self.record,self.note])

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:record']=self.record._idJSON
        self._json[self._idJSON]['prov:note']=self.note._idJSON
        self._provcontainer['hasAnnotation']=self._json
        return self._provcontainer
    

class PROVLiteral():
    
    def __init__(self,value,type):
        self.value=value
        self.type=type
        self._json = []
        
    def to_provJSON(self,nsdict):
        self._json = []
        if isinstance(self.value,PROVQname):
            self._json.append(self.value.qname(nsdict))
        else:
            self._json.append(self.value)
        if isinstance(self.type,PROVQname):
            self._json.append(self.type.qname(nsdict))
        else:
            self._json.append(self.type)
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
        self.identifier = "default"
        self._idJSON = None
   
    def add(self,record):
        if isinstance(record,Element):
            self._validate_record(record)
            if record.account is None:
                self._elementlist.append(record)
            elif not record.account.identifier == self.identifier:
                record.account.add(record)
            elif not record in self._elementlist:
                self._elementlist.append(record)
        elif isinstance(record,Relation):
            self._validate_record(record)
            if record.account is None:
                self._relationlist.append(record)
            elif not record.account.identifier == self.identifier:
                record.account.add(record)
            elif not record in self._elementlist:
                self._relationlist.append(record)
        elif isinstance(record,Account):
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
                element._idJSON = element.identifier.qname(nsdict)
        for relation in self._relationlist:
            if relation.identifier is None:
                relation._idJSON = self._generate_rlat_identifier()
            else:
                relation._idJSON = relation.identifier.qname(nsdict)
        for account in self._accountlist:
            account._idJSON = account.identifier.qname(nsdict)
            account._generate_idJSON(nsdict)
                    
    def add_namespace(self,prefix,url):
        #TODO: add prefix validation here
        if prefix is "default":
            raise PROVGraph_Error("The namespace prefix 'default' is a reserved by provpy library")
        else:
            self._namespacedict[prefix]=url
#            self._apply_namespace(prefix, url)

    def _generate_rlat_identifier(self):
        id = "_:RLAT"+str(self._relationkey)
        self._relationkey = self._relationkey + 1
        if self._validate_id(id) is False:
            id = self._generate_rlat_identifier()
        return id

    def _generate_elem_identifier(self):
        id = "_:ELEM"+str(self._elementkey)
        self._elementkey = self._elementkey + 1
        if self._validate_id(id) is False:
            id = self._generate_elem_identifier()
        return id
        
    def _validate_id(self,id):
        valid = True
        for element in self._elementlist:
            if element._idJSON == id:
                valid = False
        for relation in self._relationlist:
            if relation._idJSON == id:
                valid = False
        return valid

    def add_entity(self,id=None,attributes=None,account=None):
        if self._validate_id(id) is False:
            raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            element=Entity(id,attributes,account)
            self.add(element)
            return element
    
    def add_activity(self,id=None,starttime=None,endtime=None,attributes=None,account=None):
        if self._validate_id(id) is False:
            raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            element=Activity(id,starttime,endtime,attributes,account=account)
            self._elementlist.append(element)
            return element
    
    def add_agent(self,id=None,attributes=None,account=None):
        if self._validate_id(id) is False:
            raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            element=Agent(id,attributes,account=account)
            self._elementlist.append(element)
            return element
    
    def add_note(self,id=None,attributes=None,account=None):
        if self._validate_id(id) is False:
            raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            element=Note(id,attributes,account=account)
            self._elementlist.append(element)
            return element

    def add_wasGeneratedBy(self,entity,activity,id=None,time=None,attributes=None,account=None):
        if not id is None:
            if self._validate_id(id) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=wasGeneratedBy(entity,activity,id,time,attributes,account=account)
            self._relationlist.append(relation)
            return relation

    def add_used(self,activity,entity,id=None,time=None,attributes=None,account=None):
        if not id is None:
            if self._validate_id(id) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=Used(activity,entity,id,time,attributes,account=account)
            self._relationlist.append(relation)
            return relation

    def add_wasAssociatedWith(self,activity,agent,id=None,attributes=None,account=None):
        if not id is None:
            if self._validate_id(id) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=wasAssociatedWith(activity,agent,id,attributes,account=account)
            self._relationlist.append(relation)
            return relation

    def add_wasStartedBy(self,activity,agent,id=None,attributes=None,account=None):
        if not id is None:
            if self._validate_id(id) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=wasStartedBy(activity,agent,id,attributes,account=account)
            self._relationlist.append(relation)
            return relation

    def add_wasEndedBy(self,activity,agent,id=None,attributes=None,account=None):
        if not id is None:
            if self._validate_id(id) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=wasEndedBy(activity,agent,id,attributes,account=account)
            self._relationlist.append(relation)
            return relation

    def add_hadPlan(self,agent,entity,id=None,attributes=None,account=None):
        if not id is None:
            if self._validate_id(id) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=hadPlan(agent,entity,id,attributes,account=account)
            self._relationlist.append(relation)
            return relation
    
    def add_actedOnBehalfOf(self,subordinate,responsible,id=None,attributes=None,account=None):
        if not id is None:
            if self._validate_id(id) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=actedOnBehalfOf(subordinate,responsible,id,attributes,account=account)
            self._relationlist.append(relation)
            return relation
      
    def add_wasDerivedFrom(self,generatedentity,usedentity,id=None,activity=None,generation=None,usage=None,attributes=None,account=None):
        if not id is None:
            if self._validate_id(id) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=wasDerivedFrom(generatedentity,usedentity,id,activity,generation,usage,attributes,account=account)
            self._relationlist.append(relation)
            return relation
    
    def add_wasComplementOf(self,subject,alternate,id=None,attributes=None,account=None):
        if not id is None:
            if self._validate_id(id) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=wasComplementOf(subject,alternate,id,attributes,account=account)
            self._relationlist.append(relation)
            return relation
    
    def add_hasAnnotation(self,record,note,id=None,attributes=None,account=None):
        if not id is None:
            if self._validate_id(id) is False:
                raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            relation=hasAnnotation(record,note,id,attributes,account=account)
            self._relationlist.append(relation)
            return relation

    def add_account(self,id,parentaccount=None):
        acc = Account(id,parentaccount)
        self._accountlist.append(acc)

    def _validate_record(self,record):
        pass # Put possible record validation here

    def _validate_qname(self,qname):
        pass # Put possible Qname validation here
            

class PROVContainer(Bundle):
    
    def __init__(self,defaultnamespace=None):
        self.defaultnamespace=defaultnamespace
        Bundle.__init__(self)
        self._visitedrecord = []
        self._nsdict = {}
        
    def set_default_namespace(self,defaultnamespace):
        self.defaultnamespace = defaultnamespace

    def _create_nsdict(self):
        self._auto_ns_key = 0
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

        if not self.defaultnamespace is None:
            if not "default" in self._provcontainer['prefix'].keys():
                self._provcontainer['prefix']['default']=self.defaultnamespace
            else:
                pass # TODO: what if a namespace with prefix 'default' is already defined
        return self._provcontainer


class Account(Record,Bundle):
    
    def __init__(self,id,asserter,parentaccount=None):
        Record.__init__(self)
        Bundle.__init__(self)
        if isinstance(id,PROVQname):
            self.identifier = id
        elif isinstance(id,str):
            self.identifier = PROVQname(id,None,None,id)
        else:
            raise PROVGraph_Error("The identifier of PROV account record must be given as a string or an PROVQname")
        if isinstance(asserter,PROVQname):
            self.asserter = asserter
        elif isinstance(asserter,str):
            self.asserter = PROVQname(id,'',id)
        else:
            raise PROVGraph_Error("The asserter of PROV account record must be given as a string or an PROVQname")
        self.asserter = asserter
        self.parentaccount=parentaccount
    
    def to_provJSON(self,nsdict):
        Bundle.to_provJSON(self,nsdict)
        self._provcontainer['asserter']=self.asserter.qname(nsdict)
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