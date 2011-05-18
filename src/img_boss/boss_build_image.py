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

from img.common import mic2
import json


class ParticipantHandler(object):
    """ Participant class as defined by the SkyNET API """

    def handle_wi_control(self, ctrl):
        """ job control thread """
        pass

    def handle_lifecycle_control(self, ctrl):
        """ participant control thread """
        pass

    def handle_wi(self, wid):
        # We may want to examine the fields structure
        if wid.fields.debug_dump or wid.params.debug_dump:
            print wid.dump()

        wid.result = False
        f = wid.fields
        if not f.msg:
            f.msg = []
        email = f.email
        kickstart = f.kickstart
        iid = f.id
        itype = f.type
        name = f.name
        release = f.release
        archs = f.archs
        if not iid or not kickstart or not itype or not name or not archs:
            f.__error__ = "One of the mandatory fields: id, kickstart, type,"\
                          " name and archs does not exist."
            f.msg.append(f.__error__)
            raise RuntimeError("Missing mandatory field")

        prefix = "requests"
        if f.prefix and not f.prefix == "":
            prefix = f.prefix
        try:
            for arch in archs:
                mic2(iid, name, itype,  email, kickstart, release, arch,
                     dir_prefix=prefix, work_item=f)
            f.msg.append("Image %s for arch %s build result was %s"\
                         "files at: %s" % (name, arch, f.status, f.url))
            wid.result = True
        except Exception:
            f.msg.append('Image build FAILED')
            raise

