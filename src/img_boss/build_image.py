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
"""builds images from kickstart files using MIC2 image creation tools. 
Supports either KVM or normal MIC2 operation. KVM operations offer more 
flexibility and cleaner building.

.. warning ::

   * The build_ks participant should be used to read and validate kickstart 
     files, and subsequently fills the image.kickstart field.
   * The image_id field is expected to be unique, as provided by the 
     request_image participant which records it in a django database


:term:`Workitem` fields IN:

:Parameters:
   :image.kickstart (string):
      Contents of a kickstart file. Refer to :
      `<http://wiki.meego.com/Image_Configurations_-_KickStart_Files>`_
      for a description of kickstart files
   :image.image_id (string):
      Unique ID of this image job
   :image.prefix (string):
      added as another directory layer under which images will be saved
      Optional. If not provided "requests" will be used. 
   :image.image_type (string):
      Format of image as supported by mic2. ex: livecd, raw, etc..
      Check the available formats in mic2 --help
   :image.name (string):
      Name of the image, usually the name of the kickstart in the format
      `$VERTICAL-$ARCH-$VARIANT` , required by mic2 when using the --release
      option ex: meego-core-ia32-minimal
   :image.release (string):
      Turns on release creation in mic2
   :image.arch (string):
      Architecture of image. ex: i586, armv7l, etc ..,
   :image.extra_opts (list):
      list of extra options to be passed verbatim to mic2

:term:`Workitem` fields OUT:

:Returns:
  :image.result (Boolean):
     True if mic2 returned with status 0, False otherwise
  :image.files_url (string):
     base URL at which all files produced by mic2 can be accessed
  :image.image_url (string):
     URL to download the image file directly
  :image.logfile_url (string):
     URL to the mic2 logfile
  :image.error (string):
     Any errors returned by mic2
  :result (Boolean):
     True if everything was OK, False otherwise
"""

from img.common import worker_config
from img.worker import ImageWorker
from RuoteAMQP.workitem import DictAttrProxy as dap
from RuoteAMQP import Launcher 

class ParticipantHandler(object):
    """Participant class as defined by the SkyNET API"""

    def __init__(self):
        self.worker_config = None
        self.launcher = None
        self.process = \
        """Ruote.process_definition 'create_image_ondemand' do
             sequence do
               set :f => 'debug_dump', :value => 'true'
               update_image_status :status => '%s'
             end
           end
        """

    def handle_wi_control(self, ctrl):
        """ job control thread """
        pass

    def handle_lifecycle_control(self, ctrl):
        """ participant control thread """
        if ctrl.message == "start":
            self.worker_config = dap(worker_config(config=ctrl.config))
            self.launcher = Launcher(amqp_host = ctrl.config.get("boss",
                                                                 "amqp_host"),
                                     amqp_user = ctrl.config.get("boss",
                                                                 "amqp_user"),
                                     amqp_pass = ctrl.config.get("boss",
                                                                 "amqp_pwd"),
                                     amqp_vhost = ctrl.config.get("boss",
                                                                  "amqp_vhost")
                                     )
 

    def push_img_status(self, status, fields):
        """ function to push status by launching a process, ?utility """
        self.launcher.launch(self.process % status, fields)

    def handle_wi(self, wid):
        """Handle the workitem so that an image is created from the kickstart
        file correctly. One needs the kickstart as a complete file in the
        workitem, an unique id for image, image type as defined by MIC2, name
        for the image and architecture that the image root filesystem will use.
        """
        # We may want to examine the fields structure
        if wid.fields.debug_dump or wid.params.debug_dump:
            print wid.dump()

        wid.result = False
        f = wid.fields
        if not f.msg:
            f.msg = []

        if f.image:
            # new API, image namespace
            args_dict = f.image.as_dict()
        else:
            # old API, flat workitem
            args_dict = {
                          "kickstart" : f.kickstart,
                          "image_id" : f.image_id,
                          "image_type" : f.image_type,
                          "name" : f.name,
                          "release" : f.release,
                          "arch" : f.arch,
                          "prefix" : f.prefix,
                          "extra_opts" : f.extra_opts
                         }
            f.image = args_dict

        jargs = dap(args_dict)

        if (not jargs.image_id or not jargs.kickstart or not jargs.image_type
            or not jargs.name or not jargs.arch):
            missing = [fname for fname in ("image_id", "kickstart",
                                           "image_type", "name", "arch")
                             if not (args_dict.has_key(fname) and
                                     args_dict[fname])]
            f.__error__ = "One of the mandatory fields: id, kickstart, type,"\
                          " name and arch in the image namespace doesn't exist."
            f.msg.append(f.__error__)
            raise RuntimeError("Missing mandatory fields: %s"
                               % ",".join(missing))

        if jargs.extra_opts:
            if not isinstance(jargs.extra_opts, list):
                f.__error__ = "Expected extra_opts field to be a list"
                f.msg.append(f.__error__)
                raise RuntimeError("Wrong type of field")
        else:
            jargs.extra_opts = []

        if self.worker_config.extra_opts:
            jargs.extra_opts.extend(self.worker_config.extra_opts)

        if not jargs.prefix or jargs.prefix == "":
            jargs.prefix = "requests"

        try:
            worker = ImageWorker(config=self.worker_config,
                                 job_args=jargs)

            results = worker.get_results()

            image = f.image.as_dict()

            image.update(results)

            f.image = image

            self.push_img_status("BUILDING", f.as_dict())

            worker.build()

            results = worker.get_results()

            image = f.image.as_dict()

            image.update(results)

            f.image = image

            msg = "Image %s build for arch %s" % (f.image.name, f.image.arch)

            if f.image.result:
                msg = "%s succeeded \nfiles: %s \nimage: %s \nlog %s" % (msg, \
                      f.image.files_url, f.image.image_url,f.image.logfile_url)
            else:
                msg = "%s failed \nlog %s\nerror %s" % (msg, f.image.image_log,
                                                        f.image.error)
                f.__error__ = 'Image build FAILED: %s' % f.image.error
                f.msg.append(f.__error__)

            f.msg.append(msg)

            wid.result = f.image.result
        except Exception, error:
            f.__error__ = 'Image build FAILED: %s' % error
            f.msg.append(f.__error__)
            raise
        finally:
            if wid.result:
                self.push_img_status("DONE", f.as_dict())
            else:
                self.push_img_status("ERROR", f.as_dict())

