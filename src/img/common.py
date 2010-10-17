'''
Created on Oct 11, 2010

@author: locusfwork
'''
import os
import io
import random
import pwd,grp
try:
     import json
except ImportError:
     import simplejson as json
from amqplib import client_0_8 as amqp
from worker import ImageWorker
import ConfigParser

from urlparse import urlparse

import pykickstart.commands as kscommands
import pykickstart.constants as ksconstants
import pykickstart.errors as kserrors
import pykickstart.parser as ksparser
import pykickstart.version as ksversion
from pykickstart.handlers.control import commandMap
from pykickstart.handlers.control import dataMap

from mic.imgcreate.kscommands import desktop 
from mic.imgcreate.kscommands import moblinrepo
from mic.imgcreate.kscommands import micboot

conf = open("/etc/imager/img.conf")
config = ConfigParser.ConfigParser()
config.readfp(conf)
conf.close()

base_url = config.get('worker', 'base_url')
base_dir = config.get('worker', 'base_dir')
reposerver = config.get('worker','reposerver')
using_version = ksversion.DEVEL
commandMap[using_version]["desktop"] = desktop.Moblin_Desktop
commandMap[using_version]["repo"] = moblinrepo.Moblin_Repo
commandMap[using_version]["bootloader"] = micboot.Moblin_Bootloader
dataMap[using_version]["RepoData"] = moblinrepo.Moblin_RepoData
superclass = ksversion.returnClassForVersion(version=using_version)



class KSHandlers(superclass):
    def __init__(self, mapping={}):
        superclass.__init__(self, mapping=commandMap[using_version])
    
def build_kickstart(base_ks, packages=None, groups=None, projects=None):
    ks = ksparser.KickstartParser(KSHandlers())
    ks.readKickstart(base_ks)
    if packages:
        ks.handler.packages.add(packages)
    if groups:
        ks.handler.packages.add(groups)
    if projects:
        for prj in project:
            name = urlparse(prj).path
            name = name.replace(":/","_")
            name = name.replace("/","_")
            ks.handler.repo.repoList.append(moblinrepo.Moblin_RepoData(baseurl=prj, name=name))
    return ks

def mic2(id, name,  type, email, kickstart, release, arch="i686", work_item=None, chan=None):
        dir = "%s/%s"%(base_dir, id)
        print dir
        os.mkdir(dir, 0775)
        
        ksfilename = ""
        ksfilename = dir+'/'+name+'.ks'
        
        tmp = open(ksfilename, mode='w+b')
        print tmp.name   
        tmpname = tmp.name
        logfile_name = dir+'/'+name+"-log"
        tmp.write(kickstart)            
        tmp.close()
        os.chmod(tmpname, 0644)
        file = base_url+"%s"%id    
        logfile = open(logfile_name,'w')
        logurl = base_url+id+'/'+os.path.split(logfile.name)[-1]
        if chan:
            data = json.dumps({"status":"WORKER BEGIN", "id":str(id), 'url':str(file), 'log':str(logfile_name)})
            statusmsg = amqp.Message(data)
            chan.basic_publish(statusmsg, exchange="django_result_exchange", routing_key="status")
        worker = ImageWorker(id, tmpname, type, logfile, dir, work_item=work_item, chan=chan, name=name, release=release, arch=arch)
        worker.build()
        logfile.close()
