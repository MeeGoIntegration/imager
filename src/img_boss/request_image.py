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

.. warning ::

   * The build_ks participant should be used to read and validate kickstart 
     files, and subsequently fills the image.kickstart field.


:term:`Workitem` fields IN:

:Parameters:
   image.kickstart(string): 
      Contents of a kickstart file. Refer to :
      `<http://wiki.meego.com/Image_Configurations_-_KickStart_Files>`_
      for a description of kickstart files
   image.image_type(string):
      Format of image as supported by mic2. ex: livecd, raw, etc..
      Check the available formats in mic2 --help
   image.name(string):
      Name of the image, usually the name of the kickstart in the format
      `$VERTICAL-$ARCH-$VARIANT` , required by mic2 when using the --release
      option ex: meego-core-ia32-minimal
   image.release(string):
      Turns on release creation in mic2
   image.arch(string):
      Architecture of image. ex: i586, armv7l, etc..
   image.emails(list):
      emails that will be notified. Django will not handle notifications for
      jobs that originate from BOSS process, this is just a record. The process
      is responsible for doing its own notifications as it sees fit
   image.devicegroup(string):
      OTS devicegroup. Testing is handled by the process and this is only just
      a record of it
   image.extra_opts(list):
      list of extra options to be passed verbatim to mic2

:term:`Workitem` fields OUT:

:Returns:
   image.image_id(string):
      Unique ID of this image job
   image.prefix(string):
      added as another directory layer under which images will be saved
      Optional. "requests/username" will be used. 
  result(Boolean)
      True if everything was OK, False otherwise
"""

import os, time
from  RuoteAMQP.workitem import DictAttrProxy as dap

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
        # We may want to examine the fields structure
        if wid.fields.debug_dump or wid.params.debug_dump:
            print wid.dump()

        wid.result = False
        f = wid.fields
        if not f.msg:
            f.msg = []

        if (not f.ev.rid):
            f.__error__ = "One of the mandatory fields: rid,"\
                          " name and arch in the image namespace doesn't exist."
            f.msg.append(f.__error__)
            raise RuntimeError("Missing mandatory field")

        job = ImageJob()

        job.image_id = "%s-%s" % ( str(f.ev.rid),
                                   time.strftime('%Y%m%d-%H%M%S') )

        job.queue = Queue.objects.get(name="requests")
        job.user = self.user
        job.email = f.image.emails
        job.image_type = f.image.image_type
        job.arch = f.image.arch
        if f.image.release:
            job.release = f.image.release
        if f.image.devicegroup:
            job.devicegroup = f.image.devicegroup
        if f.image.extra_opts:
            job.test_options = f.image.extra_opts

        job.kickstart = f.image.kickstart
        job.name = f.image.name

        job.save()

        f.image.prefix = "%s/%s" % (job.queue.name,
                                    job.user.username)
        f.image.image_id = job.image_id 

        print "Requested image %s" % f.image.image_id
        wid.result = True 
