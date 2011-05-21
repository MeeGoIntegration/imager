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

from img.common import worker_config
from img.worker import ImageWorker
from  RuoteAMQP.workitem import DictAttrProxy

class ParticipantHandler(object):
    """ Participant class as defined by the SkyNET API """

    def __init__(self):
        self.worker_config = None

    def handle_wi_control(self, ctrl):
        """ job control thread """
        pass

    def handle_lifecycle_control(self, ctrl):
        """ participant control thread """
        if ctrl.message == "start":
            self.worker_config = worker_config(config=ctrl.config)

    def handle_wi(self, wid):
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

        jargs = DictAttrProxy(args_dict)

        if (not jargs.image_id or not jargs.kickstart or not jargs.image_type
            or not jargs.name or not jargs.arch):
            f.__error__ = "One of the mandatory fields: id, kickstart, type,"\
                          " name and arch in the image namespace doesn't exist."
            f.msg.append(f.__error__)
            raise RuntimeError("Missing mandatory field")

        if jargs.extra_opts:
            if not isinstance(jargs.extra_opts, list):
                f.__error__ = "Expected extra_opts field to be a list"
                f.msg.append(f.__error__)
                raise RuntimeError("Wrong type of field")
            if self.worker_config.extra_opts:
                jargs.extra_opts.extend(self.worker_config.extra_opts)

        if not jargs.prefix or jargs.prefix == "":
            jargs.prefix = "requests"

        try:
            worker = ImageWorker(config=self.worker_config,
                                 job_args=jargs)

            result = worker.build()

            f.image.update(worker.get_results())

            msg = "Image %s build for arch %s" % (f.image.name, f.image.arch)

            if result:
                msg = "%s succeeded \nfiles: %s \nimage: %s \nlog %s" % (msg, \
                      f.image.files_url, f.image.image_url,f.image.image_log)
            else:
                msg = "%s failed \nlog %s" % (msg, f.image.image_log)

            f.msg.append(msg)

            wid.result = result
        except Exception:
            f.__error__ = 'Image build FAILED'
            f.msg.append(f.__error__)
            raise

