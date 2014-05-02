"""Django app for persisting prov.model.ProvBundle

Save and load provenance bundles from databases

References:

PROV-DM: http://www.w3.org/TR/prov-dm/

@author: Trung Dong Huynh <trungdong@donggiang.com>
@copyright: University of Southampton 2014
"""

from collections import defaultdict, OrderedDict
import uuid
import datetime
import logging
from django.db import models
import prov.model as prov
logger = logging.getLogger(__name__)


# Interface functions
def save_bundle(prov_bundle, identifier=None):
    # Generate a unique id for the new pdbundle to store the provenance graph
    bundle_id = uuid.uuid4().urn if identifier is None else identifier
    pdbundle = PDBundle.create(bundle_id)
    pdbundle.save_bundle(prov_bundle)
    #Return the pdbundle
    return pdbundle


# Classes
class PDNamespace(models.Model):
    prefix = models.CharField(max_length=255, db_index=True)
    uri = models.TextField(db_index=True)
    bundle = models.ForeignKey('PDBundle', related_name='namespaces', db_index=True)

    class Meta:
        verbose_name = 'namespace'

    def __unicode__(self):
        return u'(%s: <%s>)' % (self.prefix, self.uri)


class PDRecord(models.Model):
    rec_id = models.TextField(null=True, blank=True, db_index=True)
    rec_type = models.SmallIntegerField(choices=prov.PROV_RECORD_TYPES, db_index=True)
    bundle = models.ForeignKey('PDBundle', related_name='_records', null=True, blank=True, db_index=True)
    asserted = models.BooleanField(default=True)
    attributes = models.ManyToManyField('self', through='RecordAttribute', symmetrical=False, related_name='references')


class RecordAttribute(models.Model):
    record = models.ForeignKey(PDRecord, related_name='from_records', db_index=True)
    value = models.ForeignKey(PDRecord, related_name='to_records')
    prov_type = models.SmallIntegerField(choices=prov.PROV_RECORD_ATTRIBUTES, db_index=True)


class LiteralAttribute(models.Model):
    record = models.ForeignKey(PDRecord, related_name='literals', db_index=True)
    prov_type = models.SmallIntegerField(choices=prov.PROV_RECORD_ATTRIBUTES, null=True, blank=True, db_index=True)
    name = models.TextField()
    value = models.TextField()
    datatype = models.TextField(null=True, blank=True)
    langtag = models.TextField(null=True, blank=True, default=None)


class PDBundle(PDRecord):
    class Meta:
        verbose_name = 'bundle'

    def __unicode__(self):
        return unicode(self.rec_id)

    @staticmethod
    def create(bundle_id):
        return PDBundle.objects.create(rec_id=bundle_id, rec_type=prov.PROV_REC_BUNDLE)

    def add_namespace(self, prefix, uri):
        namespace = PDNamespace.objects.create(prefix=prefix, uri=uri, bundle=self)
        return namespace

    def add_prov_bundle(self, bundle):
        uri = bundle.get_identifier().get_uri()

        if self._records.filter(rec_type=prov.PROV_REC_BUNDLE, rec_id=uri).exists():
            raise prov.ProvException(u"Non unique bundle identifier")

        if len(bundle._bundles) > 0:
            raise prov.ProvException(u"Bundle cannot contain bundles")

        pdbundle = PDBundle.create(uri)
        pdbundle.bundle = self
        pdbundle.save_bundle(bundle)
        pdbundle.save()
        return pdbundle

    def get_namespaces(self):
        results = {}
        for namespace in self.namespaces.all():
            results[namespace.prefix] = namespace.uri
        return results

    def save_bundle(self, prov_bundle):
        # An empty map to keep track of the visited records
        record_map = {}
        # Getting all the individual records contained in the graph
        records = prov_bundle.get_records()
        # and save them
        _save_bundle(self, records, record_map, prov_bundle)

    def get_prov_bundle(self):
        logger.debug('Loading bundle id %s' % self.rec_id)
        prov_bundle = build_ProvBundle(self)
        return prov_bundle

    def get_namespace_manager(self):
        namespace_manager = prov.NamespaceManager()

        namespaces = self.get_namespaces()
        for (prefix, uri) in namespaces.items():
            if prefix == '':
                namespace_manager.set_default_namespace(uri)
            else:
                namespace_manager.add_namespace(prov.Namespace(prefix, uri))

        return namespace_manager


# Internal functions
def _encode_python_literal(literal):
    if isinstance(literal, datetime.datetime):
        return literal.isoformat(), 'xsd:dateTime', None
    elif isinstance(literal, prov.Identifier):
        return literal.get_uri(), 'xsd:anyURI', None
    elif isinstance(literal, prov.Literal):
        value, _, _ = _encode_python_literal(literal.get_value())
        datatype = literal.get_datatype()
        langtag = literal.get_langtag()
        xsd_type = prov.XSD.qname(datatype)
        if xsd_type:
            xsd_type_str = str(xsd_type)
#            if xsd_type_str in ('xsd:anyURI', 'xsd:QName'):
            return value, xsd_type_str, langtag
        else:
            return value, datatype.get_uri() if isinstance(datatype, prov.Identifier) else datatype, langtag
    else:
        return literal, type(literal), None

DATATYPE_FUNCTIONS_MAP = {'xsd:dateTime': prov.parse_xsd_dateTime,
                          "<type 'datetime.datetime'>": prov.parse_xsd_dateTime,
                          "<type 'str'>": unicode,
                          "<type 'unicode'>": unicode,
                          "<type 'bool'>": bool,
                          "<type 'int'>": int,
                          "<type 'long'>": long,
                          "<type 'float'>": float}


def _decode_python_literal(value, datatype, langtag, graph):
    if datatype in DATATYPE_FUNCTIONS_MAP:
        return DATATYPE_FUNCTIONS_MAP[datatype](value)
    elif datatype == 'xsd:anyURI':
        return graph.valid_identifier(value)
    else:
        literal_type = graph.valid_identifier(datatype)
        return prov.Literal(value, literal_type, langtag)


def _create_pdrecord(prov_record, bundle, record_map, prov_bundle=None):
    logger.debug('Saving PROV record: %s' % unicode(prov_record))
    prov_type = prov_record.get_type()
    record_id = prov_record.get_identifier()
    record_uri = None if record_id is None else record_id.get_uri()
    if prov_type != prov.PROV_REC_BUNDLE:
        # Create a normal record
        pdrecord = PDRecord.objects.create(rec_id=record_uri, rec_type=prov_type, bundle=bundle, asserted=prov_record.is_asserted())
        record_map[prov_record] = pdrecord
    else:
        # Create an bundle record
        pdrecord = PDBundle.objects.create(rec_id=record_uri, rec_type=prov_type, bundle=bundle, asserted=prov_record.is_asserted())
        record_map[prov_record] = pdrecord
        # Recursive call to save this bundle
        _save_bundle(pdrecord, prov_record.get_records(), record_map, prov_bundle)

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
                value, datatype, langtag = _encode_python_literal(value)
                LiteralAttribute.objects.create(record=pdrecord, prov_type=attr, name=attr_name, value=value, datatype=datatype, langtag=langtag)

    if extra_attributes:
        for (attr, value) in extra_attributes:
            # Create a literal attribute
            attr_name = attr.get_uri() if isinstance(attr, prov.Identifier) else attr
            value, datatype, langtag = _encode_python_literal(value)
            LiteralAttribute.objects.create(record=pdrecord, prov_type=None, name=attr_name, value=value, datatype=datatype, langtag=langtag)

    return pdrecord


def _save_bundle(bundle, records, record_map, prov_bundle):
    # Save all the namespaces for future QName recreation
    logger.debug('Saving namespaces...')
    if prov_bundle.is_document():
        # Only save the namespaces if this is a document
        namespaces = prov_bundle.get_registered_namespaces()
        for namespace in namespaces:
            bundle.add_namespace(namespace.get_prefix(), namespace.get_uri())
        # and the default namespace as well
        default_namespace = prov_bundle.get_default_namespace()
        if default_namespace:
            bundle.add_namespace('', default_namespace.get_uri())

    logger.debug('Saving bundle %s...' % bundle.rec_id)
    for record in records:
        # if the record is not visited
        if record not in record_map:
            # visit it and create the corresponding PDRecord
            _create_pdrecord(record, bundle, record_map, prov_bundle)


def _create_prov_record(prov_bundle, pk, records, attributes, literals, record_map):
    if pk in record_map:
        # skip this record
        return record_map[pk]

    record_type = records[pk]['rec_type']
    record_id = prov_bundle.valid_identifier(records[pk]['rec_id'])
    asserted = records[pk]['asserted']

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
            prov_literals[attr.prov_type] = _decode_python_literal(attr.value, attr.datatype, attr.langtag, prov_bundle)
        else:
            other_literals.append((prov_bundle.valid_identifier(attr.name), _decode_python_literal(attr.value, attr.datatype, attr.langtag, prov_bundle)))
    prov_attributes.update(prov_literals)

    # Create the record by its type
    prov_record = prov_bundle.add_record(record_type, record_id, prov_attributes, other_literals, asserted=asserted)
    record_map[pk] = prov_record

    if record_type == prov.PROV_REC_BUNDLE:
        # Loading records in this sub-bundle
        logger.debug('Loading records for %s' % unicode(prov_record))
        pdbundle = PDBundle.objects.get(pk=pk)
        build_ProvBundle(pdbundle, prov_record, record_map)

    logger.debug('Loaded PROV record: %s' % unicode(prov_record))
    return prov_record


def build_ProvBundle(pdbundle, prov_bundle=None, record_map=None):
    if record_map is None:
        record_map = dict()

    if prov_bundle is None:
        prov_bundle = prov.ProvBundle()

    if not prov_bundle._bundle and pdbundle.bundle:
        # If this is a bundle, not a document, but is being displayed as a standalone document
        namespaces = pdbundle.bundle.get_namespaces()
        for (prefix, uri) in namespaces.items():
            if prefix == '':
                prov_bundle.set_default_namespace(uri)
            else:
                prov_bundle.add_namespace(prov.Namespace(prefix, uri))
    else:
        # If this is a bundle within a document or a document itself
        namespaces = pdbundle.get_namespaces()
        for (prefix, uri) in namespaces.items():
            if prefix == '':
                prov_bundle.set_default_namespace(uri)
            else:
                prov_bundle.add_namespace(prov.Namespace(prefix, uri))

    # Sorting the records by their types to make sure the elements are created before the relations
    records = OrderedDict()
    for pk, rec_id, rec_type, asserted in PDRecord.objects.select_related().filter(bundle=pdbundle).values_list('pk', 'rec_id', 'rec_type', 'asserted').order_by('rec_type'):
        records[pk] = {'rec_id': rec_id,
                       'rec_type': rec_type,
                       'asserted': asserted}

    attributes = defaultdict(list)
    for rec_id, value_id, attr_id in RecordAttribute.objects.filter(record__bundle=pdbundle).values_list('record__pk', 'value__pk', 'prov_type'):
        attributes[rec_id].append((attr_id, value_id))

    literals = defaultdict(list)
    for literal_attr in LiteralAttribute.objects.filter(record__bundle=pdbundle):
        literals[literal_attr.record_id].append(literal_attr)
    for pk in records:
        _create_prov_record(prov_bundle, pk, records, attributes, literals, record_map)
    return prov_bundle
