import datetime


class PROVIdentifier():
    
    def __init__(self,name):
        self.name = name


class PROVURIRef(PROVIdentifier):
    
    def __init__(self,name,namespacename=None,localname=None):
        PROVIdentifier.__init__(self, name)
        self.namespacename = namespacename
        self.localname = localname
        
    def __str__(self):
        return self.name
    
    def qname(self,nsdict):
        rt = self.name
        for prefix,namespacename in nsdict.items():
            if not prefix is 'default':
                if self.namespacename == namespacename:
                    if not self.localname is None:
                        rt = ":".join((prefix, self.localname))
            else:
                rt = self.localname
        return rt
    
    def to_provJSON(self,nsdict):
        rt = [self.qname(nsdict),"xsd:QName"]
        return rt


class PROVNamespace(PROVURIRef):
    
    def __init__(self,namespacename):
        self.namespacename = namespacename
        
    def __getitem__(self,localname):
        return PROVURIRef(self.namespacename+localname,self.namespacename,localname)

        
xsd = PROVNamespace('http://www.w3.org/2001/XMLSchema-datatypes#')


class Record:

    def __init__(self):
        pass
    
    def _get_type_JSON(self,value):
        type = None
        if isinstance(value,float):
            type = xsd["float"]
        if isinstance(value,datetime.datetime):
            type = xsd["dateTime"]
        if isinstance(value,int):
            type = xsd["integer"]
        return type
        
    def _convert_value_JSON(self,value,nsdict):
        valuetojson = value
        if isinstance(value,PROVLiteral) or isinstance(value,PROVURIRef):
            valuetojson=value.to_provJSON(nsdict)
        else:
            type = self._get_type_JSON(value)
            if not type is None:
                valuetojson=[str(value),type.qname(nsdict)]
        return valuetojson


class Element(Record):
    
    def __init__(self,id=None,attributes=None,account=None):
        if not id is None:
            if isinstance(id,PROVURIRef):
                self.identifier = id
            elif isinstance(id,str):
                self.identifier = PROVURIRef(id,'',id)
            else:
                raise PROVGraph_Error("The identifier of PROV record must be given as a string or an PROVURIRef")
        else:
            self.identifer = id
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes
        self.account=account
        self._json = {}
        self._provcontainer = {}
        self._idJSON = None
        
    def to_provJSON(self,nsdict):
        if isinstance(self.identifier,PROVURIRef):
            self._idJSON = self.identifier.qname(nsdict)
        elif self.identifer is None:
            if self._idJSON is None:
                self._idJSON = 'NoID'
        self._json[self._idJSON]=self.attributes
        for attribute in self._json[self._idJSON].keys():
            if isinstance(attribute, PROVURIRef):
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

    def __init__(self,id,attributes,account=None):
        if id is None:
            self.identifier = id
        elif isinstance(id,PROVURIRef):
            self.identifier = id
        elif isinstance(id,str):
            self.identifier = PROVURIRef(id,'',id)
        else:
            raise PROVGraph_Error("The identifier of PROV record must be given as a string or an PROVURIRef")
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes
        self.account=account
        self._json = {}
        self._provcontainer = {}
        self._idJSON = None
    
    def to_provJSON(self,nsdict):
        if isinstance(self.identifier,PROVURIRef):
            self._idJSON = self.identifier.qname(nsdict)
        elif self.identifier is None:
            if self._idJSON is None:
                self._idJSON = 'NoID'
        self._json[self._idJSON]=self.attributes
        for attribute in self._json[self._idJSON].keys():
            if isinstance(attribute, PROVURIRef):
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
        
    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:entity']=self.entity.identifier.qname(nsdict)
        self._json[self._idJSON]['prov:activity']=self.activity.identifier.qname(nsdict)
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
        
    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:entity']=self.entity.identifier.qname(nsdict)
        self._json[self._idJSON]['prov:activity']=self.activity.identifier.qname(nsdict)
        if self.time is not None:
            self._json[self._idJSON]['prov:time']=self._convert_value_JSON(self.time)
        self._provcontainer['used']=self._json
        return self._provcontainer
    

class wasAssociatedWith(Relation):
    
    def __init__(self,activity,agent,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.activity=activity
        self.agent=agent

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:activity']=self.activity.identifier.qname(nsdict)
        self._json[self._idJSON]['prov:agent']=self.agent.identifier.qname(nsdict)
        self._provcontainer['wasAssociatedWith']=self._json
        return self._provcontainer
    

class wasStartedBy(Relation):
    
    def __init__(self,activity,agent,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.activity=activity
        self.agent=agent

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:activity']=self.activity.identifier.qname(nsdict)
        self._json[self._idJSON]['prov:agent']=self.agent.identifier.qname(nsdict)
        self._provcontainer['wasStartedBy']=self._json
        return self._provcontainer
    

class wasEndedBy(Relation):
    
    def __init__(self,activity,agent,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.activity=activity
        self.agent=agent
        
    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:activity']=self.activity.identifier.qname(nsdict)
        self._json[self._idJSON]['prov:agent']=self.agent.identifier.qname(nsdict)
        self._provcontainer['wasEndedBy']=self._json
        return self._provcontainer
    

class hadPlan(Relation):
    
    def __init__(self,agent,entity,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.entity=entity
        self.agent=agent

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:entity']=self.entity.identifier.qname(nsdict)
        self._json[self._idJSON]['prov:agent']=self.agent.identifier.qname(nsdict)
        self._provcontainer['hadPlan']=self._json
        return self._provcontainer
    

class actedOnBehalfOf(Relation):
    
    def __init__(self,subordinate,responsible,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.subordinate=subordinate
        self.responsible=responsible

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:subordinate']=self.subordinate.identifier.qname(nsdict)
        self._json[self._idJSON]['prov:responsible']=self.responsible.identifier.qname(nsdict)
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

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:generatedentity']=self.generatedentity.identifier.qname(nsdict)
        self._json[self._idJSON]['prov:usedentity']=self.usedentity.identifier.qname(nsdict)
        if self.activity is not None:
            self._json[self._idJSON]['prov:activity']=self.activity.identifier.qname(nsdict)
        if self.generation is not None:
            self._json[self._idJSON]['prov:generation']=self.generation.identifier.qname(nsdict)
        if self.usage is not None:
            self._json[self._idJSON]['prov:usage']=self.usage.identifier.qname(nsdict)
        self._provcontainer['wasDerivedFrom']=self._json
        return self._provcontainer
                        

class wasComplementOf(Relation):
    
    def __init__(self,subject,alternate,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.subject=subject
        self.alternate=alternate

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:subject']=self.subject.identifier.qname(nsdict)
        self._json[self._idJSON]['prov:alternate']=self.alternate.identifier.qname(nsdict)
        self._provcontainer['wasComplementOf']=self._json
        return self._provcontainer
            

class hasAnnotation(Relation):
    
    def __init__(self,record,note,id=None,attributes=None,account=None):
        Relation.__init__(self,id,attributes,account)
        self.record=record
        self.note=note

    def to_provJSON(self,nsdict):
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:record']=self.record.identifier.qname(nsdict)
        self._json[self._idJSON]['prov:note']=self.note.identifier.qname(nsdict)
        self._provcontainer['hasAnnotation']=self._json
        return self._provcontainer
    

class PROVLiteral():
    
    def __init__(self,value,type):
        self.value=value
        self.type=type
        self._json = []
        
    def to_provJSON(self,nsdict):
        if isinstance(self.value,PROVURIRef):
            self._json.append(self.value.qname(nsdict))
        else:
            self._json.append(self.value)
        if isinstance(self.type,PROVURIRef):
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
        for element in self._elementlist:
            if element.identifier is None:
                element._idJSON = self._generate_elem_identifer()
            if isinstance(element,Agent):
                if not 'agent' in self._provcontainer.keys():
                    self._provcontainer['agent']=[]
                self._provcontainer['agent'].append(element.identifier)
            for key in element.to_provJSON(nsdict):
                if not key in self._provcontainer.keys():
                    self._provcontainer[key]={}
                self._provcontainer[key].update(element.to_provJSON(nsdict)[key])
        for relation in self._relationlist:
            if relation.identifier is None:
                relation._idJSON = self._generate_rlat_identifer()
            for key in relation.to_provJSON(nsdict):
                if not key in self._provcontainer.keys():
                    self._provcontainer[key]={}
                self._provcontainer[key].update(relation.to_provJSON(nsdict)[key])
        for account in self._accountlist:
            if not 'account' in self._provcontainer.keys():
                self._provcontainer['account']={}
            account._idJSON = account.identifier.qname(nsdict)
            if not account._idJSON in self._provcontainer['account'].keys():
                self._provcontainer['account'][account._idJSON]={}
            self._provcontainer['account'][account._idJSON].update(account.to_provJSON(nsdict))
        return self._provcontainer
                    
    def add_namespace(self,prefix,url):
        #TODO: add prefix validation here
        if prefix is "default":
            raise PROVGraph_Error("The namespace prefix 'default' is a reserved by provpy library")
        else:
            self._namespacedict[prefix]=url
#            self._apply_namespace(prefix, url)

    def _generate_rlat_identifer(self):
        id = "_:RLAT"+str(self._relationkey)
        self._relationkey = self._relationkey + 1
        if self._validate_id(id) is False:
            id = self._generate_rlat_identifer()
        return id

    def _generate_elem_identifer(self):
        id = "_:ELEM"+str(self._elementkey)
        self._relationkey = self._elementkey + 1
        if self._validate_id(id) is False:
            id = self._generate_elem_identifer()
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
                if not isinstance(attribute,PROVURIRef):
                    raise PROVGraph_Error('Bad type for attribute name, expecting str or PROVURIRef.')
#            elif (not attribute.startswith("http://")) and (":" in attribute):
#                self._validate_qname(attribute)
#            if isinstance(literal,PROVLiteral):
#                if literal.type is "xsd:QName":
#                    self._validate_qname(literal.value)

    def _validate_qname(self,qname):
        prefix=qname.split(':')[0]
        if not prefix in self._namespacedict.keys():
            if not prefix in self._implicitnamespace.keys():
                raise PROVGraph_Error('%s Prefix of QName not defined.' % qname)
            
    def _replace_prefix(self,target,oldprefix,newprefix):
        oldprefixcolon = oldprefix + ":"
        newprefixcolon = newprefix + ":"
        if isinstance(target,str):
            if target.startswith(oldprefixcolon):
                target = target.replace(oldprefixcolon,newprefixcolon)
        elif isinstance(target,dict):
            for key in target.keys():
                if not key == 'prefix':
                    target[key] = self._replace_prefix(target[key],oldprefix,newprefix)
                    if key.startswith(oldprefixcolon):
                        newkey = key.replace(oldprefixcolon,newprefixcolon)
                        target[newkey] = target[key]
                        del target[key]
        elif isinstance(target,list):
            for item in target:
                target[target.index(item)] = self._replace_prefix(item,oldprefix,newprefix)
        return target
    

class PROVContainer(Bundle):
    
    def __init__(self,defaultnamespace=None):
        self.defaultnamespace=defaultnamespace
        Bundle.__init__(self)
        
    def set_default_namespace(self,defaultnamespace):
        self.defaultnamespace = defaultnamespace
        
    def to_provJSON(self):
        nsdict = {'default':self.defaultnamespace}
        nsdict.update(self._implicitnamespace)
        nsdict.update(self._namespacedict)
        for account in self._accountlist:
            for prefix,url in account._namespacedict.items():
                if not prefix in nsdict.keys():
                    if not url in nsdict.values():
                        nsdict[prefix]=url
                elif not nsdict[prefix] is url:
                    newprefix = "ns" + str(self._auto_ns_key)
                    self._auto_ns_key = self._auto_ns_key + 1
                    nsdict[newprefix]=url
        Bundle.to_provJSON(self,nsdict)
        self._provcontainer['prefix']={}
        for prefix,url in nsdict.items():
            self._provcontainer['prefix'][prefix]=url

        if not self.defaultnamespace is None:
            if not "default" in self._provcontainer['prefix'].keys():
                self._provcontainer['prefix']['default']=self.defaultnamespace
            else:
                pass # TODO: what if a namespace with prefix 'default' is already defined
            
#        for prefix,url in self._namespacedict.items():
#            self._apply_prefix(self._provcontainer, prefix, url)
#        self._apply_prefix(self._provcontainer, '', self.defaultnamespace)
        return self._provcontainer

    def _apply_prefix(self,target,ns_prefix,ns_URI):
        prefix = ns_prefix
        if not ns_prefix is '':
            prefix = ns_prefix + ":"
        if type(target) == type(str()):
            if target.startswith(ns_URI):
                target = target.replace(ns_URI,prefix)
                if ns_prefix is '':
                    target = [target,"xsd:QName"]
        elif isinstance(target,PROVURIRef):
            if target.namespacename is ns_URI:
                target.qname({ns_prefix:ns_URI})
        elif type(target) == type(dict()):
            for key in target.keys():
                if not key == 'prefix':
                    target[key] = self._apply_prefix(target[key],ns_prefix,ns_URI)
                    newkey = self._apply_prefix(key,ns_prefix,ns_URI)
                    target[newkey] = target[key]
                    del target[key]
        elif type(target) == type(list()):
            for item in target:
                target[target.index(item)] = self._apply_prefix(item,ns_prefix,ns_URI)
        elif isinstance(target,PROVURIRef):
            target = str(target).replace(ns_URI,prefix)
        return target


class Account(Record,Bundle):
    
    def __init__(self,id,asserter,parentaccount=None,attributes=None):
        Record.__init__(self)
        Bundle.__init__(self)
        if isinstance(id,PROVURIRef):
            self.identifier = id
        elif isinstance(id,str):
            self.identifier = PROVURIRef(id,'',id)
        else:
            raise PROVGraph_Error("The identifier of PROV account record must be given as a string or an PROVURIRef")
        if isinstance(asserter,PROVURIRef):
            self.asserter = asserter
        elif isinstance(asserter,str):
            self.asserter = PROVURIRef(id,'',id)
        else:
            raise PROVGraph_Error("The asserter of PROV account record must be given as a string or an PROVURIRef")
        self.asserter = asserter
        self.parentaccount=parentaccount
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes
    
    def to_provJSON(self,nsdict):
        Bundle.to_provJSON(self,nsdict)
        self._provcontainer['prov:asserter']=self.asserter.qname(nsdict)
        for attribute in self._provcontainer.keys():
            if isinstance(attribute, PROVURIRef):
                attrtojson = attribute.qname(nsdict)
                self._provcontainer[attrtojson] = self._provcontainer[attribute]
                del self._provcontainer[attribute]
        for attribute,value in self.attributes.items():
            valuetojson = self._convert_value_JSON(value,nsdict)
            if not valuetojson is None:
                self._provcontainer[attribute]=valuetojson
        return self._provcontainer
    

class PROVGraph_Error(Exception):
    def __init__(self, error_message):
        self.error_message = error_message
    def __str__(self):
        return repr(self.error_message)
    
def is_URI(str):
    if str.startswith('http://'):
        return True
    else:
        return False