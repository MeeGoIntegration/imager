#~ Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
#~ Contact: Ramez Hanna <ramez.hanna@nokia.com>
#~ This program is free software: you can redistribute it and/or modify
#~ it under the terms of the GNU General Public License as published by
#~ the Free Software Foundation, either version 3 of the License, or
#~ (at your option) any later version.

#~ This program is distributed in the hope that it will be useful,
#~ but WITHOUT ANY WARRANTY; without even the implied warranty of
#~ MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#~ GNU General Public License for more details.

#~ You should have received a copy of the GNU General Public License
#~ along with this program.  If not, see <http://www.gnu.org/licenses/>.
import json

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
import img_web.settings as settings
from django.contrib.auth.models import User
from django.contrib import admin
from django.db.models.signals import post_save, post_delete
import django.dispatch
from RuoteAMQP import Launcher
from taggit.managers import TaggableManager

def launch(process, fields):
    """ BOSS process launcher

    :param process: process definition
    :param fields: dict of workitem fields
    """

    launcher = Launcher(amqp_host = settings.boss_host,
                        amqp_user = settings.boss_user,
                        amqp_pass = settings.boss_pass,
                        amqp_vhost = settings.boss_vhost)

    fields.update({"priority" : "high"})
    launcher.launch(process, fields)

def imagejob_delete_callback(sender, **kwargs):
    """ utility function to launch the delete process as a callback to the
    post_delete signal of the an ImageJob object """

    pass

def imagejob_save_callback(sender, **kwargs):
    """ utility function to launch the save process as a callback to the
    post_save signal of the an ImageJob object. if the associated Queue object
    has handling enabled and this is a just created object  it will launch a
    create image process, else if it is an update to an already existing object
    notify and test processes are optionally launched """

    job = kwargs['instance']

    if not job.queue.handle_launch:
        return

    fields = job.to_fields()

    if kwargs['created']:
        try:
            with open(settings.create_image_process, mode='r') as process_file:
                process = process_file.read()
    
            launch(process, fields)

        except Exception as error:
            kwargs['instance'].status = "ERROR"
            kwargs['instance'].error = error
            kwargs['instance'].save()
    else:
        for pp in job.post_processes.filter(active=True):
            try:
                state = JobState.objects.get(name=job.status)
            except JobState.DoesNotExist:
                continue

            if state in pp.triggers.all():
                launch(pp.pdef, fields)

class Queue(models.Model):    
    name = models.CharField(max_length=30)
    handle_launch = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class JobState(models.Model):

    def __str__(self):
        return self.name

    name = models.CharField(max_length=30, unique=True)

class PostProcess(models.Model):

    def __str__(self):
        return self.name

    name = models.CharField(max_length=40, unique=True)
    active = models.BooleanField(default=True)
    default = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    pdef = models.TextField(blank=False)
    argname = models.CharField(max_length=40, blank=True)
    triggers = models.ManyToManyField(JobState)

class ImageJob(models.Model):    
    """ An instance of this ImageJob model contains all the information needed
    to reproduce an image usin mic2 """

    tags = TaggableManager()

    def mytags(self):
       return [ x.name for x in self.tags.all() ]

    def has_tag(self, tagname):
        if tagname in self.mytags():
            return True
        return False

    @property
    def pinned(self):
        return self.has_tag("pinned")

    def to_fields(self):
        fields = {"image" : {
                          "kickstart" : self.kickstart,
                          "image_id" : self.image_id,
                          "image_type" : self.image_type,
                          "name" : self.name,
                          "arch" : self.arch,
                          "prefix" : "%s/%s" % (self.queue.name,
                                                self.user.username),
                          "result" : self.status
                          }
                }

        if self.image_url:
            fields['image']['image_url'] = self.image_url
        if self.tokenmap:
            fields['image']['tokenmap'] = self.tokenmap
        if self.overlay:
            fields['image']['packages'] = self.overlay.split(",")
        if self.extra_repos:
            fields['image']['extra_repos'] = self.extra_repos.split(",")
        if self.pp_args:
            pp_args = json.loads(self.pp_args)
            fields['image'].update(pp_args)

        return fields

    image_id = models.CharField(max_length=60, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    done = models.DateTimeField(blank=True, null=True)
    queue = models.ForeignKey(Queue, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    test_result = models.BooleanField(blank=True, default=False)
    test_results_url = models.TextField(blank=True, null=True)

    image_type = models.CharField(max_length=10)
    tokenmap = models.CharField(max_length=1000, blank=True)
    arch = models.CharField(max_length=10)

    overlay = models.CharField(max_length=500, blank=True)
    extra_repos = models.CharField(max_length=800, blank=True)

    kickstart = models.TextField()
    name = models.CharField(max_length=100)

    status = models.CharField(max_length=30, default="IN QUEUE")
    image_url = models.CharField(max_length=500, blank=True)
    files_url = models.CharField(max_length=500, blank=True)
    logfile_url = models.CharField(max_length=500, blank=True)
    error = models.CharField(max_length=1000, blank=True)

    post_processes = models.ManyToManyField(PostProcess)
    pp_args = models.TextField(blank=True)

class BuildService(models.Model):

    name = models.CharField(max_length=50, unique=True)
    apiurl = models.CharField(max_length=250, unique=True)

    def __unicode__(self):
        return self.name

class Arch(models.Model):

    def __unicode__(self):
        return self.name

    name = models.CharField(max_length=50, unique=True)

class ImageType(models.Model):

    def __unicode__(self):
        return self.name

    name = models.CharField(max_length=20, unique=True)

class Token(models.Model):

    def __unicode__(self):
        return self.name

    name = models.CharField(max_length=40, unique=True)
    default = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)


class ImageJobAdmin(admin.ModelAdmin):
    list_display = ('image_id', 'user', 'arch', 'image_type', 'status', 'queue')
    list_filter = ('user', 'arch', 'image_type', 'status', 'queue')

class QueueAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

class BuildServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'apiurl')

class ArchAdmin(admin.ModelAdmin):
    list_display = ('name',)

class ImageTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)

class TokenAdmin(admin.ModelAdmin):
    list_display = ('name',)

class JobStateAdmin(admin.ModelAdmin):
    list_display = ('name',)

class PostProcessAdmin(admin.ModelAdmin):
    list_display = ('name',)

admin.site.register(ImageJob, ImageJobAdmin)
admin.site.register(Queue, QueueAdmin)
admin.site.register(BuildService, BuildServiceAdmin)
admin.site.register(Arch, ArchAdmin)
admin.site.register(ImageType, ImageTypeAdmin)
admin.site.register(Token, TokenAdmin)
admin.site.register(JobState, JobStateAdmin)
admin.site.register(PostProcess, PostProcessAdmin)

post_save.connect(imagejob_save_callback, sender=ImageJob, weak=False,
                  dispatch_uid="imagejob_save_callback")

post_delete.connect(imagejob_delete_callback, sender=ImageJob, weak=False,
                    dispatch_uid="imagejob_delete_callback")
