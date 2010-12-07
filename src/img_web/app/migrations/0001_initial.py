# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding model 'ImageJob'
        db.create_table('app_imagejob', (
            ('status', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('devicegroup', self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True)),
            ('task_id', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('imagefile', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('email', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('notify', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('error', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('test_image', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('logfile', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('app', ['ImageJob'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'ImageJob'
        db.delete_table('app_imagejob')
    
    
    models = {
        'app.imagejob': {
            'Meta': {'object_name': 'ImageJob'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'devicegroup': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imagefile': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'logfile': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'notify': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'task_id': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'test_image': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        }
    }
    
    complete_apps = ['app']
