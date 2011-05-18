'''
Created on Oct 11, 2010

@author: locusfwork
'''
import os

from worker import ImageWorker
from urlparse import urlparse

import pykickstart.parser as ksparser
import pykickstart.version as ksversion
from pykickstart.handlers.control import commandMap
from pykickstart.handlers.control import dataMap

from mic.imgcreate.kscommands import desktop 
from mic.imgcreate.kscommands import moblinrepo
from mic.imgcreate.kscommands import micboot

KSCLASS = ksversion.returnClassForVersion(version=ksversion.DEVEL)

class KSHandlers(KSCLASS):
    def __init__(self):
        ver = ksversion.DEVEL
        commandMap[ver]["desktop"] = desktop.Moblin_Desktop
        commandMap[ver]["repo"] = moblinrepo.Moblin_Repo
        commandMap[ver]["bootloader"] = micboot.Moblin_Bootloader
        dataMap[ver]["RepoData"] = moblinrepo.Moblin_RepoData
        KSCLASS.__init__(self, mapping=commandMap[ver])
    
def build_kickstart(base_ks, packages=[], groups=[], projects=[]):
    ks = ksparser.KickstartParser(KSHandlers())
    ks.readKickstart(base_ks)
    ks.handler.packages.add(packages)
    ks.handler.packages.add(groups)
    for prj in projects:
        name = urlparse(prj).path
        name = name.replace(":/","_")
        name = name.replace("/","_")
        repo = moblinrepo.Moblin_RepoData(baseurl=prj, name=name)
        ks.handler.repo.repoList.append(repo)
    ks_txt = str(ks.handler)
    return ks_txt

def mic2(iid, name, itype, kickstart, release, arch,
         base_dir="/tmp", dir_prefix="unknown"):
    idir = os.path.join(base_dir, dir_prefix, iid)
    os.makedirs(idir, 0775)

    ksfile_name = os.path.join(idir, "%s.ks" % name)
    ksfile = open(ksfile_name, mode='w+b')
    ksfile.write(kickstart)
    ksfile.close()

    logfile_name = os.path.join(idir, "%s.log" % name)
    logfile = open(logfile_name,'w+b')

    os.chmod(ksfile_name, 0644)
    os.chmod(logfile_name, 0644)

    worker = ImageWorker(iid, ksfile_name, itype, logfile, idir,
                         name=name, release=release, arch=arch,
                         dir_prefix=dir_prefix)
    result = worker.build()

    logfile.close()

    return result
