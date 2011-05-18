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

import os, time, tempfile
from img.common import build_kickstart

class ParticipantHandler(object):
    """ Participant class as defined by the SkyNET API """
    def __init__(self):
        self.reposerver = ""
        self.ksstore = ""

    def handle_wi_control(self, ctrl):
        """ job control thread """
        pass

    def handle_lifecycle_control(self, ctrl):
        """ participant control thread """
        if ctrl.message == "start":
            self.reposerver = ctrl.config.get("build_ks", "reposerver")
            self.ksstore = ctrl.config.get("build_ks", "ksstore")

    def handle_wi(self, wid):
        # We may want to examine the fields structure
        if wid.fields.debug_dump or wid.params.debug_dump:
            print wid.dump()

        wid.result = False
        f = wid.fields
        if not f.msg:
            f.msg = []
        if not f.ksfile or not f.kickstart:
            f.__error__ = "One of the mandatory fields: kickstart or ksfile"\
                          " does not exist."
            f.msg.append(f.__error__)
            raise RuntimeError("Missing mandatory field")

        projects = []
        if f.project and f.repository:
            project = f.project
            repo = f.repository
            project = project.replace(":", ":/")
            repo = repo.replace(":", ":/")
            url = "%s/%s/%s" % (self.reposerver, project, repo)
            projects = [ url ]

        packages = []
        if wid.params.packages_from :
            packages = f.as_dict()[wid.params.packages_from]
        elif f.packages:
            packages = f.packages

        groups = []
        if wid.params.groups_from :
            groups = f.as_dict()[wid.params.groups_from]
        elif f.groups:
            groups = f.groups

        remove = False
        ksfile = ""

        if f.ksfile:
            ksfile = os.path.join(self.ksstore, f.ksfile)
        elif f.kickstart:
            kstemplate = tempfile.NamedTemporaryFile(delete=False)
            kstemplate.write(f.kickstart)
            kstemplate.close()
            ksfile = kstemplate.name
            remove = ksfile

        try:
            ks = build_kickstart(ksfile, packages=packages, groups=groups,
                                 projects=projects)
            f.kickstart = ks
        except Exception, error:
            f.__error__ = "Failed to handle kickstart. %s" % error
            f.msg.append(f.__error__)
            raise
        finally:
            if remove:
                os.remove(remove)

        if f.ev.rid:
            f.iid = "%s-%s" % (str(f.ev.rid), time.strftime('%Y%m%d-%H%M%S'))
        else:
            f.iid = time.strftime('%Y%m%d-%H%M%S')

        if not f.name:
            f.name = os.path.basename(ksfile)[0:-3]

        f.msg.append("Kickstart handled successfully.")
        wid.result = True
