# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'PDNamespace.uri'
        db.alter_column(u'persistence_pdnamespace', 'uri', self.gf('django.db.models.fields.TextField')())

        # Changing field 'LiteralAttribute.name'
        db.alter_column(u'persistence_literalattribute', 'name', self.gf('django.db.models.fields.TextField')())

        # Changing field 'LiteralAttribute.datatype'
        db.alter_column(u'persistence_literalattribute', 'datatype', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'LiteralAttribute.value'
        db.alter_column(u'persistence_literalattribute', 'value', self.gf('django.db.models.fields.TextField')())

        # Changing field 'PDRecord.rec_id'
        db.alter_column(u'persistence_pdrecord', 'rec_id', self.gf('django.db.models.fields.TextField')(null=True))

    def backwards(self, orm):

        # Changing field 'PDNamespace.uri'
        db.alter_column(u'persistence_pdnamespace', 'uri', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'LiteralAttribute.name'
        db.alter_column(u'persistence_literalattribute', 'name', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'LiteralAttribute.datatype'
        db.alter_column(u'persistence_literalattribute', 'datatype', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'LiteralAttribute.value'
        db.alter_column(u'persistence_literalattribute', 'value', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'PDRecord.rec_id'
        db.alter_column(u'persistence_pdrecord', 'rec_id', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

    models = {
        u'persistence.literalattribute': {
            'Meta': {'object_name': 'LiteralAttribute'},
            'datatype': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'prov_type': ('django.db.models.fields.SmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'record': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'literals'", 'to': u"orm['persistence.PDRecord']"}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        u'persistence.pdbundle': {
            'Meta': {'object_name': 'PDBundle', '_ormbases': [u'persistence.PDRecord']},
            u'pdrecord_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['persistence.PDRecord']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'persistence.pdnamespace': {
            'Meta': {'object_name': 'PDNamespace'},
            'bundle': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'namespaces'", 'to': u"orm['persistence.PDBundle']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'prefix': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'uri': ('django.db.models.fields.TextField', [], {'db_index': 'True'})
        },
        u'persistence.pdrecord': {
            'Meta': {'object_name': 'PDRecord'},
            'asserted': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'attributes': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'references'", 'symmetrical': 'False', 'through': u"orm['persistence.RecordAttribute']", 'to': u"orm['persistence.PDRecord']"}),
            'bundle': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'_records'", 'null': 'True', 'to': u"orm['persistence.PDBundle']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rec_id': ('django.db.models.fields.TextField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'rec_type': ('django.db.models.fields.SmallIntegerField', [], {'db_index': 'True'})
        },
        u'persistence.recordattribute': {
            'Meta': {'object_name': 'RecordAttribute'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'prov_type': ('django.db.models.fields.SmallIntegerField', [], {'db_index': 'True'}),
            'record': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'from_records'", 'to': u"orm['persistence.PDRecord']"}),
            'value': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'to_records'", 'to': u"orm['persistence.PDRecord']"})
        }
    }

    complete_apps = ['persistence']