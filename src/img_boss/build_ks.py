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

"""Used to manipulate kickstart files in many ways :

   * Validation : it will disassemble and reassemble a kickstart and raise
     various exceptions in case of errors.
   * Augmentation : it can insert repositories, packages, package groups into
     a kickstart.
   * Generation : It can generate kickstarts from a YAML kickstarter files
     (Not yet Implemented)

   Refer to :
   `<http://wiki.meego.com/Image_Configurations_-_KickStart_Files>`_
   for a description of kickstart files.

.. warning ::

   * Running the defineimage participant first might be useful in adding some 
     meaningful extra packages in the image.packages field, usually in the 
     context of a process handling a promotion request

:term:`Workitem` fields IN:

:Parameters:
   :ev.actions (list):
      OPTIONAL Only used if the "packages_event" parameter is passed submit
      request data structure :term:`actions`
   :image.ksfile (string):
      Full path to a local readable kickstart file under the "ksstore" 
      directory which is configured in the conf file
   :image.kickstart (string):
      Contents of a kickstart file
   :image.extra_repos (list):
      OPTIONAL URLs of package repositories that will be added to the kickstart
      file
   :image.groups (list):
      OPTIONAL Group names to be added to the kickstart file
   :image.packages (list):
      OPTIONAL Package names to be added to the kickstart file
   :project (string):
      OPTIONAL Name of an OBS project which publishes packages to the
      "reposerver" set in the configuration
   :repository (string):
      OPTIONAL Name of the repository in the above project
   
   
:term:`Workitem` params IN

:Parameters:
   :pacakges (list):
      If preset will be added to the extra packages list
   :packages_event (Boolean):
      If present the packages in the actions array from a submit request are
      added to the kickstart file
   :packages_from (string):
      Arbitary field name from which to get a list of package names, typically
      used when a participant provides package names in a new namespace
   :groups (list):
      If preset will be added to the extra groups list
   :groups_from (string):
      Arbitary field name from which to get a list of group names, typicall used
      when a participant provides group names in a new namespace

:term:`Workitem` fields OUT:

:Returns:
   :image.kickstart (string):
      Validated and augmented kickstart file contents
   :image.name (string):
      If not already set, the basename of the kickstart file is used
   :result (Boolean):
      True if the kickstart handling went OK, False otherwise

"""


import os, tempfile
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
        """ Workitem handling function """
        # We may want to examine the fields structure
        if wid.fields.debug_dump or wid.params.debug_dump:
            print wid.dump()

        wid.result = False
        f = wid.fields
        if not f.msg:
            f.msg = []

        if not f.image:
            raise RuntimeError("Missing mandatory field: image")

        if not f.image.ksfile and not f.image.kickstart:
            raise RuntimeError("Missing mandatory field: image.kickstart"\
                               " or image.ksfile")

        projects = []
        if f.project and f.repository:
            project = f.project
            repo = f.repository
            project = project.replace(":", ":/")
            repo = repo.replace(":", ":/")
            url = "%s/%s/%s" % (self.reposerver, project, repo)
            projects = [ url ]

        if f.image.extra_repos:
            if isinstance(f.image.extra_repos, list):
                projects.extend(f.image.extra_repos)
            else:
                raise RuntimeError("extra_repos field should be a list")

        packages = []
        if wid.params.packages:
            if isinstance(f.params.packages, list):
                packages.extend(wid.params.packages)
            else:
                raise RuntimeError("packages parameter should be a list")
        if wid.params.packages_from:
            extra_packages = f.as_dict()[wid.params.packages_from]
            if isinstance(extra_packages, list):
                packages.extend(extra_packages)
            else:
                raise RuntimeError("field %s should be a list"
                                   % wid.params.packages_from)
        if wid.params.packages_event:
            packages.extend( [act['sourcepackage'] for act in f.ev.actions] )
        if f.image.packages:
            if isinstance(f.image.packages, list):
                packages.extend(f.image.packages)
            else:
                raise RuntimeError("image.packages field should be a list")

        groups = []
        if wid.params.groups:
            if isinstance(f.params.groups, list):
                groups.extend(wid.params.groups)
            else:
                raise RuntimeError("groups parameter should be a list")
        if wid.params.groups_from:
            extra_groups = f.as_dict()[wid.params.groups_from]
            if isinstance(extra_groups, list):
                groups.extend(extra_groups)
            else:
                raise RuntimeError("field %s should be a list"
                                   % wid.params.groups_from)
        if f.image.groups:
            if isinstance(f.image.groups, list):
                groups.extend(f.image.groups)
            else:
                raise RuntimeError("groups field should be a list")

        remove = False
        ksfile = ""

        if f.image.ksfile:
            ksfile = os.path.join(self.ksstore, f.image.ksfile)
        elif f.image.kickstart:
            with tempfile.NamedTemporaryFile(delete=False) as kstemplate:
                kstemplate.write(f.image.kickstart)
            ksfile = kstemplate.name
            remove = ksfile
        try:
            ks = build_kickstart(ksfile, packages=packages, groups=groups,
                                 projects=projects)
            f.image.kickstart = ks
        finally:
            if remove:
                os.remove(remove)

        if not f.image.name:
            f.image.name = os.path.basename(ksfile)[0:-3]

        f.msg.append("Kickstart handled successfully.")
        wid.result = True
