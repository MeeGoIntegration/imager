# -*- coding: utf-8 -*-
import datetime
from django import db
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [ ('app', '0001_initial'), ]
    
    def forwards(self, orm):
        # Adding model 'JobState'
        db.create_table('app_jobstate', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
        ))
        db.send_create_signal('app', ['JobState'])

        # Adding model 'PostProcess'
        db.create_table('app_postprocess', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('default', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('pdef', self.gf('django.db.models.fields.TextField')()),
            ('argname', self.gf('django.db.models.fields.CharField')(max_length=40, blank=True)),
        ))
        db.send_create_signal('app', ['PostProcess'])

        # Adding M2M table for field triggers on 'PostProcess'
        db.create_table('app_postprocess_triggers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('postprocess', models.ForeignKey(orm['app.postprocess'], null=False)),
            ('jobstate', models.ForeignKey(orm['app.jobstate'], null=False))
        ))
        db.create_unique('app_postprocess_triggers', ['postprocess_id', 'jobstate_id'])

        # Deleting field 'ImageJob.notify'
        db.delete_column('app_imagejob', 'notify')

        # Deleting field 'ImageJob.test_options'
        db.delete_column('app_imagejob', 'test_options')

        # Deleting field 'ImageJob.log'
        db.delete_column('app_imagejob', 'log')

        # Deleting field 'ImageJob.email'
        db.delete_column('app_imagejob', 'email')

        # Deleting field 'ImageJob.devicegroup'
        db.delete_column('app_imagejob', 'devicegroup')

        # Deleting field 'ImageJob.test_image'
        db.delete_column('app_imagejob', 'test_image')

        # Adding field 'ImageJob.pp_args'
        db.add_column('app_imagejob', 'pp_args',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding M2M table for field post_processes on 'ImageJob'
        db.create_table('app_imagejob_post_processes', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('imagejob', models.ForeignKey(orm['app.imagejob'], null=False)),
            ('postprocess', models.ForeignKey(orm['app.postprocess'], null=False))
        ))
        db.create_unique('app_imagejob_post_processes', ['imagejob_id', 'postprocess_id'])

        # Adding unique constraint on 'ImageJob', fields ['image_id']
        db.create_unique('app_imagejob', ['image_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'ImageJob', fields ['image_id']
        db.delete_unique('app_imagejob', ['image_id'])

        # Deleting model 'JobState'
        db.delete_table('app_jobstate')

        # Deleting model 'PostProcess'
        db.delete_table('app_postprocess')

        # Removing M2M table for field triggers on 'PostProcess'
        db.delete_table('app_postprocess_triggers')

        # Adding field 'ImageJob.notify'
        db.add_column('app_imagejob', 'notify',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'ImageJob.test_options'
        db.add_column('app_imagejob', 'test_options',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'ImageJob.log'
        db.add_column('app_imagejob', 'log',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'ImageJob.email'
        db.add_column('app_imagejob', 'email',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'ImageJob.devicegroup'
        db.add_column('app_imagejob', 'devicegroup',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True),
                      keep_default=False)

        # Adding field 'ImageJob.test_image'
        db.add_column('app_imagejob', 'test_image',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Deleting field 'ImageJob.pp_args'
        db.delete_column('app_imagejob', 'pp_args')

        # Removing M2M table for field post_processes on 'ImageJob'
        db.delete_table('app_imagejob_post_processes')


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
            'done': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'}),
            'extra_repos': ('django.db.models.fields.CharField', [], {'max_length': '800', 'blank': 'True'}),
            'files_url': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '60'}),
            'image_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'image_url': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'kickstart': ('django.db.models.fields.TextField', [], {}),
            'logfile_url': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'overlay': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'post_processes': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['app.PostProcess']", 'symmetrical': 'False'}),
            'pp_args': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'queue': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app.Queue']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'IN QUEUE'", 'max_length': '30'}),
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
        'app.jobstate': {
            'Meta': {'object_name': 'JobState'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'app.postprocess': {
            'Meta': {'object_name': 'PostProcess'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'argname': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'pdef': ('django.db.models.fields.TextField', [], {}),
            'triggers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['app.JobState']", 'symmetrical': 'False'})
        },
        'app.queue': {
            'Meta': {'object_name': 'Queue'},
            'handle_launch': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'app.token': {
            'Meta': {'object_name': 'Token'},
            'default': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
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
