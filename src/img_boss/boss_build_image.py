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
        prefix = "requests"
        extra_opts = []

        if not f.msg:
            f.msg = []
        if f.image:
            # new API, image namespace
            kickstart = f.image.kickstart
            image_id = f.image.image_id
            image_type = f.image.image_type
            name = f.image.name
            release = f.release
            arch = f.image.arch
            if f.image.prefix and not f.image.prefix == "":
                prefix = f.image.prefix
            if f.image.extra_opts and isinstance(f.image.extra_opts, list):
                extra_opts = f.image.extra_opts
        else:
            # old API, flat workitem
            kickstart = f.kickstart
            image_id = f.image_id
            image_type = f.image_type
            name = f.name
            release = f.release
            arch = f.arch
            if f.prefix and not f.prefix == "":
                prefix = f.prefix
            if f.extra_opts and isinstance(f.extra_opts, list):
                extra_opts = f.extra_opts
            f.image = {}

        if self.worker_config.extra_opts:
            extra_opts.extend(self.worker_config.extra_opts)

        if not image_id or not kickstart or not image_type or not name\
                or not arch:
            f.__error__ = "One of the mandatory fields: id, kickstart, type,"\
                          " name and archs does not exist."
            f.msg.append(f.__error__)
            raise RuntimeError("Missing mandatory field")

        try:
            job_args = { "image_id" : image_id, 
                         "image_name" : name,
                         "image_type" : image_type,
                          "kickstart" : kickstart,
                          "release" :  release, 
                          "arch" : arch,
                          "prefix" : prefix,
                          "extra_opts" : extra_opts
                         }

            worker = ImageWorker(config=self.worker_config,
                                 job_args=job_args)

            result = worker.build()

            results = worker.get_results()

            f.image.update(results)


            msg = "Image %s build for arch %s" % (name, arch)

            if result:
                msg = "%s succeeded \nfiles: %s \nimage: %s \nlog %s" % (msg, \
                      results["files_url"], results["image_url"],\
                      results["image_log"])
            else:
                msg = "%s failed \nlog %s" % (msg, \
                      results["image_log"])

            wid.result = result
        except Exception:
            f.__error__ = ('Image build FAILED')
            f.msg.append(f.__error__)
            raise

