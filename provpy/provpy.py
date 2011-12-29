import datetime

class Record:

    def __init__(self):
        pass
    
    def _get_type_JSON(self,value):
        type = None
        if isinstance(value,datetime.datetime):
            type = "xsd:dateTime"
        if isinstance(value,int):
            type = "xsd:integer"
        return type
        
    def _convert_value_JSON(self,value):
        valuetojson = value
        if isinstance(value,PROVLiteral):
            valuetojson=value.to_provJSON()
        else:
            type = self._get_type_JSON(value)
            if not type is None:
                valuetojson=[str(value),type]
        return valuetojson


class Element(Record):
    
    def __init__(self,id,attributes=None,account=None):
        self.identifier = id
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes
        self.account=account
        self._json = {}
        self._provcontainer = {}
        
    def to_provJSON(self):
        self._json[self.identifier]=self.attributes
        for attribute,value in self._json[self.identifier].items():
            valuetojson = self._convert_value_JSON(value)
            if not valuetojson is None:
                self._json[self.identifier][attribute] = valuetojson
        return self._json
    

class Entity(Element):

    def __init__(self,id,attributes=None,account=None):
        Element.__init__(self,id,attributes,account)
        
    def to_provJSON(self):
        Element.to_provJSON(self)
        self._provcontainer['entity']=self._json
        return self._provcontainer
    

class Activity(Element):
    
    def __init__(self,id,starttime=None,endtime=None,attributes=None,account=None):
        Element.__init__(self,id,attributes,account)
        self.starttime=starttime
        self.endtime=endtime
        
    def to_provJSON(self):
        Element.to_provJSON(self)
        if self.starttime is not None:
            self._json[self.identifier]['prov:starttime']=self._convert_value_JSON(self.starttime)
        if self.endtime is not None:
            self._json[self.identifier]['prov:endtime']=self._convert_value_JSON(self.endtime)
        self._provcontainer['activity']=self._json
        return self._provcontainer


class Agent(Entity):

    def __init__(self,id,attributes=None,account=None):
        Entity.__init__(self,id,attributes,account)
        
    def to_provJSON(self):
        Element.to_provJSON(self)
        self._provcontainer['entity']=self._json
        return self._provcontainer
        

class Note(Element):

    def __init__(self,id,attributes=None,account=None):
        Element.__init__(self,id,attributes,account)
        
    def to_provJSON(self):
        Element.to_provJSON(self)
        self._provcontainer['note']=self._json
        return self._provcontainer


class Relation(Record):

    def __init__(self,id,attributes,account=None):
        self.identifier = id
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes
        self.account=account
        self._json = {}
        self._provcontainer = {}
    
    def to_provJSON(self):
        self._json[self.identifier]=self.attributes
        for attribute,value in self._json[self.identifier].items():
            valuetojson = self._convert_value_JSON(value)
            if not valuetojson is None:
                self._json[self.identifier][attribute] = valuetojson
        return self._json
        
    

class wasGeneratedBy(Relation):
    
    def __init__(self,entity,activity,id=None,time=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.entity=entity
        self.activity=activity
        self.time = time
        
    def to_provJSON(self):
        Relation.to_provJSON(self)
        self._json[self.identifier]['prov:entity']=self.entity.identifier
        self._json[self.identifier]['prov:activity']=self.activity.identifier
        if self.time is not None:
            self._json[self.identifier]['prov:time']=self._convert_value_JSON(self.time)
        self._provcontainer['wasGeneratedBy']=self._json
        return self._provcontainer
    

class Used(Relation):
    
    def __init__(self,activity,entity,id=None,time=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.entity=entity
        self.activity=activity
        self.time = time
        
    def to_provJSON(self):
        Relation.to_provJSON(self)
        self._json[self.identifier]['prov:entity']=self.entity.identifier
        self._json[self.identifier]['prov:activity']=self.activity.identifier
        if self.time is not None:
            self._json[self.identifier]['prov:time']=self._convert_value_JSON(self.time)
        self._provcontainer['used']=self._json
        return self._provcontainer
    

class wasAssociatedWith(Relation):
    
    def __init__(self,activity,agent,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.activity=activity
        self.agent=agent

    def to_provJSON(self):
        Relation.to_provJSON(self)
        self._json[self.identifier]['prov:activity']=self.activity.identifier
        self._json[self.identifier]['prov:agent']=self.agent.identifier
        self._provcontainer['wasAssociatedWith']=self._json
        return self._provcontainer
    

class wasStartedBy(Relation):
    
    def __init__(self,activity,agent,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.activity=activity
        self.agent=agent

    def to_provJSON(self):
        Relation.to_provJSON(self)
        self._json[self.identifier]['prov:activity']=self.activity.identifier
        self._json[self.identifier]['prov:agent']=self.agent.identifier
        self._provcontainer['wasStartedBy']=self._json
        return self._provcontainer
    

class wasEndedBy(Relation):
    
    def __init__(self,activity,agent,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.activity=activity
        self.agent=agent
        
    def to_provJSON(self):
        Relation.to_provJSON(self)
        self._json[self.identifier]['prov:activity']=self.activity.identifier
        self._json[self.identifier]['prov:agent']=self.agent.identifier
        self._provcontainer['wasEndedBy']=self._json
        return self._provcontainer
    

class hadPlan(Relation):
    
    def __init__(self,agent,entity,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.entity=entity
        self.agent=agent

    def to_provJSON(self):
        Relation.to_provJSON(self)
        self._json[self.identifier]['prov:entity']=self.entity.identifier
        self._json[self.identifier]['prov:agent']=self.agent.identifier
        self._provcontainer['hadPlan']=self._json
        return self._provcontainer
    

class actedOnBehalfOf(Relation):
    
    def __init__(self,subordinate,responsible,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.subordinate=subordinate
        self.responsible=responsible

    def to_provJSON(self):
        Relation.to_provJSON(self)
        self._json[self.identifier]['prov:subordinate']=self.subordinate.identifier
        self._json[self.identifier]['prov:responsible']=self.responsible.identifier
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

    def to_provJSON(self):
        Relation.to_provJSON(self)
        self._json[self.identifier]['prov:generatedentity']=self.generatedentity.identifier
        self._json[self.identifier]['prov:usedentity']=self.usedentity.identifier
        if self.activity is not None:
            self._json[self.identifier]['prov:activity']=self.activity.identifier
        if self.generation is not None:
            self._json[self.identifier]['prov:generation']=self.generation.identifier
        if self.usage is not None:
            self._json[self.identifier]['prov:usage']=self.usage.identifier
        self._provcontainer['wasDerivedFrom']=self._json
        return self._provcontainer
                        

class wasComplementOf(Relation):
    
    def __init__(self,subject,alternate,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.subject=subject
        self.alternate=alternate

    def to_provJSON(self):
        Relation.to_provJSON(self)
        self._json[self.identifier]['prov:subject']=self.subject.identifier
        self._json[self.identifier]['prov:alternate']=self.alternate.identifier
        self._provcontainer['wasComplementOf']=self._json
        return self._provcontainer
            

class hasAnnotation(Relation):
    
    def __init__(self,record,note,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.record=record
        self.note=note

    def to_provJSON(self):
        Relation.to_provJSON(self)
        self._json[self.identifier]['prov:record']=self.record.identifier
        self._json[self.identifier]['prov:note']=self.note.identifier
        self._provcontainer['hasAnnotation']=self._json
        return self._provcontainer
    

class PROVLiteral():
    
    def __init__(self,value,type):
        self.value=value
        self.type=type
        self._json = []
        
    def to_provJSON(self):
        self._json.append(self.value)
        self._json.append(self.type)
        return self._json


class Bundle():
    
    def __init__(self):
        self._provcontainer = {}
        self._elementlist = []
        self._relationlist = []
        self._namespacedict = {}
        self._implicitnamespace = {'prov':'http://www.w3.org/ns/prov-dm/',
                                   'xsd' :'http://www.w3.org/2001/XMLSchema-datatypes'}
        self._accountlist = []
        self._relationkey = 0
        self.identifier = "default"
   
    def add(self,record):
        if isinstance(record,Element):
            self._validate_record(record)
            if record.account is None:
                self._elementlist.append(record)
            elif record.account.identifier is not self.identifier:
                record.account.add(record)
            elif not record in self._elementlist:
                self._elementlist.append(record)
        elif isinstance(record,Relation):
            self._validate_record(record)
            if record.account is None:
                self._relationlist.append(record)
            elif record.account.identifier is not self.identifier:
                record.account.add(record)
            elif not record in self._elementlist:
                self._relationlist.append(record)
        elif isinstance(record,Account):
            self._accountlist.append(record)
            
    def to_provJSON(self):
        for element in self._elementlist:
            if isinstance(element,Agent):
                if not 'agent' in self._provcontainer.keys():
                    self._provcontainer['agent']=[]
                self._provcontainer['agent'].append(element.identifier)
            for key in element.to_provJSON():
                if not key in self._provcontainer.keys():
                    self._provcontainer[key]={}
                self._provcontainer[key].update(element.to_provJSON()[key])
        for relation in self._relationlist:
            if relation.identifier is None:
                relation.identifier = self._generate_identifer()
            for key in relation.to_provJSON():
                if not key in self._provcontainer.keys():
                    self._provcontainer[key]={}
                self._provcontainer[key].update(relation.to_provJSON()[key])
        for account in self._accountlist:
            if not 'account' in self._provcontainer.keys():
                self._provcontainer['account']={}
            if not account.identifier in self._provcontainer['account'].keys():
                self._provcontainer['account'][account.identifier]={}
            self._provcontainer['account'][account.identifier].update(account.to_provJSON())
        return self._provcontainer
                    
    def add_namespace(self,prefix,url):
        #TODO: add prefix validation here
        self._namespacedict[prefix]=url
        self._apply_namespace(prefix, url)
    
    def _apply_namespace(self,prefix,url):
        pass

    def _generate_identifer(self):
        id = "_:RLAT"+str(self._relationkey)
        self._relationkey = self._relationkey + 1
        if self._validate_id(id) is False:
            id = self._generate_identifer()
        return id
    
    def _validate_id(self,id):
        valid = True
        for element in self._elementlist:
            if element.identifier == id:
                valid = False
        for relation in self._relationlist:
            if relation.identifier == id:
                valid = False
        return valid

    def add_entity(self,id,attributes=None,account=None):
        if self._validate_id(id) is False:
            raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            element=Entity(id,attributes,account)
            self.add(element)
            return element
    
    def add_activity(self,id,starttime=None,endtime=None,attributes=None,account=None):
        if self._validate_id(id) is False:
            raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            element=Activity(id,starttime,endtime,attributes,account=account)
            self._elementlist.append(element)
            return element
    
    def add_agent(self,id,attributes=None,account=None):
        if self._validate_id(id) is False:
            raise PROVGraph_Error('Identifier conflicts with existing assertions')
        else:
            element=Agent(id,attributes,account=account)
            self._elementlist.append(element)
            return element
    
    def add_note(self,id,attributes=None,account=None):
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
        for attribute,literal in record.attributes.items():
            if not isinstance(attribute,str):
                raise PROVGraph_Error('Bad type for attribute name, expecting str.')
            elif (not attribute.startswith("http://")) and (":" in attribute):
                self._validate_qname(attribute)
            if isinstance(literal,PROVLiteral):
                if literal.type is "xsd:QName":
                    self._validate_qname(literal.value)

    def _validate_qname(self,qname):
        prefix=qname.split(':')[0]
        if not prefix in self._namespacedict.keys():
            if not prefix in self._implicitnamespace.keys():
                raise PROVGraph_Error('%s Prefix of QName not defined.' % qname)
    

class PROVContainer(Bundle):
    
    def __init__(self):
        Bundle.__init__(self)
        
    def to_provJSON(self):
        Bundle.to_provJSON(self)
        self._provcontainer['prefix']={}
        for prefix,url in self._namespacedict.items():
            self._provcontainer['prefix'][prefix]=url
        return self._provcontainer


class Account(Record,Bundle):
    
    def __init__(self,id,asserter,parentaccount=None,attributes=None):
        Record.__init__(self)
        Bundle.__init__(self)
        self.identifier = id
        self.asserter = asserter
        self.parentaccount=parentaccount
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes
    
    def to_provJSON(self):
        Bundle.to_provJSON(self)
        self._provcontainer['prov:asserter']=self.asserter
        for attr,value in self.attributes.items():
            valuetojson = self._convert_value_JSON(value)
            if not valuetojson is None:
                self._provcontainer[attr]=valuetojson
        return self._provcontainer
    

class PROVGraph_Error(Exception):
    def __init__(self, error_message):
        self.error_message = error_message
    def __str__(self):
        return repr(self.error_message)
    
