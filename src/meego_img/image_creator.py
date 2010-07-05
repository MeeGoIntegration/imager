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

import json
import subprocess as sub
from subprocess import CalledProcessError
import os
from tempfile import TemporaryFile, NamedTemporaryFile, mkdtemp
import shutil
import re
import time
from threading import Thread
#from multiprocessing import Process, Queue, Pool
from amqplib import client_0_8 as amqp
from worker import ImageWorker
# SETTINGS
from imgsettings import *
# END SETTINGS

conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
chan = conn.channel()

chan.queue_declare(queue="image_queue", durable=True, exclusive=False, auto_delete=False)
chan.queue_declare(queue="kickstarter_queue", durable=True, exclusive=False, auto_delete=False)
chan.queue_declare(queue="status_queue", durable=False, exclusive=False, auto_delete=False)

chan.exchange_declare(exchange="image_exchange", type="direct", durable=True, auto_delete=False,)
chan.exchange_declare(exchange="django_result_exchange", type="direct", durable=True, auto_delete=False,)

chan.queue_bind(queue="image_queue", exchange="image_exchange", routing_key="img")
chan.queue_bind(queue="kickstarter_queue", exchange="image_exchange", routing_key="ks")
chan.queue_bind(queue="status_queue", exchange="django_result_exchange", routing_key="status")

def mic2(id, type, email, ksfile):
    dir = "%s/%s"%(base_dir, id)
    os.mkdir(dir, 0775)    
    tmp = NamedTemporaryFile(dir=dir, delete=False)    
    tmpname = tmp.name
    logfile_name = tmp.name+"-log"
    tmp.write(ksfile)    
    tmp.close()    
    logfile = open(logfile_name,'w')
    data = json.dumps({"status":"BUILDING", "id":str(id)})
    statusmsg = amqp.Message(data)
    chan.basic_publish(statusmsg, exchange="django_result_exchange", routing_key="status")  
    print "worker"
    worker = ImageWorker(id, tmpname, type, logfile, dir)
    worker.build()
    logfile.close()
    file = base_url+"%s"%id
    data = json.dumps({"status":"IN WORKER","url":str(file), "id":str(id)})
    imagemsg = amqp.Message(data)
    chan.basic_publish(imagemsg, exchange="django_result_exchange", routing_key="status")
    
#job_pool = Pool(num_workers)
def mic2_callback(msg):  
    print "mic2"
    job = json.loads(msg.body)    
    email = job["email"]
    id = job["id"]    
    type = job['imagetype']
    ksfile = job['ksfile']    
    mic2(id, type, email, ksfile)
    print "mic2 end"
    #job_pool.apply_async(mic2, args=args)        
    
    #chan.basic_ack(msg.delivery_tag)
    
        
 
def kickstarter_callback(msg):
    print "ks"
    kickstarter = json.loads(msg.body)    
    config = kickstarter["config"]
    email = kickstarter["email"]    
    id = kickstarter['id']
    imagetype = kickstarter['imagetype']
    configtemp = NamedTemporaryFile(delete=False)
    configtemp.write(config)  
    configtemp.close()    
    out_dir = mkdtemp()
    try:
        sub.check_call(['/usr/bin/python','/usr/share/img/kickstarter/kickstarter.py', '-c', configtemp.name, '-r', '/usr/share/img/kickstarter/repos.yaml', '-o', out_dir], stdout=sub.PIPE, stderr=sub.PIPE)                
        kickstart_file = open(out_dir+'/'+os.listdir(out_dir)[0])
        ksfile = kickstart_file.read()        
        data = json.dumps({'email':email, 'id':id, 'imagetype':imagetype, 'ksfile':ksfile})
        msg2 = amqp.Message(data)        
        chan.basic_publish(msg2, exchange="image_exchange", routing_key="img")        
    except CalledProcessError as err:       
        print err
        print err.returncode
    
    shutil.rmtree(out_dir) 
    os.remove(configtemp.name)
    configtemp.close()    
    print "ks end"
    
chan.basic_consume(queue='image_queue', no_ack=True, callback=mic2_callback)
chan.basic_consume(queue='kickstarter_queue', no_ack=True, callback=kickstarter_callback)
while True:
    chan.wait()
chan.basic_cancel("img")
chan.basic_cancel("ks")
chan.close()
conn.close()
