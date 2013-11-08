# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'PDNamespace'
        db.create_table(u'persistence_pdnamespace', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('prefix', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('uri', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('bundle', self.gf('django.db.models.fields.related.ForeignKey')(related_name='namespaces', to=orm['persistence.PDBundle'])),
        ))
        db.send_create_signal(u'persistence', ['PDNamespace'])

        # Adding model 'PDRecord'
        db.create_table(u'persistence_pdrecord', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('rec_id', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=255, null=True, blank=True)),
            ('rec_type', self.gf('django.db.models.fields.SmallIntegerField')(db_index=True)),
            ('bundle', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='_records', null=True, to=orm['persistence.PDBundle'])),
            ('asserted', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'persistence', ['PDRecord'])

        # Adding model 'RecordAttribute'
        db.create_table(u'persistence_recordattribute', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('record', self.gf('django.db.models.fields.related.ForeignKey')(related_name='from_records', to=orm['persistence.PDRecord'])),
            ('value', self.gf('django.db.models.fields.related.ForeignKey')(related_name='to_records', to=orm['persistence.PDRecord'])),
            ('prov_type', self.gf('django.db.models.fields.SmallIntegerField')(db_index=True)),
        ))
        db.send_create_signal(u'persistence', ['RecordAttribute'])

        # Adding model 'LiteralAttribute'
        db.create_table(u'persistence_literalattribute', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('record', self.gf('django.db.models.fields.related.ForeignKey')(related_name='literals', to=orm['persistence.PDRecord'])),
            ('prov_type', self.gf('django.db.models.fields.SmallIntegerField')(db_index=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('datatype', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
        ))
        db.send_create_signal(u'persistence', ['LiteralAttribute'])

        # Adding model 'PDBundle'
        db.create_table(u'persistence_pdbundle', (
            (u'pdrecord_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['persistence.PDRecord'], unique=True, primary_key=True)),
        ))
        db.send_create_signal(u'persistence', ['PDBundle'])


    def backwards(self, orm):
        # Deleting model 'PDNamespace'
        db.delete_table(u'persistence_pdnamespace')

        # Deleting model 'PDRecord'
        db.delete_table(u'persistence_pdrecord')

        # Deleting model 'RecordAttribute'
        db.delete_table(u'persistence_recordattribute')

        # Deleting model 'LiteralAttribute'
        db.delete_table(u'persistence_literalattribute')

        # Deleting model 'PDBundle'
        db.delete_table(u'persistence_pdbundle')


    models = {
        u'persistence.literalattribute': {
            'Meta': {'object_name': 'LiteralAttribute'},
            'datatype': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'prov_type': ('django.db.models.fields.SmallIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'record': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'literals'", 'to': u"orm['persistence.PDRecord']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
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
            'uri': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'})
        },
        u'persistence.pdrecord': {
            'Meta': {'object_name': 'PDRecord'},
            'asserted': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'attributes': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'references'", 'symmetrical': 'False', 'through': u"orm['persistence.RecordAttribute']", 'to': u"orm['persistence.PDRecord']"}),
            'bundle': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'_records'", 'null': 'True', 'to': u"orm['persistence.PDBundle']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rec_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
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