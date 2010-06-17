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
from multiprocessing import Process, Queue
from amqplib import client_0_8 as amqp

# SETTINGS

base_url = "http://localhost/images/"
base_dir = "/var/www/images"
amqp_host = "localhost:5672"
amqp_user = "img"
amqp_pwd = "imgpwd"
amqp_vhost = "imgvhost"

# END SETTINGS

conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
chan = conn.channel()

chan.queue_declare(queue="image_queue", durable=True, exclusive=False, auto_delete=False)
chan.queue_declare(queue="link_queue", durable=False, exclusive=False, auto_delete=False)
chan.queue_declare(queue="result_queue", durable=False, exclusive=False, auto_delete=False)
chan.queue_declare(queue="kickstarter_queue", durable=True, exclusive=False, auto_delete=False)
chan.queue_declare(queue="error_queue", durable=False, exclusive=False, auto_delete=False)
chan.queue_declare(queue="status_queue", durable=False, exclusive=False, auto_delete=False)

chan.exchange_declare(exchange="image_exchange", type="direct", durable=True, auto_delete=False,)
chan.exchange_declare(exchange="django_result_exchange", type="direct", durable=True, auto_delete=False,)

chan.queue_bind(queue="image_queue", exchange="image_exchange", routing_key="img")
chan.queue_bind(queue="kickstarter_queue", exchange="image_exchange", routing_key="ks")
chan.queue_bind(queue="link_queue", exchange="django_result_exchange", routing_key="link")
chan.queue_bind(queue="result_queue", exchange="django_result_exchange", routing_key="res")
chan.queue_bind(queue="error_queue", exchange="django_result_exchange", routing_key="err")
chan.queue_bind(queue="status_queue", exchange="django_result_exchange", routing_key="status")

def mic2(id, type, email, ksfile):
    print "MIC2 function"    
    dir = "%s/%s"%(base_dir, id)
    print dir
    os.mkdir(dir, 0775)    
    tmp = NamedTemporaryFile(dir=dir, delete=False)
    print tmp.name
    tmpname = tmp.name
    logfile_name = tmp.name+"-log"
    tmp.write(ksfile)    
    tmp.close()
    data2 = json.dumps({'logfile':logfile_name, 'id':id})
    ret = amqp.Message(data2)
    chan.basic_publish(ret, exchange="django_result_exchange", routing_key="res")
    try:
        logfile = open(logfile_name,'w')
        data = json.dumps({"status":"BUILDING", "id":str(id)})
        statusmsg = amqp.Message(data)
        chan.basic_publish(statusmsg, exchange="django_result_exchange", routing_key="status")        
        sub.check_call(['/usr/bin/sudo','/usr/bin/mic-image-creator', '-d', '-v','--config='+tmpname,'--format='+(type if type else 'raw'),'--cache=/tmp/mycache/', '--outdir='+dir], shell=False, stdout=logfile, stderr=logfile, bufsize=-1)        
        logfile.close()
    except CalledProcessError as err:
        logfile = open(logfile_name,'a')
        logfile.write("IMG FAILED MISERABLY IN CREATING THE IMAGE!\n")
        logfile.write("%s\n"%err)        
        logfile.close()
        print err
        error = json.dumps({"error":"Command failed %s"%err, 'id':str(id), 'imagefile':base_url+id})
        errmsg = amqp.Message(error)
        chan.basic_publish(errmsg, exchange="django_result_exchange", routing_key="err")
        return       
    file = base_url+"%s"%id
    print str(file)
    print str(id)
    data = json.dumps({"imagefile":str(file), "id":str(id)})
    imagemsg = amqp.Message(data)
    chan.basic_publish(imagemsg, exchange="django_result_exchange", routing_key="link")
    chan.close()
    conn.close()
        
def mic2_callback(msg):  
    print "AT MIC2 CALLBACK"       
    job = json.loads(msg.body)
    print job
    email = job["email"]
    id = job["id"]    
    type = job['imagetype']
    ksfile = job['ksfile']
    Process(target=mic2, args=(id, type, email, ksfile)).start()
    #chan.basic_ack(msg.delivery_tag)
    
        
 
def kickstarter_callback(msg):
    kickstarter = json.loads(msg.body)    
    print kickstarter
    config = kickstarter["config"]
    email = kickstarter["email"]    
    id = kickstarter['id']
    configtemp = NamedTemporaryFile(delete=False)
    configtemp.write(config)  
    configtemp.close()    
    out_dir = mkdtemp()
    try:
        sub.check_call(['/usr/bin/python','/usr/share/img/kickstarter/kickstarter.py', '-c', configtemp.name, '-r', '/usr/share/img/kickstarter/repos.yaml', '-o', out_dir], stdout=sub.PIPE, stderr=sub.PIPE)                
        kickstart_file = open(out_dir+'/'+os.listdir(out_dir)[0])
        ksfile = kickstart_file.read()        
        data = json.dumps({'email':email, 'id':id, 'imagetype':kickstarter['imagetype'], 'ksfile':ksfile})
        msg2 = amqp.Message(data)        
        chan.basic_publish(msg2, exchange="image_exchange", routing_key="img")        
    except CalledProcessError as err:       
        print err
        print err.returncode
    
    shutil.rmtree(out_dir) 
    os.remove(configtemp.name)
    configtemp.close()    
    
chan.basic_consume(queue='image_queue', no_ack=True, callback=mic2_callback)
chan.basic_consume(queue='kickstarter_queue', no_ack=True, callback=kickstarter_callback)
while True:
    chan.wait()
chan.basic_cancel("img")
chan.basic_cancel("ks")
chan.close()
conn.close()
