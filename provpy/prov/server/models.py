"""Module docstring to go here"""
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import  post_save
from collections import defaultdict
import uuid
import datetime
import prov.model as prov
import logging
logger = logging.getLogger(__name__)


# Interface functions
def save_records(prov_graph):
    # Generate a unique id for a new account to contain the provenance graph
    account_id = uuid.uuid4().urn
    account = PDAccount.create(account_id, '#me')
    account.save_graph(prov_graph)
    #Return the account
    return account


# Classes
class PDNamespace(models.Model):
    prefix = models.CharField(max_length=255, db_index=True)
    uri  = models.CharField(max_length=255, db_index=True)


class PDRecord(models.Model):
    rec_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    rec_type = models.SmallIntegerField(choices=provm.PROV_RECORD_TYPES, db_index=True)
    account = models.ForeignKey('PDAccount', related_name='_records', null=True, blank=True, db_index=True)
    attributes = models.ManyToManyField('self', through='RecordAttribute', symmetrical=False, related_name='references')


class RecordAttribute(models.Model):
    record = models.ForeignKey(PDRecord, related_name='from_records', db_index=True)
    value = models.ForeignKey(PDRecord, related_name='to_records')
    prov_type = models.SmallIntegerField(choices=prov.PROV_RECORD_ATTRIBUTES, db_index=True)


class LiteralAttribute(models.Model):
    record = models.ForeignKey(PDRecord, related_name='literals', db_index=True)
    prov_type = models.SmallIntegerField(choices=prov.PROV_RECORD_ATTRIBUTES, null=True, blank=True, db_index=True)
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    datatype = models.CharField(max_length=255, null=True, blank=True)


class PDAccount(PDRecord):
    owner = models.OneToOneField(User)
    asserter = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    namespaces = models.ManyToManyField(PDNamespace, related_name='accounts')
    
    @staticmethod
    def create(account_id, asserter_id, owner_id):
        return PDAccount.objects.create(rec_id=account_id, rec_type=prov.PROV_REC_ACCOUNT,
                                        asserter=asserter_id, owner = owner_id)
    
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
        
    def save_graph(self, prov_graph):
        # Save all the namespaces for future QName recreation
        logger.debug('Saving namespaces...')
        namespaces = prov_graph.get_registered_namespaces()
        for namespace in namespaces:
            self.add_namespace(namespace.get_prefix(), namespace.get_uri())
        # and the default namespace as well
        default_namespace = prov_graph.get_default_namespace()
        if default_namespace:
            self.add_namespace('', default_namespace.get_uri())
         
        # An empty map to keep track of the visited records
        record_map = {}
        # Getting all the individual records contained in the graph
        records = prov_graph.get_records()
        # and save them
        save_account(self, records, record_map)
        
    def get_graph(self):
        logger.debug('Loading account id %s' % self.rec_id)
        prov_graph = build_PROVContainer(self)
        return prov_graph

class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)


# Internal functions
def _encode_python_literal(literal):
    if isinstance(literal, datetime.datetime):
        return literal.isoformat(), 'xsd:dateTime'
    elif isinstance(literal, prov.Identifier):
        return literal.get_uri(), 'xsd:anyURI'
    elif isinstance(literal, prov.Literal):
        value, _ = _encode_python_literal(literal.get_value())
        datatype = literal.get_datatype()
        xsd_type = prov.XSD.qname(datatype);
        if xsd_type:
            xsd_type_str = str(xsd_type)
#            if xsd_type_str in ('xsd:anyURI', 'xsd:QName'):
            return value, xsd_type_str 
        else:
            return value, datatype.get_uri() if isinstance(datatype, prov.Identifier) else datatype
    else:
        return literal, type(literal)

DATATYPE_FUNCTIONS_MAP = {'xsd:dateTime': prov.parse_xsd_dateTime,
                          "<type 'datetime.datetime'>": prov.parse_xsd_dateTime,
                          "<type 'str'>": str,
                          "<type 'unicode'>": unicode,
                          "<type 'int'>": int}

def _decode_python_literal(value, datatype, graph):
    if datatype in DATATYPE_FUNCTIONS_MAP:
        return DATATYPE_FUNCTIONS_MAP[datatype](value)
    elif datatype == 'xsd:anyURI':
        return graph.valid_identifier(value)
    else:
        literal_type = graph.valid_identifier(datatype)
        return prov.Literal(value, literal_type) 
    
def _create_pdrecord(prov_record, account, record_map):
    logger.debug('Saving PROV record: %s' % str(prov_record))
    prov_type = prov_record.get_type()
    record_id = prov_record.get_identifier()
    record_uri = record_id.get_uri() if record_id is not None else None
    if prov_type <> prov.PROV_REC_ACCOUNT:
        # Create a normal record
        pdrecord = PDRecord.objects.create(rec_id=record_uri, rec_type=prov_type, account=account)
        record_map[prov_record] = pdrecord
    else:
        # Create an account record
        asserter_uri = prov_record.get_asserter().get_uri()
        pdrecord = PDAccount.objects.create(rec_id=record_id, rec_type=prov_type, account=account, asserter=asserter_uri)
        record_map[prov_record] = pdrecord
        # Recursive call to save this account
        save_account(pdrecord, prov_record.get_records(), record_map)
        
    # TODO add all _attributes here
    prov_attributes, extra_attributes = prov_record.get_attributes()
    if prov_attributes:
        for (attr, value) in prov_attributes.items():
            if value is None:
                # skipping unset attributes
                continue
            if attr in prov.PROV_ATTRIBUTE_LITERALS:
                # Create a literal attribute
                attr_name = prov.PROV_ID_ATTRIBUTES_MAP[attr]
                value, datatype = _encode_python_literal(value)
                LiteralAttribute.objects.create(record=pdrecord, prov_type=attr, name=attr_name, value=value, datatype=datatype)
            else:
                # Create a linked attribute's record
                if isinstance(value, prov.ProvRecord):
                    if value not in record_map:
                        # The record in value needed to be saved first
                        # Assumption: no bidirectional relationship between records; otherwise, duplicated RecordAttribute will be created
                        # Recursive call to create the other record
                        # TODO: Check if the other record is in another account
                        other_record = _create_pdrecord(value, account, record_map)
                    else:
                        other_record = record_map[value]
                    RecordAttribute.objects.create(record=pdrecord, value=other_record, prov_type=attr)
                else:
                    raise Exception('Expected a PROV Record for %s. Got %s.' % str(value))
    if extra_attributes:
        for (attr, value) in extra_attributes:
            # Create a literal attribute
            attr_name = attr.get_uri() if isinstance(attr, prov.Identifier) else attr
            value, datatype = _encode_python_literal(value)
            LiteralAttribute.objects.create(record=pdrecord, prov_type=None, name=attr_name, value=value, datatype=datatype)
            
    return pdrecord

def save_account(account, records, record_map):
    logger.debug('Saving account %s...' % account.rec_id)
    for record in records:
        # if the record is not visited
        if record not in record_map:
            # visit it and create the corresponding PDRecord
            _create_pdrecord(record, account, record_map)
    
def _create_prov_record(graph, pk, records, attributes, literals, record_map):
    if pk in record_map:
        # skip this record
        return record_map[pk]
    
    record_type = records[pk]['rec_type']
    record_id = graph.valid_identifier(records[pk]['rec_id'])
    
    # Prepare record-_attributes, this map will return None for non-existent key request
    prov_attributes = defaultdict()
    for attr_id, value_id in attributes[pk]:
        # If the other PROV record has been created, use it; otherwise, create it before use 
        other_prov_record = record_map[value_id] if value_id in record_map else _create_prov_record(graph, value_id, records, attributes, literals, record_map) 
        prov_attributes[attr_id] = other_prov_record 
    # Prepare literal-_attributes
    prov_literals = defaultdict()
    other_literals = []
    for attr in literals[pk]:
        if attr.prov_type:
            prov_literals[attr.prov_type] = _decode_python_literal(attr.value, attr.datatype, graph)
        else:
            other_literals.append((graph.valid_identifier(attr.name), _decode_python_literal(attr.value, attr.datatype, graph)))
    prov_attributes.update(prov_literals)
            
    # Create the record by its type
    #TODO Add account support
    prov_record = graph.add_record(record_type, record_id, prov_attributes, other_literals)
        
    record_map[pk] = prov_record
    logger.debug('Loaded PROV record: %s' % str(prov_record))
    return prov_record
    
def build_PROVContainer(account):
    graph = prov.ProvContainer()
    namespaces = account.get_namespaces()
    for (prefix, uri) in namespaces.items():
        if prefix == '':
            graph.set_default_namespace(uri)
        else:
            graph.add_namespace(prov.Namespace(prefix, uri))
    
    record_map = {}
    # Sorting the records by their types to make sure the elements are created before the relations
    records = defaultdict(dict) 
    for pk, rec_id, rec_type in PDRecord.objects.select_related().filter(account=account).values_list('pk', 'rec_id', 'rec_type').order_by('rec_type'):
        records[pk]['rec_id'] = rec_id
        records[pk]['rec_type'] = rec_type
        
    attributes = defaultdict(list)
    for rec_id, value_id, attr_id in RecordAttribute.objects.filter(record__account=account).values_list('record__pk', 'value__pk', 'prov_type'):
        attributes[rec_id].append((attr_id, value_id))
        
    literals = defaultdict(list)
    for literal_attr in LiteralAttribute.objects.filter(record__account=account):
        literals[literal_attr.record_id].append(literal_attr)
    for pk in records:
        _create_prov_record(graph, pk, records, attributes, literals, record_map)
    return graph

def _create_profile(sender, instance, created, **kwargs):
    #logging.debug(created)
    if(created):
        UserProfile.objects.create(user=instance)

post_save.connect(_create_profile, sender=User)
    