#!/usr/bin/python
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
"""Records an image job request in the django database of the web UI. Thus
facilitating tracking and controlling it and later on removing it.

This is useful to allow visibility of non-IMG processes in the IMG queue.

This participant does not block and build_image should be called in the controlling process at some point after request_image.

Once build_image is done, update_image_status can be called to set a status on the image.

.. warning::
    The build_ks participant should have run first to provide the name and
    kickstart fields

:term:`Workitem` fields IN:

:Parameters:
   :action (string):
      "get_or_create" is the only supported value. If set the participant will
      try to find an already created image with the parameters specified. When not
      set or set to any unkown value the backward compatible default is to always
      create a new job
   :max_age (integer):
      In days, if specified along with get_or_create will limit the search to images
      that are older than max_age days

:term:`Workitem` fields IN:

:Parameters:
   :image.kickstart (string):
      Contents of a kickstart file. Refer to :
      `<http://wiki.meego.com/Image_Configurations_-_KickStart_Files>`_
      for a description of kickstart files
   :image.image_type (string):
      Format of image as supported by mic. ex: livecd, raw, etc..
      Check the available formats in mic --help
   :image.name (string):
      Name of the image, usually the name of the kickstart in the format
      `$VERTICAL-$ARCH-$VARIANT` , required by mic when using the --release
      option ex: meego-core-ia32-minimal
   :image.release (string):
      Turns on release creation in mic
   :image.arch (string):
      Architecture of image. ex: i586, armv7l, etc..
   :image.emails (list):
      emails that will be notified. Django will not handle notifications for
      jobs that originate from BOSS process, this is just a record. The process
      is responsible for doing its own notifications as it sees fit
   :image.devicegroup (string):
      OTS devicegroup. Testing is handled by the process and this is only just
      a record of it
   :image.extra_opts (list):
      list of extra options to be passed verbatim to mic
   :image.queue (string):
      OPTIONAL If provided, specifies the IMG qeuee to be used.
      defaults to "requests"
   :image.prefix (string):
      OPTIONAL If provided, specifies the path prefix where the resulting files
      will be stored
      defaults to "requests"

:term:`Workitem` fields OUT:

:Returns:
   :image.image_id (string):
      Unique ID of this image job
   :image.prefix (string):
      added as another directory layer under which images will be saved
      Optional. "requests/username" will be used. 
   :result (Boolean):
      True if everything was OK, False otherwise
"""

import os, time
import datetime

os.environ['DJANGO_SETTINGS_MODULE'] = 'img_web.settings'
from img_web.app.models import ImageJob, Queue
from django.contrib.auth.models import User

class ParticipantHandler(object):

    def __init__(self):
        self.user = None

    def handle_wi_control(self, ctrl):
        """ job control thread """
        pass

    def handle_lifecycle_control(self, ctrl):
        """ participant control thread """
        if ctrl.message == "start":
            if ctrl.config.has_option("request_image", "username"):
                username = ctrl.config.get("request_image", "username")
                self.user = User.objects.get(username__exact=username)
            else:
                self.user = User.objects.get(id=1)
 
    def handle_wi(self, wid):
        wid.result = False
        f = wid.fields
        p = wid.params
        if not f.msg:
            f.msg = []

        if (not f.ev or not f.ev.id or not f.image.kickstart
            or not f.image.image_type or not f.image.arch or not f.image.name):
            f.__error__ = "One of the mandatory fields: ev.id,"\
                          " image.kickstart, image_type, image.arch,"\
                          " or image.name doesn't exist."
            f.msg.append(f.__error__)
            raise RuntimeError("Missing mandatory field")

        qname = "requests"
        if f.image.queue and not f.image.queue == "web":
            qname = f.image.queue
        queue = Queue.objects.get(name=qname)

        image_args = { "queue" : queue, "user" : self.user,
                       "image_type" : f.image.image_type,
                       "arch" : f.image.arch,
                       "kickstart" : f.image.kickstart,
                       "name" : f.image.name
                      }
        if f.emails:
            image_args["email"] = ",".join(f.emails)
        else:
            image_args["email"] = self.user.email
        if f.image.devicegroup:
            image_args["devicegroup"] = f.image.devicegroup
        if f.image.extra_opts:
            image_args["test_options"] = f.image.extra_opts
        if f.image.tokenmap:
            image_args["tokenmap"] = f.image.tokenmap

        job = None
        if wid.params.action == "get_or_create":
            self.log.info("get_or_create")
            jobs = ImageJob.objects.filter(**image_args).filter(status__startswith="DONE")
            if wid.params.max_age:
                ts = datetime.datetime.now() - datetime.timedelta(int(wid.params.max_age))
                self.log.info(ts)
                jobs.filter(done__gte = ts)
            self.log.info(jobs.count())
            if jobs.count():
                job = jobs[0]
                f.image.image_url = job.image_url
                f.image.files_url = job.files_url
                f.image.logfile_url = job.logfile_url
 
        if not job:
            self.log.info("New job")
            job = ImageJob(**image_args)
            job.image_id = "%s-%s" % ( str(f.ev.id),
                                       time.strftime('%Y%m%d-%H%M%S') )
            job.save()
            f.image.image_url = ""

        f.image.prefix = "%s/%s" % (job.queue.name,
                                    job.user.username)
        f.image.image_id = job.image_id 

        self.log.info("Requested image %s" % f.image.image_id)
        wid.result = True 
