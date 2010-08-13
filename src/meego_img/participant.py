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

from  RuoteAMQP.workitem import Workitem
from  RuoteAMQP.participant import Participant
#import image_creator
try:
     from worker import ImageWorker
except ImportError:
     from worker.worker import ImageWorker	
try:
     import simplejson as json
except ImportError:
     import json
from multiprocessing import Process, Queue, Pool
import ConfigParser

config = ConfigParser.ConfigParser()
config.read('/etc/imger/img.conf')
base_url = config.get('worker', 'base_url')
base_dir = config.get('worker', 'base_dir')
post = config.get('worker', 'post_creation')
amqp_host = config.get('boss', 'amqp_host')
amqp_user = config.get('boss', 'amqp_user')
amqp_pass = config.get('boss', 'amqp_pwd')
amqp_vhost = config.get('boss', 'amqp_vhost')
use_kvm = config.get('worker', 'use_kvm')
import os, sys
from tempfile import TemporaryFile, NamedTemporaryFile, mkdtemp


# if not root...kick out
if not os.geteuid()==0:
    sys.exit("\nOnly root can run this script\n")
if not os.path.exists('/dev/kvm') and use_kvm == "yes":
    sys.exit("\nYou must enable KVM kernel module\n")
    
class MICParticipant(Participant):
    __job_pool = None
    def mic2(self, id, name,  type, email, kickstart, wi, release):
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
        worker = ImageWorker(id, tmpname, type, logfile, dir, work_item=wi, name=name, release=release)    
        worker.build()
        logfile.close()
        
    def consume(self):
        wi = self.workitem
        email = wi.lookup('email')
        kickstart = wi.lookup('kickstart')
        id = wi.lookup('id')
        type = wi.lookup('type')
        name = wi.lookup('name')
        release = wi.lookup('release')
        print "Workitem: "
        print json.dumps(wi.to_h())
        if kickstart:
          self.mic2(id, name, type,  email, kickstart, wi, release)
        
if __name__ == "__main__":
    print "Started a python participant"
    p = MICParticipant(ruote_queue="build_image", amqp_host=amqp_host,  amqp_user=amqp_user, amqp_pass=amqp_pass, amqp_vhost=amqp_vhost)
    p.register("build_image", {'queue':'build_image'})
    p.run()
    
        
