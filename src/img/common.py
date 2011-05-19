'''
Created on Oct 11, 2010

@author: locusfwork
'''
import os

from img.worker import ImageWorker
from urlparse import urlparse

import pykickstart.parser as ksparser
import pykickstart.version as ksversion
from pykickstart.handlers.control import commandMap
from pykickstart.handlers.control import dataMap

from mic.imgcreate.kscommands import desktop 
from mic.imgcreate.kscommands import moblinrepo
from mic.imgcreate.kscommands import micboot

import ConfigParser
from  RuoteAMQP.workitem import DictAttrProxy

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
    with open(ksfile_name, mode='w+b') as ksfile:
        ksfile.write(kickstart)
    os.chmod(ksfile_name, 0644)

    worker = ImageWorker(image_id=iid, ksfile_name=ksfile_name,
                         image_type=itype, 
                         name=name, release=release, arch=arch,
                         dir_prefix=dir_prefix)
    result = worker.build()

    return result


def get_worker_config(conffile="/etc/imager/img.conf"):
    config = ConfigParser.ConfigParser()
    config.read(conffile)

    conf = {
            "base_url" : config.get('worker', 'base_url'),
            "base_dir" : config.get('worker', 'base_dir'),
            "use_kvm"  : config.getboolean('worker', 'use_kvm'),
            "use_sudo" : config.getboolean('worker', 'use_sudo'),
            "mic_args" : config.get('worker', 'mic_opts'),
            "img_home" : config.get('worker', 'img_home'),
            "img_tmp"  : config.get('worker', 'img_tmp'),
           }

    if config.has_option("worker", "ssh_key"):
        conf["ssh_key"] = config.get("worker", "ssh_key")
    else:
        conf["ssh_key"] = os.path.join(conf["img_home"], 'id_rsa')
    
    if config.has_option("worker", "base_img"):
        conf["base_img"] = config.get("worker", "base_img")
    else:
        conf["base_img"] = os.path.join(conf["img_home"], 'base.img')

    dap = DictAttrProxy(conf)

    return dap

