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
from worker import ImageWorker
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

import os, sys
from tempfile import TemporaryFile, NamedTemporaryFile, mkdtemp


# if not root...kick out
if not os.geteuid()==0:
    sys.exit("\nOnly root can run this script\n")
if not os.path.exists('/dev/kvm'):
    sys.exit("\nYou must enable KVM kernel module\n")
    
class MICParticipant(Participant):
    __job_pool = None
    def mic2(self, id, type, email, kickstart, wi):
        dir = "%s/%s"%(base_dir, id)
        os.mkdir(dir, 0775)    
        tmp = NamedTemporaryFile(dir=dir, delete=False)    
        tmpname = tmp.name
        logfile_name = tmp.name+"-log"
        tmp.write(kickstart)    
        tmp.close()    
        file = base_url+"%s"%id    
        logfile = open(logfile_name,'w')
        logurl = base_url+id+'/'+os.path.split(logfile.name)[-1]
        worker = ImageWorker(id, tmpname, type, logfile, dir, work_item=wi)    
        worker.build()
        logfile.close()
        
    def consume(self):
        wi = self.workitem
        email = wi.lookup('email')
        kickstart = wi.lookup('kickstart')
        id = wi.lookup('id')
        type = wi.lookup('type')
        print "Workitem: "
        print json.dumps(wi.to_h())
        args = (id, type, email, kickstart)
        #self.__job_pool = Pool(2)
        self.mic2(id, type, email, kickstart, wi)
        #self.__job_pool.apply_async(mic2, args)
        
if __name__ == "__main__":
    print "Started a python participant"
    p = MICParticipant(ruote_queue="mic", amqp_vhost="ruote-test")
    p.register("mic", {'queue':'mic'})
    p.run()
    
        
