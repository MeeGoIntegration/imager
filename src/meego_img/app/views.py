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

# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound,  Http404
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from meego_img.app.forms import *
from meego_img.app.models import ImageJob
from uuid import *
from amqplib import client_0_8 as amqp
from tempfile import TemporaryFile, NamedTemporaryFile, mkdtemp
from django.core.servers.basehttp import FileWrapper
from settings import *
import urllib2
import os
import sys
try:
     import simplejson as json
except ImportError:
     import json
import yaml
import Queue

queue = Queue.Queue()

def submit(request):    
    defconfig = file('/usr/share/img/kickstarter/configurations.yaml', 'r')
    config = yaml.load(defconfig) 
    if request.method == 'POST':        
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            print request.POST
            email = request.POST['email']
            imagetype = request.POST['imagetype']
            conn = amqp.Connection(host=BROKER_HOST, userid=BROKER_USER, password=BROKER_PASSWORD, virtual_host=BROKER_VHOST, insist=False)
            chan = conn.channel() 
            if 'overlay' in request.POST and not 'ksfile' in request.FILES:
                overlay = request.POST['overlay']
                platform = request.POST['platform']                
                if overlay == None:
                    overlay = ''
                splits = overlay.split(',')
                           
                for pkg in splits:
                    if pkg: 
                        if pkg[0] != '@':
                            config[platform]["ExtraPackages"].append(pkg)
                        else:
                            config[platform]["Groups"].append(pkg)
                config_raw = yaml.dump(config)
                print config_raw
                uuid = str(uuid1())        
                                  
                params = {'config':config_raw, 'email':email, 'imagetype':imagetype, 'id':uuid}
                data = json.dumps(params)
                msg = amqp.Message(data, message_id=uuid)    
                imgjob = ImageJob()
                imgjob.task_id = msg.message_id
                imgjob.email = email
                imgjob.type = imagetype
                imgjob.save()
                #chan.queue_purge("result_queue")
                chan.basic_publish(msg,exchange="image_exchange",routing_key="ks")
            elif 'ksfile' in request.FILES and request.POST['overlay'] == '':                
                ksfile = request.FILES['ksfile']                                
                id = str(uuid1())
                data = json.dumps({'email':email, 'id':id, 'imagetype':imagetype, 'ksfile':ksfile.read()})
                              
                imgjob = ImageJob()                
                imgjob.task_id = msg.message_id
                imgjob.email = email
                imgjob.type = imagetype
                imgjob.status = "IN BOSS (receive not yet implemented)"
                imgjob.save()                
                # Specify a process definition
                pdef = {
                    "definition": """
                        Ruote.process_definition :name => 'test' do
                          sequence do
                            mic
                            workitem_dumper
                          end
                        end
                      """,
                    "fields" : {
                        "kickstart" : data['ksfile'], 
                        "email": data['email'], 
                        "id": data['id'], 
                        "type": data['imagetype']
                        }
                    }
                    # Encode the message as json
                msg = amqp.Message(json.dumps(pdef))
                # delivery_mode=2 is persistent
                msg.properties["delivery_mode"] = 2 
                
                # Publish the message.
                
                # Notice that this is sent to the anonymous/'' exchange (which is
                # different to 'amq.direct') with a routing_key for the queue
                bossconn = amqp.Connection(host="amqpvm", userid="ruote",
                       password="ruote", virtual_host="ruote-test", insist=False)
                bosschan = bossconn.channel() 
                bosschan.basic_publish(msg, exchange='', routing_key='ruote_workitems')  
                bosschan.close()
                bossconn.close()
            else:
                form = UploadFileForm()
                return render_to_response('app/upload.html', {'form': form, 'formerror':"Can't specify an overlay and a kickstart file!"})
            chan.close()
            conn.close()
            return HttpResponseRedirect(reverse('img-app-queue')) # Redirect after POST
    else:
        form = UploadFileForm()
        

    return render_to_response('app/upload.html', {'form': form})

def get_or_none(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None

def queue(request):
    conn = amqp.Connection(host=BROKER_HOST, userid=BROKER_USER, password=BROKER_PASSWORD, virtual_host=BROKER_VHOST, insist=False)
    chan = conn.channel()
    msg = chan.basic_get("status_queue")
    file = ""
    id = ""
    error = ""
    if msg:
        data = json.loads(msg.body)
        print data
        job = get_or_none(ImageJob, task_id__exact=data['id'])
        if job:
            print "Matched %s job with %s"%(job.task_id, data['id'])
            if "status" in data:
                job.status = data['status']
            if "url" in data:
                job.imagefile = data['url']
            if "error" in data:
                job.error = data['error']
            if "log" in data:
                job.logfile = data['log']
            job.save()
            chan.basic_ack(msg.delivery_tag)
    chan.close()
    conn.close()
    return render_to_response('app/queue.html', {'queue':ImageJob.objects.all(), 'error':error})
    
def clear(request):
    for job in ImageJob.objects.all():
        job.delete()
    return HttpResponseRedirect(reverse('img-app-queue'))
    
def download(request, msgid):
    imgjob = ImageJob.objects.get(task_id__exact=msgid)    
    response = HttpResponseRedirect(imgjob.imagefile)
    return response
    
def job(request, msgid): 
    conn = amqp.Connection(host=BROKER_HOST, userid=BROKER_USER, password=BROKER_PASSWORD, virtual_host=BROKER_VHOST, insist=False)
    chan = conn.channel()  
    imgjob = ImageJob.objects.get(task_id__exact=msgid)
    msg = chan.basic_get("status_queue")
    res = ''
    if msg:
        data = json.loads(msg.body)
        print data        
        if (imgjob.task_id==data['id']):
            if 'log' in data:
                print "matched: %s to %s with %s file" %(imgjob.task_id, data['id'], data['log'])
                imgjob.logfile = data['log']
                imgjob.save() 
                chan.basic_ack(msg.delivery_tag)
    if imgjob.logfile:
        res = urllib2.urlopen(imgjob.logfile).read()    
    chan.close()
    conn.close()
    return render_to_response('app/job_details.html', {'job':res})

def index(request):
    return render_to_response('index.html')
