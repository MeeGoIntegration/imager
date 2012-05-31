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
   :ev.namespace (string):
      OPTIONAL Only used if the "project" field is set and the "repository"
      parameter is not set. Used to contact the right OBS instance.
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
      "reposerver" set in the configuration. URLs to all repositories in
      this project will be added to the kickstart file.
   
   
:term:`Workitem` params IN

:Parameters:
   :packages (list):
      If present will be added to the extra packages list
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
   :repository (string):
      OPTIONAL Only used if the "project" field is set. Add only this repository
      to the kickstart file.

:term:`Workitem` fields OUT:

:Returns:
   :image.kickstart (string):
      Validated and augmented kickstart file contents
   :image.name (string):
      If not already set, the basename of the kickstart file is used
   :result (Boolean):
      True if the kickstart handling went OK, False otherwise

"""


import json
import os
import tempfile
from urllib2 import HTTPError

from pykickstart.errors import KickstartError
from optparse import OptionValueError

from img.common import build_kickstart
from buildservice import BuildService

def get_list(value, desc):
    """Check if the value is a list, and complain (RuntimeError) if it's not.
    """
    if not value:
        return []
    if isinstance(value, basestring):
        try:
            value = json.loads(value)
        except ValueError:
            pass
    if isinstance(value, list):
        return value
    raise RuntimeError("%s should be a list" % desc)

class ParticipantHandler(object):
    """ Participant class as defined by the SkyNET API """
    def __init__(self):
        self.reposerver = ""
        self.ksstore = ""
        self.oscrc = ""

    def handle_wi_control(self, ctrl):
        """ job control thread """
        pass

    def handle_lifecycle_control(self, ctrl):
        """ participant control thread """
        if ctrl.message == "start":
            self.reposerver = ctrl.config.get("build_ks", "reposerver")
            self.ksstore = ctrl.config.get("build_ks", "ksstore")
            if ctrl.config.has_option("obs", "oscrc"):
                self.oscrc = ctrl.config.get("obs", "oscrc")

    def get_repositories(self, wid, project):
        if not wid.fields.ev or not wid.fields.ev.namespace:
            raise RuntimeError("Missing field: ev.namespace")
        obs = BuildService(oscrc=self.oscrc, apiurl=wid.fields.ev.namespace)
        try:
            repositories = obs.getProjectRepositories(project)
        except HTTPError, exobj:
            if exobj.code == 404:
                raise RuntimeError("Project %s not found in OBS" % project)
            raise
        return repositories

    def handle_wi(self, wid):
        """ Workitem handling function """
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
        if f.project:
            if wid.params.repository:
                repositories = [ wid.params.repository ]
            else:
                repositories = self.get_repositories(wid, f.project)
            for repo in repositories:
                projects.append("%s/%s/%s" % (self.reposerver,
                                              f.project.replace(":", ":/"),
                                              repo.replace(":", ":/")))

        if f.image.extra_repos:
            projects.extend(get_list(f.image.extra_repos, "extra_repos field"))

        packages = []
        packages.extend(get_list(wid.params.packages, "packages parameter"))
        if wid.params.packages_from:
            extra_packages = f.as_dict().get(wid.params.packages_from, None)
            packages.extend(get_list(extra_packages,
                            "field %s" % wid.params.packages_from))
        if wid.params.packages_event:
            packages.extend([act['targetpackage'] for act in f.ev.actions])
        packages.extend(get_list(f.image.packages, "image.packages field"))

        groups = []
        groups.extend(get_list(wid.params.groups, "groups parameter"))
        if wid.params.groups_from:
            extra_groups = f.as_dict().get(wid.params.groups_from, None)
            groups.extend(get_list(extra_groups,
                                   "field %s" % wid.params.groups_from))
        groups.extend(get_list(f.image.groups, "groups field"))

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
        except (KickstartError, OptionValueError), error:
            f.msg.append("Error while handling  Kickstart: %s" % error)
            f.__error__ = str(error)
        else:
            if not f.image.name:
                f.image.name = os.path.basename(ksfile)[0:-3]

            f.msg.append("Kickstart handled successfully.")
            wid.result = True
        finally:
            if remove:
                os.remove(remove)

