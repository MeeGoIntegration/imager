#!/usr/bin/python2.6
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

import os, sys, traceback, ConfigParser, optparse, io, pwd, grp
from tempfile import TemporaryFile, NamedTemporaryFile, mkdtemp
import daemon

from  RuoteAMQP.workitem import Workitem
from  RuoteAMQP.participant import Participant

from img.worker import ImageWorker

try:
     import simplejson as json
except ImportError:
     import json

from multiprocessing import Process, Queue, Pool


participant_name = "build_image"

# Fallback configuration. If you need to customize it, copy it somewhere 
# ( ideally to your system's configuration directory ), modify it and 
# pass it with the -c option
defaultconf = """[boss]
amqp_host = 127.0.0.1:5672
amqp_user = boss
amqp_pwd = boss
amqp_vhost = boss
[%s]
daemon = Yes 
logfile = /var/log/%s.log
runas_user = root
runas_group = root
[worker]
base_url = http://192.168.11.2/images/
base_dir = /var/www/images
num_workers = 2
post_creation = /bin/echo
use_kvm = yes
; Example, mic_opts = --save-kernel, --use_comps, so comma separated options
mic_opts =
""" % ( participant_name, participant_name )

parser = optparse.OptionParser()
parser.add_option("-c", "--config", dest="filename",
                  help="read configuration from CFILE", metavar="CFILE")
(options, args) = parser.parse_args()

try:
    conf = open(options.filename)
except:
    # Fallback
    conf = io.BytesIO(defaultconf)

config = ConfigParser.ConfigParser()
config.readfp(conf)
conf.close()

amqp_vhost = config.get('boss', 'amqp_vhost')
amqp_pwd = config.get('boss', 'amqp_pwd')
amqp_user = config.get('boss', 'amqp_user')
amqp_host = config.get('boss', 'amqp_host')
d = config.get(participant_name, 'daemon')
daemonize = False
if d == "Yes":
    daemonize = True

logfile = config.get(participant_name, 'logfile')
runas_user = config.get(participant_name, 'runas_user')
runas_group = config.get(participant_name, 'runas_group')
uid = pwd.getpwnam(runas_user)[2]
gid = grp.getgrnam(runas_group)[2]

use_kvm = config.get('worker', 'use_kvm')
base_url = config.get('worker', 'base_url')
base_dir = config.get('worker', 'base_dir')
post = config.get('worker', 'post_creation')

# if not root...kick out
if not os.geteuid()==0:
    sys.exit("\nOnly root can run this script\n")
if not os.path.exists('/dev/kvm') and use_kvm == "yes":
    sys.exit("\nYou must enable KVM kernel module\n")
    
class MICParticipant(Participant):
    __job_pool = None
    def mic2(self, id, name,  type, email, kickstart, release, arch):
        dir = "%s/%s"%(base_dir, id)
        os.mkdir(dir, 0775)    
        tmp = open(dir+'/'+name+'.ks', mode='w+b')    
        tmpname = tmp.name
        logfile_name = dir+'/'+name+"-log"
        tmp.write(kickstart)            
        tmp.close()
        os.chmod(tmpname, 0644)
        file = base_url+"%s"%id    
        logfile = open(logfile_name,'w')
        logurl = base_url+id+'/'+os.path.split(logfile.name)[-1]
        worker = ImageWorker(id, tmpname, type, logfile, dir, work_item=self.workitem, name=name, release=release, arch=arch)
        worker.build()
        logfile.close()
        
    def consume(self):
        try:
            wi = self.workitem
            email = wi.lookup('email')
            kickstart = wi.lookup('kickstart')
            id = wi.lookup('id')
            type = wi.lookup('type')
            name = wi.lookup('name')
            release = wi.lookup('release')
            arch = wi.lookup('arch')
            print "Workitem: "
            print json.dumps(wi.to_h())
            if kickstart:
              self.mic2(id, name, type,  email, kickstart, release, arch)
            result = True
        except Exception as e:
            print type(e)
            print e
            traceback.print_exc(file=sys.stdout)
            result = False
            pass
        wi.set_result(result)

def main():
    print "Image building participant running"
    # Create an instance
    p = MICParticipant(ruote_queue=participant_name, amqp_host=amqp_host,  amqp_user=amqp_user, amqp_pass=amqp_pwd, amqp_vhost=amqp_vhost)
    # Register with BOSS
    p.register(participant_name, {'queue':participant_name})
    # Enter event loop
    p.run()

if __name__ == "__main__":
    if daemonize:
        log = open(logfile,'a+')
        with daemon.DaemonContext(stdout=log, stderr=log, uid=uid, gid=gid):
            main()
    else:
        main()

