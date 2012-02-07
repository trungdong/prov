"""Module docstring to go here"""
from django.db import models
import uuid
import model.core as provdm

# Constants
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

PROV_RECORD_ATTR_MAP = dict((name, value) for (value, name) in PROV_RECORD_ATTRIBUTES)
PROV_RECORD_LITERAL_MAP = dict((name, value) for (value, name) in PROV_RECORD_LITERALS)

# Interface functions
def save_records(prov_graph):
    # Generate a unique id for a new account to contain the provenance graph
    account_id = uuid.uuid4().urn
    account = PDAccount.create(account_id, '#me')
    # Save all the namespaces for future QName recreation
    namespaces = prov_graph.get_namespaces()
    for (prefix,uri) in namespaces.iteritems():
        account.add_namespace(prefix, uri)
    # and the default namespace as well
    default_namespace_uri = prov_graph.get_default_namespace()
    if default_namespace_uri:
        account.add_namespace('default', default_namespace_uri)
     
    # An empty map to keep track of the visited records
    record_map = {}
    # Getting all the individual records containted in the graph
    records = prov_graph.get_records()
    # and save them
    save_account(account, records, record_map)
    #Return the account
    return account


# Classes
class PDNamespace(models.Model):
    prefix = models.CharField(max_length=255, db_index=True)
    uri  = models.CharField(max_length=255, db_index=True)


class PDRecord(models.Model):
    rec_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    rec_type = models.SmallIntegerField(choices=provdm.PROV_RECORD_TYPES, db_index=True)
    account = models.ForeignKey('PDAccount', related_name='records', null=True, blank=True, db_index=True)
    attributes = models.ManyToManyField('self', through='RecordAttribute', symmetrical=False, related_name='references')


class RecordAttribute(models.Model):
    record = models.ForeignKey(PDRecord, related_name='from_records', db_index=True)
    value = models.ForeignKey(PDRecord, related_name='to_records')
    prov_type = models.SmallIntegerField(choices=PROV_RECORD_ATTRIBUTES, db_index=True)


class LiteralAttribute(models.Model):
    record = models.ForeignKey(PDRecord, related_name='literals', db_index=True)
    prov_type = models.SmallIntegerField(choices=PROV_RECORD_LITERALS, null=True, blank=True, db_index=True)
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    datatype = models.CharField(max_length=255, null=True, blank=True)


class PDAccount(PDRecord):
    asserter = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    namespaces = models.ManyToManyField(PDNamespace, related_name='accounts')
    
    @staticmethod
    def create(account_id, asserter_id):
        return PDAccount.objects.create(rec_id=account_id, rec_type=provdm.PROV_REC_ACCOUNT, asserter=asserter_id)
    
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


# Internal functions
def create_record(prov_record, account, record_map):
    prov_type = prov_record.get_prov_type()
    record_id = prov_record.get_record_id()
    record_uri = record_id.uri() if record_id is not None else None
    if prov_type <> provdm.PROV_REC_ACCOUNT:
        # Create a normal record
        pdrecord = PDRecord.objects.create(rec_id=record_uri, rec_type=prov_type, account=account)
        record_map[prov_record] = pdrecord
    else:
        # Create an account record
        asserter_uri = prov_record.get_asserter().uri()
        pdrecord = PDAccount.objects.create(rec_id=record_id, rec_type=prov_type, account=account, asserter=asserter_uri)
        record_map[prov_record] = pdrecord
        # Recursive call to save this account
        save_account(pdrecord, prov_record.get_records(), record_map)
        
    # TODO add all attributes here
    attributes = prov_record.get_all_attributes()
    for (name, value) in attributes.iteritems():
        # TODO This assume all prov attributes use QName strings, e.g. "prov:entity"
        if name in PROV_RECORD_ATTR_MAP:
            # Create a linked attribute's record
            if isinstance(value, provdm.Record):
                if value not in record_map:
                    # The record in value needed to be saved first
                    # Assumption: no bidirectional relationship between records; otherwise, duplicated RecordAttribute will be created
                    # Recursive call to create the other record
                    # TODO: Check if the other record is in another account
                    other_record = create_record(value, account, record_map)
                else:
                    other_record = record_map[value]
                RecordAttribute.objects.create(record=pdrecord, value=other_record, prov_type=PROV_RECORD_ATTR_MAP[name])
            else:
                raise Exception('Expected a PROV Record for %s. Got %s.' % name )
        else:
            # Create a literal attribute
            attr_name = name.uri() if isinstance(name, provdm.PROVIdentifier) else str(name)
            if isinstance(value, provdm.PROVLiteral):
                LiteralAttribute.objects.create(record=pdrecord, prov_type=PROV_RECORD_LITERAL_MAP.get(attr_name),
                                                name=attr_name, value=value.get_value(), datatype=value.get_datatype())
            else:
                LiteralAttribute.objects.create(record=pdrecord, prov_type=PROV_RECORD_LITERAL_MAP.get(attr_name),
                                                name=attr_name, value=value, datatype=None)
            
    return pdrecord

def save_account(account, records, record_map):
    for record in records:
        # if the record is not visited
        if record not in record_map:
            # visit it and create the corresponding PDRecord
            create_record(record, account, record_map)
    
def build_PROVContainer(account):
    graph = provdm.PROVContainer()
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
        rec_id = graph.get_compact_identifier(record.rec_id)
        attributes = record.attributes.all()
        prov_literals = record.literals.filter(prov_type__isnull=False)
        literal_attrs = record.literals.filter(prov_type__isnull=True)
        if rec_type == provdm.PROV_REC_ACCOUNT:
            # Do something special with account
            pass
        elif rec_type == provdm.PROV_REC_ENTITY:
            prov_record = graph.add_entity(rec_id)
        elif rec_type == provdm.PROV_REC_ACTIVITY:
#            startTime = datetime.strptime(attr_map.startTime, 'YYYY-MM-DD HH:MM:SS.mmmmmm') if 'time' in attr_map else None 
#            endTime = datetime.strptime(attr_map.endTime, 'YYYY-MM-DD HH:MM:SS.mmmmmm') if 'time' in attr_map else None
            prov_record = graph.add_activity(rec_id)
        elif rec_type == provdm.PROV_REC_GENERATION:
            pass
        if prov_record:
            # Build the attributes list
            attributes = {}
            for attr in literal_attrs:
                attr_name = str(graph.get_compact_identifier(attr.name))
                attributes[attr_name] = attr.value
            if attributes:
                prov_record.add_attributes(attributes)
                
            record_map[record] = prov_record 
        
    return graph
    