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
   :project (string):
      OPTIONAL Name of an OBS project which publishes packages to the
      "reposerver" set in the configuration. URLs to all repositories in
      this project will be added to the kickstart file.
   :repository (string):
      OPTIONAL Only used if the "project" parameter is set. Add only this repository
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
from optparse import OptionValueError
from buildservice import BuildService
from urlparse import urlparse

try:
    import pykickstart.parser as ksparser
    import pykickstart.version as ksversion
    from pykickstart.handlers.control import commandMap
    from pykickstart.handlers.control import dataMap
    from pykickstart.base import *
    from pykickstart.errors import *
    from pykickstart.options import *
    from pykickstart.commands.bootloader import *
    from pykickstart.commands.repo import *
    from pykickstart.commands.partition import *
except:
    raise RuntimeError("Couldn't import pykickstart")

# Verbatim inclusion from mic upstream
#################################################################

# Copyright (c) 2008, 2009, 2010 Intel, Inc.
#
# Yi Yang <yi.y.yang@intel.com>
# Anas Nashif
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; version 2 of the License
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 59
# Temple Place - Suite 330, Boston, MA 02111-1307, USA.

class Moblin_Desktop(KickstartCommand):
    def __init__(self, writePriority=0,
                       defaultdesktop=None,
                       defaultdm=None,
                       autologinuser="meego",
                       session=None):

        KickstartCommand.__init__(self, writePriority)

        self.__new_version = False
        self.op = self._getParser()

        self.defaultdesktop = defaultdesktop
        self.autologinuser = autologinuser
        self.defaultdm = defaultdm
        self.session = session

    def __str__(self):
        retval = ""

        if self.defaultdesktop != None:
            retval += " --defaultdesktop=%s" % self.defaultdesktop
        if self.session != None:
            retval += " --session=\"%s\"" % self.session
        if self.autologinuser != None:
            retval += " --autologinuser=%s" % self.autologinuser
        if self.defaultdm != None:
            retval += " --defaultdm=%s" % self.defaultdm

        if retval != "":
            retval = "# Default Desktop Settings\ndesktop %s\n" % retval

        return retval

    def _getParser(self):
        try:
            op = KSOptionParser(lineno=self.lineno)
        except TypeError:
            # the latest version has not lineno argument
            op = KSOptionParser()
            self.__new_version = True

        op.add_option("--defaultdesktop", dest="defaultdesktop",
                                          action="store",
                                          type="string",
                                          nargs=1)
        op.add_option("--autologinuser", dest="autologinuser",
                                         action="store",
                                         type="string",
                                         nargs=1)
        op.add_option("--defaultdm", dest="defaultdm",
                                     action="store",
                                     type="string",
                                     nargs=1)
        op.add_option("--session", dest="session",
                                   action="store",
                                   type="string",
                                   nargs=1)
        return op

    def parse(self, args):
        if self.__new_version:
            (opts, extra) = self.op.parse_args(args=args, lineno=self.lineno)
        else:
            (opts, extra) = self.op.parse_args(args=args)

        if extra:
            m = _("Unexpected arguments to %(command)s command: %(options)s") \
                  % {"command": "desktop", "options": extra}
            raise KickstartValueError, formatErrorMsg(self.lineno, msg=m)

        self._setToSelf(self.op, opts)


class Moblin_Bootloader(F8_Bootloader):
    def __init__(self, writePriority=10, appendLine="", driveorder=None,
                 forceLBA=False, location="", md5pass="", password="",
                 upgrade=False, menus=""):
        F8_Bootloader.__init__(self, writePriority, appendLine, driveorder,
                                forceLBA, location, md5pass, password, upgrade)

        self.menus = ""

    def _getArgsAsStr(self):
        ret = F8_Bootloader._getArgsAsStr(self)

        if self.menus == "":
            ret += " --menus=%s" %(self.menus,)
        return ret

    def _getParser(self):
        op = F8_Bootloader._getParser(self)
        op.add_option("--menus", dest="menus")
        return op


class Moblin_RepoData(F8_RepoData):
    def __init__(self, baseurl="", mirrorlist="", name="", priority=None,
                 includepkgs=[], excludepkgs=[], save=False, proxy=None,
                 proxy_username=None, proxy_password=None, debuginfo=False,
                 source=False, gpgkey=None, disable=False, ssl_verify="yes"):
        F8_RepoData.__init__(self, baseurl=baseurl, mirrorlist=mirrorlist,
                             name=name,  includepkgs=includepkgs,
                             excludepkgs=excludepkgs)
        self.save = save
        self.proxy = proxy
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        self.debuginfo = debuginfo
        self.disable = disable
        self.source = source
        self.gpgkey = gpgkey
        self.ssl_verify = ssl_verify.lower()
        self.priority = priority

    def _getArgsAsStr(self):
        retval = F8_RepoData._getArgsAsStr(self)

        if self.save:
            retval += " --save"
        if self.proxy:
            retval += " --proxy=%s" % self.proxy
        if self.proxy_username:
            retval += " --proxyuser=%s" % self.proxy_username
        if self.proxy_password:
            retval += " --proxypasswd=%s" % self.proxy_password
        if self.debuginfo:
            retval += " --debuginfo"
        if self.source:
            retval += " --source"
        if self.gpgkey:
            retval += " --gpgkey=%s" % self.gpgkey
        if self.disable:
            retval += " --disable"
        if self.ssl_verify:
            retval += " --ssl_verify=%s" % self.ssl_verify
        if self.priority:
            retval += " --priority=%s" % self.priority

        return retval

class Moblin_Repo(F8_Repo):
    def __init__(self, writePriority=0, repoList=None):
        F8_Repo.__init__(self, writePriority, repoList)

    def __str__(self):
        retval = ""
        for repo in self.repoList:
            retval += repo.__str__()

        return retval

    def _getParser(self):
        def list_cb (option, opt_str, value, parser):
            for d in value.split(','):
                parser.values.ensure_value(option.dest, []).append(d)

        op = F8_Repo._getParser(self)
        op.add_option("--save", action="store_true", dest="save",
                      default=False)
        op.add_option("--proxy", type="string", action="store", dest="proxy",
                      default=None, nargs=1)
        op.add_option("--proxyuser", type="string", action="store",
                      dest="proxy_username", default=None, nargs=1)
        op.add_option("--proxypasswd", type="string", action="store",
                      dest="proxy_password", default=None, nargs=1)
        op.add_option("--debuginfo", action="store_true", dest="debuginfo",
                      default=False)
        op.add_option("--source", action="store_true", dest="source",
                      default=False)
        op.add_option("--disable", action="store_true", dest="disable",
                      default=False)
        op.add_option("--gpgkey", type="string", action="store", dest="gpgkey",
                      default=None, nargs=1)
        op.add_option("--ssl_verify", type="string", action="store",
                      dest="ssl_verify", default="yes")
        op.add_option("--priority", type="int", action="store", dest="priority",
                      default=None)
        return op

# Marko Saukko <marko.saukko@cybercom.com>
#
# Copyright (C) 2011 Nokia Corporation and/or its subsidiary(-ies).
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2. This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.


class MeeGo_PartData(FC4_PartData):
    removedKeywords = FC4_PartData.removedKeywords
    removedAttrs = FC4_PartData.removedAttrs

    def __init__(self, *args, **kwargs):
        FC4_PartData.__init__(self, *args, **kwargs)
        self.deleteRemovedAttrs()
        self.align = kwargs.get("align", None)

    def _getArgsAsStr(self):
        retval = FC4_PartData._getArgsAsStr(self)

        if self.align:
            retval += " --align"

        return retval

class MeeGo_Partition(FC4_Partition):
    removedKeywords = FC4_Partition.removedKeywords
    removedAttrs = FC4_Partition.removedAttrs

    def _getParser(self):
        op = FC4_Partition._getParser(self)
        # The alignment value is given in kBytes. e.g., value 8 means that
        # the partition is aligned to start from 8096 byte boundary.
        op.add_option("--align", type="int", action="store", dest="align",
                      default=None)
        return op
#################################################################

KSCLASS = ksversion.returnClassForVersion(version=ksversion.DEVEL)

class KSHandlers(KSCLASS):
    """Helper class for parsing a kickstart file"""
    def __init__(self):
        ver = ksversion.DEVEL
        commandMap[ver]["desktop"] = Moblin_Desktop
        commandMap[ver]["repo"] = Moblin_Repo
        commandMap[ver]["bootloader"] = Moblin_Bootloader
        dataMap[ver]["RepoData"] = Moblin_RepoData
        KSCLASS.__init__(self, mapping=commandMap[ver])
    
def build_kickstart(base_ks, packages=[], groups=[], projects=[]):
    """Build a kickstart file using the handler class, with custom kickstart,
    packages, groups and projects.

    :param base_ks: Full path to the original kickstart file
    :param packages: list of packagenames
    :param groups: list of groupnames
    :param projects: list of rpm repository URLs

    :returns: Validated kickstart with any extra packages, groups or repourls
       added
    """
    ks = ksparser.KickstartParser(KSHandlers())
    ks.readKickstart(str(base_ks))
    ks.handler.packages.add(packages)
    ks.handler.packages.add(groups)
    for prj in projects:
        name = urlparse(prj).path
        name = name.replace(":/","_")
        name = name.replace("/","_")
        repo = Moblin_RepoData(baseurl=prj, name=name, save=True)
        ks.handler.repo.repoList.append(repo)
    ks_txt = str(ks.handler)
    return ks_txt

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

        if f.image.extra_repos:
            projects.extend(get_list(f.image.extra_repos, "extra_repos field"))

        if wid.params.project:
            if wid.params.repository:
                repositories = [ wid.params.repository ]
            else:
                repositories = self.get_repositories(wid, wid.params.project)
            for repo in repositories:
                repourl = "%s/%s/%s" % (self.reposerver,
                                        wid.params.project.replace(":", ":/"),
                                        repo.replace(":", ":/"))
                projects.append(repourl)

       f.image.extra_repos = projects

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
        except (KickstartError, OptionValueError, ValueError), error:
            f.msg.append("Error while handling  Kickstart: %s" % error)
            f.__error__ = str(error)
        else:
            if not f.image.name:
                f.image.name = os.path.basename(ksfile)[0:-3]

            wid.result = True
        finally:
            if remove:
                os.remove(remove)

