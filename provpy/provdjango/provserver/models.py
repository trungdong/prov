"""Module docstring to go here"""
from django.db import models
import uuid
import model.core as provdm
import datetime

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
    # Getting all the individual records contained in the graph
    records = prov_graph.get_records()
    # and save them
    save_account(account, records, record_map)
    #Return the account
    return account


# Classes
class PDNamespace(models.Model):
    _prefix = models.CharField(max_length=255, db_index=True)
    _uri  = models.CharField(max_length=255, db_index=True)


class PDRecord(models.Model):
    rec_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    rec_type = models.SmallIntegerField(choices=provdm.PROV_RECORD_TYPES, db_index=True)
    account = models.ForeignKey('PDAccount', related_name='_records', null=True, blank=True, db_index=True)
    _attributes = models.ManyToManyField('self', through='RecordAttribute', symmetrical=False, related_name='references')


class RecordAttribute(models.Model):
    record = models.ForeignKey(PDRecord, related_name='from_records', db_index=True)
    _value = models.ForeignKey(PDRecord, related_name='to_records')
    prov_type = models.SmallIntegerField(choices=PROV_RECORD_ATTRIBUTES, db_index=True)


class LiteralAttribute(models.Model):
    record = models.ForeignKey(PDRecord, related_name='literals', db_index=True)
    prov_type = models.SmallIntegerField(choices=PROV_RECORD_LITERALS, null=True, blank=True, db_index=True)
    name = models.CharField(max_length=255)
    _value = models.CharField(max_length=255)
    _datatype = models.CharField(max_length=255, null=True, blank=True)


class PDAccount(PDRecord):
    asserter = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    _namespaces = models.ManyToManyField(PDNamespace, related_name='accounts')
    
    @staticmethod
    def create(account_id, asserter_id):
        return PDAccount.objects.create(rec_id=account_id, rec_type=provdm.PROV_REC_ACCOUNT, asserter=asserter_id)
    
    def add_namespace(self, prefix, uri):
        namespace = PDNamespace.objects.create(prefix=prefix, uri=uri)
        self._namespaces.add(namespace)
        
    def add_sub_account(self, account_record):
        pass
    
    def get_namespaces(self):
        results = {}
        for namespace in self._namespaces.all():
            results[namespace._prefix] = namespace._uri
        return results
        
    def get_PROVContainer(self):
        return build_PROVContainer(self)


# Internal functions
def _convert_python_literal(literal):
    if isinstance(literal, datetime.datetime):
        return literal.isoformat()
    else:
        return literal
    
def _create_pdrecord(prov_record, account, record_map):
    prov_type = prov_record.get_prov_type()
    record_id = prov_record.get_record_id()
    record_uri = record_id._uri() if record_id is not None else None
    if prov_type <> provdm.PROV_REC_ACCOUNT:
        # Create a normal record
        pdrecord = PDRecord.objects.create(rec_id=record_uri, rec_type=prov_type, account=account)
        record_map[prov_record] = pdrecord
    else:
        # Create an account record
        asserter_uri = prov_record.get_asserter()._uri()
        pdrecord = PDAccount.objects.create(rec_id=record_id, rec_type=prov_type, account=account, asserter=asserter_uri)
        record_map[prov_record] = pdrecord
        # Recursive call to save this account
        save_account(pdrecord, prov_record.get_records(), record_map)
        
    # TODO add all _attributes here
    attributes = prov_record.get_all_attributes()
    for (name, value) in attributes.iteritems():
        # TODO This assume all prov _attributes use QName strings, e.g. "prov:entity"
        if name in PROV_RECORD_ATTR_MAP:
            # Create a linked attribute's record
            if isinstance(value, provdm.Record):
                if value not in record_map:
                    # The record in value needed to be saved first
                    # Assumption: no bidirectional relationship between records; otherwise, duplicated RecordAttribute will be created
                    # Recursive call to create the other record
                    # TODO: Check if the other record is in another account
                    other_record = _create_pdrecord(value, account, record_map)
                else:
                    other_record = record_map[value]
                RecordAttribute.objects.create(record=pdrecord, value=other_record, prov_type=PROV_RECORD_ATTR_MAP[name])
            else:
                raise Exception('Expected a PROV Record for %s. Got %s.' % name )
        else:
            # Create a literal attribute
            attr_name = name._uri() if isinstance(name, provdm.PROVIdentifier) else str(name)
            if isinstance(value, provdm.PROVLiteral):
                LiteralAttribute.objects.create(record=pdrecord, prov_type=PROV_RECORD_LITERAL_MAP.get(attr_name),
                                                name=attr_name, value=value.get_value(), datatype=value.get_datatype())
            else:
                LiteralAttribute.objects.create(record=pdrecord, prov_type=PROV_RECORD_LITERAL_MAP.get(attr_name),
                                                name=attr_name, value=_convert_python_literal(value), datatype=type(value))
            
    return pdrecord

def save_account(account, records, record_map):
    for record in records:
        # if the record is not visited
        if record not in record_map:
            # visit it and create the corresponding PDRecord
            _create_pdrecord(record, account, record_map)
    
def _parse_literal_value(literal, datatype):
    if datatype == 'xsd:dateTime' or datatype == "<type 'datetime.datetime'>":
        return datetime.datetime.strptime(literal, "%Y-%m-%dT%H:%M:%S")
    elif datatype == 'xsd:anyURI':
        return provdm.PROVIdentifier(literal)
    elif datatype == "<type 'str'>":
        return str(literal)
    elif datatype == "<type 'int'>":
        return int(literal) 
    return literal

def _create_prov_record(graph, record, record_map):
    if record in record_map:
        # skip this record
        return record_map[record]
    
    rec_type = record.rec_type
    rec_id = graph.get_compact_identifier(record.rec_id)
    
    from collections import defaultdict
    # Prepare record-_attributes, this map will return None for non-existent key request
    record_attributes = defaultdict(lambda: None)
    for attr in RecordAttribute.objects.filter(record=record):
        # If the other PROV record has been created, use it; otherwise, create it before use 
        other_prov_record = record_map[attr._value] if attr._value in record_map else _create_prov_record(graph, attr._value, record_map) 
        record_attributes[attr.prov_type] = other_prov_record 
    # Prepare literal-_attributes
    prov_literals = defaultdict(lambda: None)
    other_literals = defaultdict(lambda: None)
    for attr in record.literals.all():
        if attr.prov_type:
            prov_literals[attr.prov_type] = _parse_literal_value(attr._value, attr._datatype)
        else:
            other_literals[str(graph.get_compact_identifier(attr.name))] = _parse_literal_value(attr._value, attr._datatype)
            
    # Create the record by its type
    #TODO Add account support
    if rec_type == provdm.PROV_REC_ENTITY:
        prov_record = graph.add_entity(rec_id, other_literals)
    elif rec_type == provdm.PROV_REC_ACTIVITY:
        prov_record = graph.add_activity(rec_id, prov_literals[PROV_ATTR_STARTTIME], prov_literals[PROV_ATTR_ENDTIME], other_literals)
    elif rec_type == provdm.PROV_REC_AGENT:
        prov_record = graph.add_agent(rec_id, other_literals)
    elif rec_type == provdm.PROV_REC_NOTE:
        prov_record = graph.add_note(rec_id, other_literals)
    elif rec_type == provdm.PROV_REC_GENERATION:
        prov_record = graph.add_wasGeneratedBy(record_attributes[PROV_ATTR_ENTITY], record_attributes[PROV_ATTR_ACTIVITY], rec_id, prov_literals[PROV_ATTR_TIME], other_literals)
    elif rec_type == provdm.PROV_REC_USAGE:
        prov_record = graph.add_used(record_attributes[PROV_ATTR_ACTIVITY], record_attributes[PROV_ATTR_ENTITY], rec_id, prov_literals[PROV_ATTR_TIME], other_literals)
    elif rec_type == provdm.PROV_REC_ACTIVITY_ASSOCIATION:
        prov_record = graph.add_wasAssociatedWith(record_attributes[PROV_ATTR_ACTIVITY], record_attributes[PROV_ATTR_AGENT], rec_id, other_literals)
    elif rec_type == provdm.PROV_REC_START:
        prov_record = graph.add_wasStartedBy(record_attributes[PROV_ATTR_ACTIVITY], record_attributes[PROV_ATTR_AGENT], rec_id, other_literals)
    elif rec_type == provdm.PROV_REC_END:
        prov_record = graph.add_wasEndedBy(record_attributes[PROV_ATTR_ACTIVITY], record_attributes[PROV_ATTR_AGENT], rec_id, other_literals)
    elif rec_type == provdm.PROV_REC_RESPONSIBILITY:
        prov_record = graph.add_actedOnBehalfOf(record_attributes[PROV_ATTR_SUBORDINATE], record_attributes[PROV_ATTR_RESPONSIBLE], rec_id, other_literals)
    elif rec_type == provdm.PROV_REC_DERIVATION:
        prov_record = graph.add_wasDerivedFrom(record_attributes[PROV_ATTR_GENERATED_ENTITY], record_attributes[PROV_ATTR_USED_ENTITY], rec_id, record_attributes[PROV_ATTR_ACTIVITY], record_attributes[PROV_ATTR_GENERATION], record_attributes[PROV_ATTR_USAGE], other_literals)
    elif rec_type == provdm.PROV_REC_ALTERNATE:
        prov_record = graph.add_alternateOf(record_attributes[PROV_ATTR_ENTITY], record_attributes[PROV_ATTR_ALTERNATE], rec_id, other_literals)
    elif rec_type == provdm.PROV_REC_SPECIALIZATION:
        prov_record = graph.add_specializationOf(record_attributes[PROV_ATTR_ENTITY], record_attributes[PROV_ATTR_SPECIALIZATION], rec_id, other_literals)
    elif rec_type == provdm.PROV_REC_ANNOTATION:
        prov_record = graph.add_hasAnnotation(record_attributes[PROV_ATTR_RECORD], record_attributes[PROV_ATTR_NOTE], rec_id, other_literals)
    elif rec_type == provdm.PROV_REC_ACCOUNT:
        #TODO implement creating account
        prov_record = graph.add_account(rec_id)
        
    record_map[record] = prov_record    
    return prov_record
    
def build_PROVContainer(account):
    graph = provdm.PROVContainer()
    namespaces = account.get_namespaces()
    for (prefix, uri) in namespaces.items():
        if prefix == 'default':
            graph.set_default_namespace(uri)
        else:
            graph.add_namespace(prefix, uri)
    
    record_map = {}
    # Sorting the records by their types to make sure the elements are created before the relations
    records = account._records.order_by('rec_type')
    for record in records:
        _create_prov_record(graph, record, record_map)
    return graph
    