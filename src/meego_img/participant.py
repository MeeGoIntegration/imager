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
import json
from multiprocessing import Process, Queue, Pool
from imgsettings import *
import os, sys
from tempfile import TemporaryFile, NamedTemporaryFile, mkdtemp

num_workers = 2
job_pool = Pool(num_workers)

    
class MICParticipant(Participant):
    def mic2(self, id, type, email, kickstart):
        print id
        print type
        print email
        print kickstart
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
        worker = ImageWorker(id, tmpname, type, logfile, dir)    
        worker.build()
        logfile.close()

    def consume(self):
        wi = self.workitem
        email = wi.lookup('email')
        kickstart = wi.lookup('kickstart')
        id = wi.lookup('id')
        print "Workitem: "
        print json.dumps(wi.to_h())
        args = (id, 'raw', email, kickstart)
        self.mic2(id, 'raw', email, kickstart)
        #job_pool.apply_async(self.mic2, args)
        

if __name__ == "__main__":
    print "Started a python participant"
    p = MICParticipant(ruote_queue="mic", amqp_vhost="ruote-test")
    p.register("mic", {'queue':'mic'})
    p.run()
    
        
