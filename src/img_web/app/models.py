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

# Create your models here.
class ImageJob(models.Model):    
    email = models.CharField(max_length=40)
    filename = models.CharField(max_length=40)
    logfile = models.CharField(max_length=50)
    task_id = models.CharField(max_length=30)
    imagefile = models.CharField(max_length=50)    
    created = models.DateTimeField(auto_now_add=True)
    error = models.CharField(max_length=500)
    type = models.CharField(max_length=10)
    status = models.CharField(max_length=30)
    test_image = models.BooleanField(blank=True, default=False)
    devicegroup = models.CharField(blank=True, default="", max_length=100)
    notify = models.BooleanField(blank=True, default=False)
    def delete(self, *args, **kwargs):
        topdir = os.path.join(settings.IMGDIR, self.task_id) + os.sep
        if os.path.exists(topdir):
            shutil.rmtree(topdir)
            super(ImageJob, self).delete(*args, **kwargs)

