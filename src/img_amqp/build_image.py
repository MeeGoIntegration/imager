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

try:
     import json
except ImportError:
     import simplejson as json
import subprocess as sub
from subprocess import CalledProcessError
import os, sys, random, pwd, grp, traceback
import daemon
from tempfile import TemporaryFile, NamedTemporaryFile, mkdtemp
import shutil
import re
import time
import optparse
import tempfile
from amqplib import client_0_8 as amqp
from img.worker import ImageWorker
from img.common import mic2,build_kickstart

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

import ConfigParser

config = ConfigParser.ConfigParser()
config.read('/etc/imager/img.conf')

parser = optparse.OptionParser()
parser.add_option("-n", "--num_worker", dest="num",
                  help="Number for this worker", metavar="NUM")
(options, args) = parser.parse_args()

amqp_host = config.get('amqp', 'amqp_host')
amqp_user = config.get('amqp', 'amqp_user')
amqp_pwd = config.get('amqp', 'amqp_pwd')
amqp_vhost = config.get('amqp', 'amqp_vhost')
#num_workers = config.getint('worker', 'num_workers')
base_dir = config.get('worker', 'base_dir')
base_url = config.get('worker', 'base_url')
use_kvm = config.get('worker', 'use_kvm')
reposerver = config.get('worker', 'reposerver')
templates_dir = config.get('worker', 'templates_dir')

# Daemon information
participant_name = "build_image"
d = config.get(participant_name, 'daemon')
daemonize = False
if d == "Yes":
    daemonize = True

config_logfile = config.get(participant_name, 'logfile')
config_logfile = config_logfile+'.'+options.num+'.log'
config_pidfile = config.get(participant_name,'pidfile')
config_pidfile = config_pidfile+'.'+options.num+'.pid'
runas_user = config.get(participant_name, 'runas_user')
runas_group = config.get(participant_name, 'runas_group')
uid = pwd.getpwnam(runas_user)[2]
gid = grp.getgrnam(runas_group)[2]
# if not root...kick out
if not os.geteuid()==0:
    sys.exit("\nOnly root can run this script\n")
if not os.path.exists('/dev/kvm') and use_kvm == "yes":
    sys.exit("\nYou must enable KVM kernel module\n")

conn = ""
chan = ""

def img_amqp_init():
    global conn 
    conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
    global chan 
    chan = conn.channel()

    chan.queue_declare(queue="image_queue", durable=True, exclusive=False, auto_delete=False)
    chan.queue_declare(queue="kickstarter_queue", durable=True, exclusive=False, auto_delete=False)
    chan.queue_declare(queue="status_queue", durable=False, exclusive=False, auto_delete=False)
    
    chan.exchange_declare(exchange="image_exchange", type="direct", durable=True, auto_delete=False,)
    chan.exchange_declare(exchange="django_result_exchange", type="direct", durable=True, auto_delete=False,)
    
    chan.queue_bind(queue="image_queue", exchange="image_exchange", routing_key="img")
    chan.queue_bind(queue="kickstarter_queue", exchange="image_exchange", routing_key="ks")
    chan.queue_bind(queue="status_queue", exchange="django_result_exchange", routing_key="status")

    return conn, chan
    
using_version = ksversion.DEVEL
commandMap[using_version]["desktop"] = desktop.Moblin_Desktop
commandMap[using_version]["repo"] = moblinrepo.Moblin_Repo
commandMap[using_version]["bootloader"] = micboot.Moblin_Bootloader
dataMap[using_version]["RepoData"] = moblinrepo.Moblin_RepoData
superclass = ksversion.returnClassForVersion(version=using_version)

class KSHandlers(superclass):
    def __init__(self, mapping={}):
        superclass.__init__(self, mapping=commandMap[using_version])

    

def mic2_callback(msg):  
    print "mic2"
    job = json.loads(msg.body)    
    email = job["email"]
    id = job["id"]    
    type = job['imagetype']
    ksfile = job['ksfile']   
    name = job['name']
    release = job['release']
    arch = None
    if 'arch' in job:
        arch = job['arch']
    file = base_url+id
    data = json.dumps({"status":"IN QUEUE", "id":str(id), 'url':str(file)})
    statusmsg = amqp.Message(data)
    chan.basic_publish(statusmsg, exchange="django_result_exchange", routing_key="status")
    mic2(id, name, type, email, ksfile, release, arch, chan=chan)        
    sys.stdout.flush()
 
def kickstarter_callback(msg):
    print "ks"
    kickstarter = json.loads(msg.body)    
    config = kickstarter["config"]
    email = kickstarter["email"]    
    id = kickstarter['id']
    imagetype = kickstarter['imagetype']
    release = kickstarter['release']
    arch = kickstarter['arch']
    config = kickstarter['config']
    name = kickstarter['name']
    kstemplate = tempfile.NamedTemporaryFile(delete=False)
    kstemplate.write(config['Template'])
    kstemplate.close()
    packages = config['Packages'] if 'Packages' in config.keys() else []
    groups = config['Groups'] if 'Groups' in config.keys() else []
    projects = config['Projects'] if 'Projects' in config.keys() else []
    try:
        print "Trying to construct KS"
        ks = build_kickstart(kstemplate.name, packages = packages, groups = groups, projects = projects)
    except Exception, error:
        print "KS validation error"
        data = json.dumps({"status":"ERROR", "error":"%s"%error, "id":str(id)})
        statusmsg = amqp.Message(data)
        chan.basic_publish(statusmsg, exchange="django_result_exchange", routing_key="status")
        os.remove(kstemplate.name)
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        return
    # We got the damn thing published, move on
    ksfile = str(ks.handler)
    os.remove(kstemplate.name)
    data = json.dumps({'email':email, 'id':id, 'imagetype':imagetype, 'ksfile':ksfile, 'name':name, 'release':release, 'arch':arch})
    msg2 = amqp.Message(data)        
    chan.basic_publish(msg2, exchange="image_exchange", routing_key="img")        
    
    print "ks end"
    sys.stdout.flush()
    
def main():
    conn, chan = img_amqp_init()
    chan.basic_consume(queue='image_queue', no_ack=True, callback=mic2_callback)
    chan.basic_consume(queue='kickstarter_queue', no_ack=True, callback=kickstarter_callback)
    while True:
        chan.wait()
    chan.basic_cancel("img")
    chan.basic_cancel("ks")
    chan.close()
    conn.close()

if __name__ == "__main__":
    if daemonize:
        log = open(config_logfile,'a+')
        pidf = open(config_pidfile,'a+')
        os.chown(config_logfile,int(uid),int(gid))
        os.chown(config_pidfile,int(uid),int(gid))
        with daemon.DaemonContext(stdout=log, stderr=log, uid=uid, gid=gid, files_preserve=[pidf]):
            pidf.write(str(os.getpid()))
            pidf.close()
            main()
    else:
        main()
