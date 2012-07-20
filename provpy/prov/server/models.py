'''Django app for persisting prov.model.ProvBundle

Save and load provenance bundles from databases 

References:

PROV-DM: http://www.w3.org/TR/prov-dm/

@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2012
'''
from django.db import models, IntegrityError, DatabaseError
from django.contrib.auth.models import User, Group
from django.db.models.signals import  post_save, post_syncdb
from collections import defaultdict
import uuid
import datetime
import prov.model as prov
import logging
from prov.model import PROV_REC_BUNDLE
logger = logging.getLogger(__name__)


# Interface functions
def save_bundle(prov_bundle, identifier=None, asserter='#unknown'):
    # Generate a unique id for the new pdbundle to store the provenance graph
    bundle_id = uuid.uuid4().urn if identifier is None else identifier
    pdbundle = PDBundle.create(bundle_id, asserter)
    pdbundle.save_bundle(prov_bundle)
    #Return the pdbundle
    return pdbundle


# Classes
class PDNamespace(models.Model):
    prefix = models.CharField(max_length=255, db_index=True)
    uri  = models.CharField(max_length=255, db_index=True)


class PDRecord(models.Model):
    rec_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    rec_type = models.SmallIntegerField(choices=prov.PROV_RECORD_TYPES, db_index=True)
    bundle = models.ForeignKey('PDBundle', related_name='_records', null=True, blank=True, db_index=True)
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


class PDBundle(PDRecord):
    owner = models.ForeignKey(User, null=True, blank=True, db_index=True)
    asserter = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    namespaces = models.ManyToManyField(PDNamespace, related_name='bundles')
    
    class Meta:
        permissions = (
            ('view_pdbundle', 'Retrieving bundles'),
            ('admin_pdbundle', 'Granting/revoking permissions'),
            ('ownership_pdbundle', 'Permission to change ownership'),
        )

    
    @staticmethod
    def create(bundle_id, asserter_id, owner_id=None):
        return PDBundle.objects.create(rec_id=bundle_id, rec_type=prov.PROV_REC_BUNDLE,
                                       asserter=asserter_id, owner=owner_id)
    
    def add_namespace(self, prefix, uri):
        namespace = PDNamespace.objects.create(prefix=prefix, uri=uri)
        self.namespaces.add(namespace)
        
    def add_sub_bundle(self, pdbundle):
        pass
    
    def get_namespaces(self):
        results = {}
        for namespace in self.namespaces.all():
            results[namespace.prefix] = namespace.uri
        return results
        
    def save_bundle(self, prov_bundle):
        # Save all the namespaces for future QName recreation
        logger.debug('Saving namespaces...')
        namespaces = prov_bundle.get_registered_namespaces()
        for namespace in namespaces:
            self.add_namespace(namespace.get_prefix(), namespace.get_uri())
        # and the default namespace as well
        default_namespace = prov_bundle.get_default_namespace()
        if default_namespace:
            self.add_namespace('', default_namespace.get_uri())
         
        # An empty map to keep track of the visited records
        record_map = {}
        # Getting all the individual records contained in the graph
        records = prov_bundle.get_records()
        # and save them
        _save_bundle(self, records, record_map)
        
    def get_prov_bundle(self):
        logger.debug('Loading bundle id %s' % self.rec_id)
        prov_bundle = build_ProvBundle(self)
        return prov_bundle

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
    
def _create_pdrecord(prov_record, bundle, record_map):
    logger.debug('Saving PROV record: %s' % str(prov_record))
    prov_type = prov_record.get_type()
    record_id = prov_record.get_identifier()
    record_uri = None if record_id is None else record_id.get_uri()
    if prov_type <> prov.PROV_REC_BUNDLE:
        # Create a normal record
        pdrecord = PDRecord.objects.create(rec_id=record_uri, rec_type=prov_type, bundle=bundle)
        record_map[prov_record] = pdrecord
    else:
        # Create an bundle record
        asserter_uri = None # Bundles do not have asserter as in (previously defined) accounts, consider removing this
        pdrecord = PDBundle.objects.create(rec_id=record_uri, rec_type=prov_type, bundle=bundle, asserter=asserter_uri)
        record_map[prov_record] = pdrecord
        # Recursive call to save this bundle
        _save_bundle(pdrecord, prov_record.get_records(), record_map)
        
    # TODO add all _attributes here
    prov_attributes, extra_attributes = prov_record.get_attributes()
    if prov_attributes:
        for (attr, value) in prov_attributes.items():
            if value is None:
                # skipping unset attributes
                continue
            # Create a linked attribute's record
            if isinstance(value, prov.ProvRecord):
                if value not in record_map:
                    # The record in value needed to be saved first
                    # Assumption: no bi-directional relationship between records; otherwise, duplicated RecordAttribute will be created
                    # Recursive call to create the other record
                    # TODO: Check if the other record is in another bundle
                    other_record = _create_pdrecord(value, bundle, record_map)
                else:
                    other_record = record_map[value]
                RecordAttribute.objects.create(record=pdrecord, value=other_record, prov_type=attr)
            else:
                # Create a literal attribute
                attr_name = prov.PROV_ID_ATTRIBUTES_MAP[attr]
                value, datatype = _encode_python_literal(value)
                LiteralAttribute.objects.create(record=pdrecord, prov_type=attr, name=attr_name, value=value, datatype=datatype)
                
    if extra_attributes:
        for (attr, value) in extra_attributes:
            # Create a literal attribute
            attr_name = attr.get_uri() if isinstance(attr, prov.Identifier) else attr
            value, datatype = _encode_python_literal(value)
            LiteralAttribute.objects.create(record=pdrecord, prov_type=None, name=attr_name, value=value, datatype=datatype)
            
    return pdrecord

def _save_bundle(bundle, records, record_map):
    logger.debug('Saving bundle %s...' % bundle.rec_id)
    for record in records:
        # if the record is not visited
        if record not in record_map:
            # visit it and create the corresponding PDRecord
            _create_pdrecord(record, bundle, record_map)
    
def _create_prov_record(prov_bundle, pk, records, attributes, literals, record_map):
    if pk in record_map:
        # skip this record
        return record_map[pk]
    
    record_type = records[pk]['rec_type']
    record_id = prov_bundle.valid_identifier(records[pk]['rec_id'])
    
    # Prepare record-attributes, this map will return None for non-existent key request
    prov_attributes = defaultdict()
    for attr_id, value_id in attributes[pk]:
        # If the other PROV record has been created, use it; otherwise, create it before use 
        other_prov_record = record_map[value_id] if value_id in record_map else _create_prov_record(prov_bundle, value_id, records, attributes, literals, record_map) 
        prov_attributes[attr_id] = other_prov_record 
    # Prepare literal-_attributes
    prov_literals = defaultdict()
    other_literals = []
    for attr in literals[pk]:
        if attr.prov_type:
            prov_literals[attr.prov_type] = _decode_python_literal(attr.value, attr.datatype, prov_bundle)
        else:
            other_literals.append((prov_bundle.valid_identifier(attr.name), _decode_python_literal(attr.value, attr.datatype, prov_bundle)))
    prov_attributes.update(prov_literals)
            
    # Create the record by its type
    prov_record = prov_bundle.add_record(record_type, record_id, prov_attributes, other_literals)
    record_map[pk] = prov_record
    
    if record_type == PROV_REC_BUNDLE:
        # Loading records in this sub-bundle
        logger.debug('Loading records for %s' % str(prov_record))
        pdbundle = PDBundle.objects.get(pk=pk)
        build_ProvBundle(pdbundle, prov_record)
    
    logger.debug('Loaded PROV record: %s' % str(prov_record))
    return prov_record
    
def build_ProvBundle(pdbundle, prov_bundle=None):
    if prov_bundle is None:
        prov_bundle = prov.ProvBundle()
    namespaces = pdbundle.get_namespaces()
    for (prefix, uri) in namespaces.items():
        if prefix == '':
            prov_bundle.set_default_namespace(uri)
        else:
            prov_bundle.add_namespace(prov.Namespace(prefix, uri))
    
    record_map = {}
    # Sorting the records by their types to make sure the elements are created before the relations
    records = defaultdict(dict) 
    for pk, rec_id, rec_type in PDRecord.objects.select_related().filter(bundle=pdbundle).values_list('pk', 'rec_id', 'rec_type').order_by('rec_type'):
        records[pk]['rec_id'] = rec_id
        records[pk]['rec_type'] = rec_type
        
    attributes = defaultdict(list)
    for rec_id, value_id, attr_id in RecordAttribute.objects.filter(record__bundle=pdbundle).values_list('record__pk', 'value__pk', 'prov_type'):
        attributes[rec_id].append((attr_id, value_id))
        
    literals = defaultdict(list)
    for literal_attr in LiteralAttribute.objects.filter(record__bundle=pdbundle):
        literals[literal_attr.record_id].append(literal_attr)
    for pk in records:
        _create_prov_record(prov_bundle, pk, records, attributes, literals, record_map)
    return prov_bundle

def _create_profile(sender, created, instance, **kwargs):
    if(created):
        UserProfile.objects.create(user=instance)
        instance.groups.add(Group.objects.get(name='public'))

def _create_public_group(**kwargs):
    from prov.settings import ANONYMOUS_USER_ID
    try:
        public = Group.objects.get(name='public') 
    except Group.DoesNotExist:
        public = Group.objects.create(name='public')
    try:
        User.objects.get(id=ANONYMOUS_USER_ID).groups.add(public)
    except User.DoesNotExist:
        User.objects.create(id=ANONYMOUS_USER_ID, username='AnonymousUser').groups.add(public)
    
post_save.connect(_create_profile, sender=User, dispatch_uid=__file__)

post_syncdb.connect(_create_public_group)
