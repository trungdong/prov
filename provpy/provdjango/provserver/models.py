from django.db import models

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

class Record(models.Model):
    rec_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    rec_type = models.SmallIntegerField(choices=PROV_RECORD_TYPES, db_index=True)
    account = models.ForeignKey('Account', related_name='records', null=True, blank=True, db_index=True)
    attributes = models.ManyToManyField('self', through='RecordAttribute', symmetrical=False, related_name='references')
    
    
    #@staticmethod

class AccountManager(models.Manager):
    def get_query_set(self):
        return super(AccountManager, self).get_query_set().filter(prov_type=PROV_REC_ACCOUNT)
    
class Account(Record):
    objects = AccountManager()
    class Meta:
        proxy = True
    
    def get_records(self):
        return Record.objects.filter(account=self)
    
    
class RecordAttribute(models.Model):
    record = models.ForeignKey(Record, related_name='from_records', db_index=True)
    attribute = models.ForeignKey(Record, related_name='to_records')
    prov_type = models.SmallIntegerField(choices=PROV_RECORD_ATTRIBUTES, db_index=True)

class LiteralAttribute(models.Model):
    record = models.ForeignKey(Record, related_name='literals', db_index=True)
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    datatype = models.CharField(max_length=255)