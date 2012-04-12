# Copyright (c) 2012, University of Southampton.

"""
The Provpy library - common.py contains classes that map 
to the provenance records defined in the common relation 
part of the PROV-DM specification (http://www.w3.org/TR/prov-dm/).
"""

from core import *

class tracedTo(Relation):
    """ The class that defines the tracedTo record """
    def __init__(self, entity, ancestor, identifier=None, attributes=None, account=None):
        """ For initialisation, the entity and ancestor are required, identifier,
        account and attributes are optional arguments """
        Relation.__init__(self, identifier, attributes, account)
#        self.prov_type = PROV_REC_GENERATION
        self.entity=entity
        self.ancestor=ancestor
        self._attributelist.extend([self.entity,self.ancestor])
        
    def get_record_attributes(self):
        """ returns the record attributes: entity and ancestor. """
        record_attributes = {}
        record_attributes['entity'] = self.entity
        record_attributes['ancestor'] = self.ancestor
        return record_attributes
    
    def to_provJSON(self,nsdict):
        """ generates the PROV JSON serialization of the record """
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:entity']=self.entity._idJSON
        self._json[self._idJSON]['prov:ancestor']=self.ancestor._idJSON
        self._provcontainer['tracedTo']=self._json
        return self._provcontainer

class wasInformedBy(Relation):
    """ The class that defines the wasInformedBy record """
    def __init__(self, informed, informant, identifier=None, attributes=None, account=None):
        """ For initialisation, the informed and informant are required, identifier,
        account and attributes are optional arguments """
        Relation.__init__(self, identifier, attributes, account)
#        self.prov_type = PROV_REC_GENERATION
        self.informed=informed
        self.informant=informant
        self._attributelist.extend([self.informed,self.informant])
        
    def get_record_attributes(self):
        """ returns the record attributes: informed and informant. """
        record_attributes = {}
        record_attributes['informed'] = self.informed
        record_attributes['informant'] = self.informant
        return record_attributes
    
    def to_provJSON(self,nsdict):
        """ generates the PROV JSON serialization of the record """
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:informed']=self.informed._idJSON
        self._json[self._idJSON]['prov:informant']=self.informant._idJSON
        self._provcontainer['wasInformedBy']=self._json
        return self._provcontainer

class wasStartedBy(Relation):
    """ The class that defines the wasStartedBy record (note the difference between this and the
    core.wasStartedBy record)"""
    def __init__(self, started, starter, identifier=None, attributes=None, account=None):
        """ For initialisation, the started and starter are required, identifier,
        account and attributes are optional arguments """
        Relation.__init__(self, identifier, attributes, account)
#        self.prov_type = PROV_REC_GENERATION
        self.started=started
        self.starter=starter
        self._attributelist.extend([self.started,self.starter])
        
    def get_record_attributes(self):
        """ returns the record attributes: started and starter. """
        record_attributes = {}
        record_attributes['started'] = self.started
        record_attributes['starter'] = self.starter
        return record_attributes
    
    def to_provJSON(self,nsdict):
        """ generates the PROV JSON serialization of the record """
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:started']=self.started._idJSON
        self._json[self._idJSON]['prov:starter']=self.starter._idJSON
        self._provcontainer['wasStartedBy']=self._json
        return self._provcontainer

class wasRevisionOf(Relation):
    """ The class that defines the wasRevisionOf record """
    def __init__(self, newer, older, responsibility=None, identifier=None, attributes=None, account=None):
        """ For initialisation, the newer and older entities are required, responsibility, identifier,
        account and attributes are optional arguments """
        Relation.__init__(self, identifier, attributes, account)
#        self.prov_type = PROV_REC_GENERATION
        self.newer=newer
        self.older=older
        self.responsibility=responsibility
        self._attributelist.extend([self.newer,self.older])
        if self.responsibility is not None:
            self._attributelist.extend([self.responsibility])
        
    def get_record_attributes(self):
        """ returns the record attributes: newer and older,
        and if available the responsibility. """
        record_attributes = {}
        record_attributes['newer'] = self.newer
        record_attributes['older'] = self.older
        if self.responsibility is not None:
            record_attributes['responsibility'] = self.responsibility
        return record_attributes
    
    def to_provJSON(self,nsdict):
        """ generates the PROV JSON serialization of the record """
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:newer']=self.newer._idJSON
        self._json[self._idJSON]['prov:older']=self.older._idJSON
        if self.responsibility is not None:
            self._json[self._idJSON]['prov:responsibility']=self.responsibility._idJSON
        self._provcontainer['wasRevisionOf']=self._json
        return self._provcontainer
    
class wasAttributedTo(Relation):
    """ The class that defines the wasAttributedTo record """
    def __init__(self, entity, agent, identifier=None, attributes=None, account=None):
        """ For initialisation, the entity and agent are required, identifier,
        account and attributes are optional arguments """
        Relation.__init__(self, identifier, attributes, account)
#        self.prov_type = PROV_REC_GENERATION
        self.entity=entity
        self.agent=agent
        self._attributelist.extend([self.entity,self.agent])
        
    def get_record_attributes(self):
        """ returns the record attributes: entity and agent. """
        record_attributes = {}
        record_attributes['entity'] = self.entity
        record_attributes['agent'] = self.agent
        return record_attributes
    
    def to_provJSON(self,nsdict):
        """ generates the PROV JSON serialization of the record """
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:entity']=self.entity._idJSON
        self._json[self._idJSON]['prov:agent']=self.agent._idJSON
        self._provcontainer['wasAttributedTo']=self._json
        return self._provcontainer
    
class wasQuotedFrom(Relation):
    """ The class that defines the wasQuotedFrom record """
    def __init__(self, quote, quoted, quoterAgent=None, quotedAgent=None, identifier=None, attributes=None, account=None):
        """ For initialisation, the quote and quoted entities are required, 
        quoterAgent, quotedAgent, identifier, account and attributes are optional arguments """
        Relation.__init__(self, identifier, attributes, account)
#        self.prov_type = PROV_REC_GENERATION
        self.quote=quote
        self.quoted=quoted
        self.quoterAgent=quoterAgent
        self.quotedAgent=quotedAgent
        self._attributelist.extend([self.quote,self.older])
        if self.quoterAgent is not None:
            self._attributelist.extend([self.quoterAgent])
        if self.quotedAgent is not None:
            self._attributelist.extend([self.quotedAgent])
        
    def get_record_attributes(self):
        """ returns the record attributes: quote and quoted,
        and if available, the quoterAgent and the quotedAgent. """
        record_attributes = {}
        record_attributes['quote'] = self.quote
        record_attributes['quoted'] = self.quoted
        if self.quoterAgent is not None:
            record_attributes['quoterAgent'] = self.quoterAgent
        if self.quotedAgent is not None:
            record_attributes['quotedAgent'] = self.quotedAgent
        return record_attributes
    
    def to_provJSON(self,nsdict):
        """ generates the PROV JSON serialization of the record """
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:quote']=self.quote._idJSON
        self._json[self._idJSON]['prov:quoted']=self.quoted._idJSON
        if self.quoterAgent is not None:
            self._json[self._idJSON]['prov:quoterAgent']=self.quoterAgent._idJSON
        if self.quotedAgent is not None:
            self._json[self._idJSON]['prov:quotedAgent']=self.quotedAgent._idJSON
        self._provcontainer['wasQuotedFrom']=self._json
        return self._provcontainer
    
class wasSummaryOf(Relation):
    """ The class that defines the wasSummaryOf record """
    def __init__(self, summarizedEntity, fullEntity, identifier=None, attributes=None, account=None):
        """ For initialisation, the summarizedEntity and fullEntity are required, identifier,
        account and attributes are optional arguments """
        Relation.__init__(self, identifier, attributes, account)
#        self.prov_type = PROV_REC_GENERATION
        self.summarizedEntity=summarizedEntity
        self.fullEntity=fullEntity
        self._attributelist.extend([self.summarizedEntity,self.agent])
        
    def get_record_attributes(self):
        """ returns the record attributes: summarizedEntity and fullEntity. """
        record_attributes = {}
        record_attributes['summarizedEntity'] = self.summarizedEntity
        record_attributes['fullEntity'] = self.fullEntity
        return record_attributes
    
    def to_provJSON(self,nsdict):
        """ generates the PROV JSON serialization of the record """
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:summarizedEntity']=self.summarizedEntity._idJSON
        self._json[self._idJSON]['prov:fullEntity']=self.fullEntity._idJSON
        self._provcontainer['wasSummaryOf']=self._json
        return self._provcontainer
    
class hadOriginalSource(Relation):
    """ The class that defines the hadOriginalSource record """
    def __init__(self, entity, source, identifier=None, attributes=None, account=None):
        """ For initialisation, the entity and source are required, identifier,
        account and attributes are optional arguments """
        Relation.__init__(self, identifier, attributes, account)
#        self.prov_type = PROV_REC_GENERATION
        self.entity=entity
        self.source=source
        self._attributelist.extend([self.entity,self.source])
        
    def get_record_attributes(self):
        """ returns the record attributes: entity and source. """
        record_attributes = {}
        record_attributes['entity'] = self.entity
        record_attributes['source'] = self.source
        return record_attributes
    
    def to_provJSON(self,nsdict):
        """ generates the PROV JSON serialization of the record """
        Relation.to_provJSON(self,nsdict)
        self._json[self._idJSON]['prov:entity']=self.entity._idJSON
        self._json[self._idJSON]['prov:source']=self.source._idJSON
        self._provcontainer['hadOriginalSource']=self._json
        return self._provcontainer
    
