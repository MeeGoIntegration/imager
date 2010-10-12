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
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator, InvalidPage, EmptyPage
import img_web.settings as settings
from img_web.app.forms import *
from img_web.app.models import ImageJob
from uuid import *
from amqplib import client_0_8 as amqp
from tempfile import TemporaryFile, NamedTemporaryFile, mkdtemp
from django.core.servers.basehttp import FileWrapper
import ConfigParser

config = ConfigParser.ConfigParser()
config.read(settings.IMGCONF)

amqp_host = config.get('amqp', 'amqp_host')
amqp_user = config.get('amqp', 'amqp_user')
amqp_pwd = config.get('amqp', 'amqp_pwd')
amqp_vhost = config.get('amqp', 'amqp_vhost')

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

@login_required
def submit(request):    
    if request.method == 'POST':        
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            print request.POST
            email = request.POST['email']
            imagetype = request.POST['imagetype']
            arch = request.POST['architecture']
            release = request.POST['release']
            conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
            chan = conn.channel() 
            if  request.POST['template'] != 'None':
                overlay = request.POST['overlay']
                projects = request.POST['projects']
                template = request.POST['template']                
                conf = {} 
                conf["Template"] =  open(str(settings.TEMPLATESDIR) + template).read()

                if overlay == None:
                    overlay = ''
                if projects == None:
                    projects = ''

                packages = overlay.split(',')
                prjs = projects.split(',')

                for pkg in packages:
                    if pkg: 
                        if pkg[0] != '@':
                            conf["Packages"].append(pkg)
                        else:
                            conf["Groups"].append(pkg)
                for prj in prjs:
                    if prj: 
                        conf["Projects"].append(prj)

                uuid = str(uuid1())        
                params = {'email':email, 'imagetype':imagetype, 'id':uuid, 'name':template, 'release':release, 'config':conf}
                data = json.dumps(params)
                msg = amqp.Message(data, message_id=uuid)    
                imgjob = ImageJob()
                imgjob.task_id = msg.message_id
                imgjob.email = email
                imgjob.type = imagetype
                imgjob.save()
                #chan.queue_purge("result_queue")
                if settings.COMM_METHOD == "amqp":
                    chan.basic_publish(msg,exchange="image_exchange",routing_key="ks")
                if settings.COMM_METHOD == "boss":
                    l = Launcher()
                    l.launch()
            elif 'ksfile' in request.FILES and request.POST['overlay'] == '': 
                ksfile = request.FILES['ksfile']
                id = str(uuid1())
                data = json.dumps({'email':email, 'id':id, 'imagetype':imagetype, 'ksfile':ksfile.read(), 'release':release, 'name': ksfile.name, 'arch':arch})
                msg = amqp.Message(data, message_id=id) 
                imgjob = ImageJob()                
                imgjob.task_id = msg.message_id
                imgjob.email = email
                imgjob.type = imagetype
                imgjob.status = "IN QUEUE"
                imgjob.save()
                if settings.COMM_METHOD == "amqp":
                    chan.basic_publish(msg, exchange="image_exchange", routing_key="img")
                if settings.COMM_METHOD == "boss":
                    l = Launcher()
                    l.launch()
                
            else:
                form = UploadFileForm()
                return render_to_response('app/upload.html', {'form': form, 'formerror':"Can't specify an overlay and a kickstart file!"})
            chan.close()
            conn.close()
            return HttpResponseRedirect(reverse('img-app-queue')) # Redirect after POST
    else:
        form = UploadFileForm()
        

    return render_to_response('app/upload.html', {'form': form},context_instance=RequestContext(request))

def get_or_none(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None

@login_required
def queue(request):
    conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
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
    q = ImageJob.objects.all().order_by('created').reverse()
    p = Paginator(q, 10)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        queue = p.page(page)
    except (EmptyPage, InvalidPage):
        queue = p.page(p.num_pages)
    return render_to_response('app/queue.html', {'queue':queue, 'error':error}, context_instance=RequestContext(request))
    
@permission_required('app.delete_imagejob')
def clear(request):
    for job in ImageJob.objects.all():
        job.delete()
    return HttpResponseRedirect(reverse('img-app-queue'))
    
@login_required
def download(request, msgid):
    return HttpResponseRedirect(settings.IMGURL + "/" + msgid)
    
@login_required
def job(request, msgid): 
    conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
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
                print data['log']
                chan.basic_ack(msg.delivery_tag)
    if imgjob.logfile:
        print imgjob.logfile
        if imgjob.logfile.startswith('http'):
            res = urllib2.urlopen(imgjob.logfile).read()    
        elif imgjob.logfile.startswith('/'):
            res = open(os.path.dirname(settings.IMGDIR) + imgjob.logfile).read()    
    chan.close()
    conn.close()
    return render_to_response('app/job_details.html', {'job':res}, context_instance=RequestContext(request))

def index(request):
    return render_to_response('index.html', context_instance=RequestContext(request))
