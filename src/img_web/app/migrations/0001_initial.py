# -*- coding: utf-8 -*-
import datetime
from django import db
from django.db import migrations, models


class Migration(migrations.Migration):

    def forwards(self, orm):
        # Adding model 'Queue'
        db.create_table('app_queue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('handle_launch', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('app', ['Queue'])

        # Adding model 'ImageJob'
        db.create_table('app_imagejob', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('image_id', self.gf('django.db.models.fields.CharField')(max_length=60)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('done', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('queue', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['app.Queue'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('email', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('notify', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('test_image', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('devicegroup', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('test_options', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('test_result', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('test_results_url', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('image_type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('tokenmap', self.gf('django.db.models.fields.CharField')(max_length=1000, blank=True)),
            ('arch', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('overlay', self.gf('django.db.models.fields.CharField')(max_length=500, blank=True)),
            ('extra_repos', self.gf('django.db.models.fields.CharField')(max_length=800, blank=True)),
            ('kickstart', self.gf('django.db.models.fields.TextField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('status', self.gf('django.db.models.fields.CharField')(default='IN QUEUE', max_length=30)),
            ('image_url', self.gf('django.db.models.fields.CharField')(max_length=500, blank=True)),
            ('files_url', self.gf('django.db.models.fields.CharField')(max_length=500, blank=True)),
            ('logfile_url', self.gf('django.db.models.fields.CharField')(max_length=500, blank=True)),
            ('log', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('error', self.gf('django.db.models.fields.CharField')(max_length=1000, blank=True)),
        ))
        db.send_create_signal('app', ['ImageJob'])

        # Adding model 'BuildService'
        db.create_table('app_buildservice', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('apiurl', self.gf('django.db.models.fields.CharField')(unique=True, max_length=250)),
        ))
        db.send_create_signal('app', ['BuildService'])

        # Adding model 'Arch'
        db.create_table('app_arch', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
        ))
        db.send_create_signal('app', ['Arch'])

        # Adding model 'ImageType'
        db.create_table('app_imagetype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
        ))
        db.send_create_signal('app', ['ImageType'])

        # Adding model 'Token'
        db.create_table('app_token', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40)),
            ('default', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('app', ['Token'])


    def backwards(self, orm):
        # Deleting model 'Queue'
        db.delete_table('app_queue')

        # Deleting model 'ImageJob'
        db.delete_table('app_imagejob')

        # Deleting model 'BuildService'
        db.delete_table('app_buildservice')

        # Deleting model 'Arch'
        db.delete_table('app_arch')

        # Deleting model 'ImageType'
        db.delete_table('app_imagetype')

        # Deleting model 'Token'
        db.delete_table('app_token')


    models = {
        'app.arch': {
            'Meta': {'object_name': 'Arch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        'app.buildservice': {
            'Meta': {'object_name': 'BuildService'},
            'apiurl': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '250'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        'app.imagejob': {
            'Meta': {'object_name': 'ImageJob'},
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'devicegroup': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'done': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'}),
            'extra_repos': ('django.db.models.fields.CharField', [], {'max_length': '800', 'blank': 'True'}),
            'files_url': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_id': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'image_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'image_url': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'kickstart': ('django.db.models.fields.TextField', [], {}),
            'log': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'logfile_url': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'notify': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'overlay': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'queue': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app.Queue']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'IN QUEUE'", 'max_length': '30'}),
            'test_image': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'test_options': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'test_result': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'test_results_url': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'tokenmap': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'app.imagetype': {
            'Meta': {'object_name': 'ImageType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'})
        },
        'app.queue': {
            'Meta': {'object_name': 'Queue'},
            'handle_launch': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'app.token': {
            'Meta': {'object_name': 'Token'},
            'default': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        }
    }

    complete_apps = ['app']
