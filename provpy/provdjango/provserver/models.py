from django.db import models
import uuid
from provdm.provdm.model import *

PROV_RECORD_ATTRIBUTES = (
    # Relations properties
    (0, u'prov:record'),
    (1, u'prov:entity'),
    (2, u'prov:activity'),
    (3, u'prov:agent'),
    (4, u'prov:note'),
    (5, u'prov:plan'),
    (6, u'prov:subordinate'),
    (7, u'prov:responsible'),
    (8, u'prov:generatedEntity'),
    (9, u'prov:usedEntity'),
    (10, u'prov:generation'),
    (11, u'prov:usage'),
    (12, u'prov:alternate'),
    (13, u'prov:specialization'),
    # Account properties
    (100, u'prov:namespace'),
    (101, u'prov:asserter'),
) 

class PDNamespace(models.Model):
    prefix = models.CharField(max_length=255, db_index=True)
    uri  = models.CharField(max_length=255, db_index=True)


class PDRecord(models.Model):
    rec_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    rec_type = models.SmallIntegerField(choices=PROV_RECORD_TYPES, db_index=True)
    account = models.ForeignKey('PDAccount', related_name='records', null=True, blank=True, db_index=True)

class Attribute(models.Model):
    record = models.ForeignKey(PDRecord, related_name='attributes', db_index=True)
    prov_type = models.SmallIntegerField(choices=PROV_RECORD_ATTRIBUTES, null=True, blank=True, db_index=True)
    attr_type = models.CharField(max_length=255, null=True, blank=True)
    value = models.CharField(max_length=255, null=True, blank=True)

class PDAccount(PDRecord):
    asserter = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    namespaces = models.ManyToManyField(PDNamespace, related_name='accounts')
    
    @staticmethod
    def create(account_id, asserter_id):
        return PDAccount.objects.create(rec_id=account_id, rec_type=PROV_REC_ACCOUNT, asserter=asserter_id)
    
    def add_namespace(self, prefix, uri):
        namespace = PDNamespace.objects.create(prefix=prefix, uri=uri)
        self.namespaces.add(namespace)
        
    def add_sub_account(self, account_record):
        pass
    
    def get_namespaces(self):
        results = {}
        for namespace in self.namespaces.all():
            results[namespace.prefix] = namespace.uri
        return results
        
    def get_PROVContainer(self):
        return build_PROVContainer(self)
    

#class PDNamespace(models.Model):
#    rec_id = models.CharField(max_length=255, db_index=True)
#    uri  = models.CharField(max_length=255, db_index=True)
#
#class PDIdentifier(models.Model):
#    name = models.CharField(max_length=255, db_index=True)
#    namespace = models.ForeignKey(PDNamespace, related_name='identifiers', null=True, blank=True)
#    
#    @staticmethod
#    def create(identifier):
#        ids = PDIdentifier.objects.filter(name=identifier) 
#        if ids.exist():
#            return ids[0]
#        else:
#            return PDIdentifier.objects.create(name=identifier)
#
#class PDRecord(models.Model):
#    rec_id = models.ForeignKey(PDIdentifier, related_name='records', null=True, blank=True)
#    rec_type = models.SmallIntegerField(choices=PROV_RECORD_TYPES, db_index=True)
#    account = models.ForeignKey('PDAccount', related_name='records', null=True, blank=True, db_index=True)
#    attributes = models.ManyToManyField('self', through='RecordAttribute', symmetrical=False, related_name='references')
#    
#    @staticmethod
#    def create(record, account):
#        if isinstance(record, Account):
#            pass
#        else:
#            PDRecord.objects.create(rec_id=record.get_record_id(), rec_type=record.get_prov_type(), account=account)
#
#class PDAccount(PDRecord):
#    asserter = models.ForeignKey(PDIdentifier, related_name='accounts', null=True, blank=True)
#    namespaces = models.ManyToManyField(PDNamespace, related_name='accounts')
#    
#    def __init__(self, **kwargs):
#        kwargs['rec_type'] = PROV_REC_ACCOUNT
#        PDRecord.__init__(self, **kwargs)
#        
##    def set_asserter(self, asserter):
##        self.literals.create(name='prov:asserter', value=asserter, datatype='xsd:anyURI')
#    @staticmethod
#    def create(account_id, asserter):
#        if isinstance(account_id, PDIdentifier):
#            identifier = account_id
#        else:
#            identifier = PDIdentifier.create(account_id)
#        if isinstance(asserter, PDIdentifier):
#            asserter_id = asserter
#        else:
#            asserter_id = PDIdentifier.create(asserter)
#        return PDAccount.objects.create(rec_id=identifier, asserter=asserter_id)
#    
#    @staticmethod    
#    def create_sub_account(pd_account, subaccount):
#        pass
#        
#    def get_records(self):
#        return PDRecord.objects.filter(account=self)
#    
#    def get_prov_graph(self):
#        records = self.get_records()
#        graph = PROVContainer()
#        for record in records:
#            add_ProvDM_Record(graph, record)
#            
#            
#def add_ProvDM_Record(graph, record):
#    rec_type = record.rec_type
#    # TODO Get all the record attributes here
#    if rec_type == PROV_REC_ENTITY:
#        graph.add_entity(record.rec_id)
#    elif rec_type == PROV_REC_ACTIVITY:
#        graph.add_activity(record.rec_id)
#    elif rec_type == PROV_REC_AGENT:
#        graph.add_agent(record.rec_id)
#    elif rec_type == PROV_REC_ANNOTATION:
#        graph.add_note(record.rec_id)
#    else:
#        # Unsupported type
#        # TODO Raise an error here
#        pass
#    
#class RecordAttribute(models.Model):
#    record = models.ForeignKey(PDRecord, related_name='from_records', db_index=True)
#    attribute = models.ForeignKey(PDRecord, related_name='to_records')
#    prov_type = models.SmallIntegerField(choices=PROV_RECORD_ATTRIBUTES, db_index=True)
#
#class LiteralAttribute(models.Model):
#    record = models.ForeignKey(PDRecord, related_name='literals', db_index=True)
#    name = models.CharField(max_length=255)
#    value = models.CharField(max_length=255)
#    datatype = models.ForeignKey(PDIdentifier, related_name='literals', null=True, blank=True)
#    

def create_record(prov_record, account, record_map):
    prov_type = prov_record.get_prov_type()
    record_id = prov_record.get_record_id()
    record_uri = record_id.uri() if record_id is not None else None
    if prov_type <> PROV_REC_ACCOUNT:
        pdrecord = PDRecord.objects.create(rec_id=record_uri, rec_type=prov_type, account=account)
        record_map[prov_record] = pdrecord
    else:
        asserter_uri = prov_record.get_asserter().uri()
        pdrecord = PDAccount.objects.create(rec_id=record_id, rec_type=prov_type, account=account, asserter=asserter_uri)
        record_map[prov_record] = pdrecord
        save_account(pdrecord, prov_record.get_records(), record_map)
        
    # TODO add all attributes here
    attributes = prov_record.get_all_attributes()
    for (name, value) in attributes.iteritems():
        Attribute.objects.create(record=pdrecord, attr_type=str(name), value=str(value))
    return pdrecord

def save_account(account, records, record_map):
    for record in records:
        if record not in record_map:
            create_record(record, account, record_map)

def save_records(prov_graph):
    account_id = uuid.uuid4().urn
    
    account = PDAccount.create(account_id, '#me')    
    namespaces = prov_graph.get_namespaces()
    for (prefix,uri) in namespaces.iteritems():
        account.add_namespace(prefix, uri)
    default_namespace_uri = prov_graph.get_default_namespace()
    if default_namespace_uri:
        account.add_namespace('default', default_namespace_uri)
     
    records = prov_graph.get_records()
    record_map = {}
    save_account(account, records, record_map)
    return account
    
def build_PROVContainer(account):
    graph = PROVContainer()
    namespaces = account.get_namespaces()
    for (prefix, uri) in namespaces.iteritems():
        if prefix == 'default':
            graph.set_default_namespace(uri)
        else:
            graph.add_namespace(prefix, uri)
    
    record_map = {}
    records = account.records.order_by('rec_type')
    for record in records:
        rec_type = record.rec_type
        rec_id = record.rec_id
        attributes = record.attributes.values_list('attr_type', 'value')
        attr_map = {}
        for (name, value) in attributes:
            attr_map[name] = value 
        
        if rec_type == PROV_REC_ACCOUNT:
            # Do something special with account
            pass
        elif rec_type == PROV_REC_ENTITY:
            graph.add_entity(rec_id, attributes=attr_map)
        elif rec_type == PROV_REC_ACTIVITY:
#            startTime = datetime.strptime(attr_map.startTime, 'YYYY-MM-DD HH:MM:SS.mmmmmm') if 'time' in attr_map else None 
#            endTime = datetime.strptime(attr_map.endTime, 'YYYY-MM-DD HH:MM:SS.mmmmmm') if 'time' in attr_map else None
            graph.add_activity(rec_id, attributes=attr_map)
        elif rec_type == PROV_REC_GENERATION:
            pass
            
    return graph
    