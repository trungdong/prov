from django.db import models
import uuid
from provpy import *

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

class ProvDJRecord(models.Model):
    rec_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    rec_type = models.SmallIntegerField(choices=PROV_RECORD_TYPES, db_index=True)
    account = models.ForeignKey('ProvDJAccount', related_name='records', null=True, blank=True, db_index=True)
    attributes = models.ManyToManyField('self', through='RecordAttribute', symmetrical=False, related_name='references')
    
    @staticmethod
    def create(record, account):
        if isinstance(record, Account):
            pass
        else:
            ProvDJRecord.objects.create(rec_id=record.get_record_id(), rec_type=record.get_prov_type(), account=account)

class ProvDJAccountManager(models.Manager):
    def get_query_set(self):
        return super(ProvDJAccountManager, self).get_query_set().filter(rec_type=PROV_REC_ACCOUNT)
    
class ProvDJAccount(ProvDJRecord):
#    objects = ProvDJAccountManager()
    class Meta:
        proxy = True
    
    def __init__(self, **kwargs):
        kwargs['rec_type'] = PROV_REC_ACCOUNT
        ProvDJRecord.__init__(self, **kwargs)
        
    def set_asserter(self, asserter):
        self.literals.create(name='prov:asserter', value=asserter, datatype='xsd:anyURI')
    
    @staticmethod    
    def create(account, subaccount):
        pass
        
    def get_records(self):
        return Record.objects.filter(account=self)
    
    def get_prov_graph(self):
        records = self.get_records()
        graph = PROVContainer()
        for record in records:
            add_ProvDM_Record(graph, record)
            
            
def add_ProvDM_Record(graph, record):
    rec_type = record.rec_type
    # TODO Get all the record attributes here
    if rec_type == PROV_REC_ENTITY:
        graph.add_entity(record.rec_id)
    elif rec_type == PROV_REC_ACTIVITY:
        graph.add_activity(record.rec_id)
    elif rec_type == PROV_REC_AGENT:
        graph.add_agent(record.rec_id)
    elif rec_type == PROV_REC_ANNOTATION:
        graph.add_note(record.rec_id)
    else:
        # Unsupported type
        # TODO Raise an error here
        pass
    
class RecordAttribute(models.Model):
    record = models.ForeignKey(ProvDJRecord, related_name='from_records', db_index=True)
    attribute = models.ForeignKey(ProvDJRecord, related_name='to_records')
    prov_type = models.SmallIntegerField(choices=PROV_RECORD_ATTRIBUTES, db_index=True)

class LiteralAttribute(models.Model):
    record = models.ForeignKey(ProvDJRecord, related_name='literals', db_index=True)
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    datatype = models.CharField(max_length=255)
    
def save_records(prov_graph):
    account_id = uuid.uuid4()
    account = ProvDJAccount.objects.create(rec_id=account_id)    
    account.set_asserter('#me')
    
    records = prov_graph.get_records()
    for record in records:
        ProvDJRecord.create(record, account)
        
def test_model():
    from provpyexample_Elements import examplegraph
    save_records(examplegraph)

