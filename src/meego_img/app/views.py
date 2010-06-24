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


import os
import sys
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
            conn = amqp.Connection(host="localhost:5672", userid="img", password="imgpwd", virtual_host="imgvhost", insist=False)
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
                imgjob.status = "IN QUEUE"
                imgjob.type = imagetype
                imgjob.save()
                #chan.queue_purge("result_queue")
                chan.basic_publish(msg,exchange="image_exchange",routing_key="ks")
            elif 'ksfile' in request.FILES and request.POST['overlay'] == '':
                ksfile = request.FILES['ksfile']                                
                id = str(uuid1())
                data = json.dumps({'email':email, 'id':id, 'imagetype':imagetype, 'ksfile':ksfile.read()})
                msg = amqp.Message(data, message_id=id)                 
                imgjob = ImageJob()                
                imgjob.task_id = msg.message_id
                imgjob.email = email
                imgjob.status = "IN QUEUE"
                imgjob.type = imagetype
                imgjob.save()                
                chan.basic_publish(msg, exchange="image_exchange", routing_key="img")
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
    conn = amqp.Connection(host="localhost:5672", userid="img", password="imgpwd", virtual_host="imgvhost", insist=False)
    chan = conn.channel()
    msg = chan.basic_get("link_queue")
    file = ""
    id = ""
    error = ""
    if msg:
        data = json.loads(msg.body)
        print data
        if "url" in data:
            file = data["url"]
            id = data["id"]
            job = get_or_none(ImageJob, task_id=id)
            if job:
                job.imagefile = file
                job.status = "DONE"
                job.save()
            chan.basic_ack(msg.delivery_tag)
    statusmsg = chan.basic_get("status_queue")
    if statusmsg:
        data = json.loads(statusmsg.body)
        print data
        if "status" in data:
                status = data["status"]
                id = data['id']
                job = get_or_none(ImageJob, task_id=id)
                if job:
                    job.status = status
                    job.save()
                chan.basic_ack(statusmsg.delivery_tag)
    errmsg = chan.basic_get("error_queue")
    if errmsg:
        errdata = json.loads(errmsg.body)
        print errdata
        if "error" and "id" in errdata:
            error = errdata["error"]
            id = errdata["id"]
            job = get_or_none(ImageJob, task_id=id)
            if job:
                job.error = error
                job.status = "ERROR"
                job.save()
            chan.basic_ack(errmsg.delivery_tag)
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
    conn = amqp.Connection(host="localhost:5672", userid="img", password="imgpwd", virtual_host="imgvhost", insist=False)
    chan = conn.channel()  
    imgjob = ImageJob.objects.get(task_id__exact=msgid)
    msg = chan.basic_get("result_queue")
    if msg:
        data = json.loads(msg.body)
        print data        
        if (imgjob.task_id==data['id']):
            print "matched: %s to %s with %s file" %(imgjob.task_id, data['id'], data['logfile'])
            imgjob.logfile = data['logfile']
            imgjob.save() 
            chan.basic_ack(msg.delivery_tag)
            
    if os.path.exists(imgjob.logfile):
        file = open(imgjob.logfile, 'r')
        res = file.read()
        file.close()
    else:
        res = "No log open yet, please refresh this page"        
    chan.close()
    conn.close()
    return render_to_response('app/job_details.html', {'job':res})

def index(request):
    return render_to_response('index.html')
