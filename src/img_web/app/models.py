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

from django.db import models
import os
import img_web.settings as settings
import shutil
from django.contrib.auth.models import User
from django.contrib import admin
from django.db.models.signals import post_save
from RuoteAMQP import Launcher

def imagejob_save_callback(sender, **kwargs):
    if kwargs['created']:
        try:
            with open(settings.process_filename, mode='r') as process_file:
                process = process_file.read()
    
            job = kwargs['instance']
            fields = {"image" : { "kickstart" : job.kickstart,
                                  "extra_repos" : job.extra_repos.split(","),
                                  "packages" : job.overlay.split(","),
                                  "image_id" : job.image_id,
                                  "image_type" : job.image_type,
                                  "name" : job.name,
                                  "release" : job.release,
                                  "arch" : job.arch,
                                  "prefix" : "ondemand"
                                  }
                        }
    
            launcher = Launcher(amqp_host = settings.boss_host,
                                amqp_user = settings.boss_user,
                                amqp_pass = settings.boss_pass,
                                amqp_vhost = settings.boss_vhost)
    
            launcher.launch(process, fields)
        except Exception, error:
            kwargs['instance'].status = "ERROR"
            kwargs['instance'].error = error
            kwargs['instance'].save()




# Create your models here.
class ImageJob(models.Model):    
    image_id = models.CharField(max_length=30)
    created = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(User, null=True)
    email = models.CharField(max_length=40)

    test_image = models.BooleanField(blank=True, default=False)
    devicegroup = models.CharField(blank=True, default="", max_length=100)

    image_type = models.CharField(max_length=10)
    release = models.CharField(max_length=50)
    arch = models.CharField(max_length=10)

    overlay = models.CharField(max_length=500)
    extra_repos = models.CharField(max_length=800)
    
    kickstart = models.CharField(max_length=1000)
    name = models.CharField(max_length=100)

    status = models.CharField(max_length=30, default="IN QUEUE")
    imagefile = models.CharField(max_length=50)
    filename = models.CharField(max_length=40)
    logfile = models.CharField(max_length=50)
    error = models.CharField(max_length=500)

class ImageJobAdmin(admin.ModelAdmin):
    list_display = ('image_id', 'user', 'arch', 'image_type', 'status')
    list_filter = ('user', 'arch', 'image_type', 'status')

admin.site.register(ImageJob, ImageJobAdmin)

post_save.connect(imagejob_save_callback, sender=ImageJob, weak=False,
                  dispatch_uid="imagejob_save_callback")

