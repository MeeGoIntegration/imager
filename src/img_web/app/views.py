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

""" imager views """

from django.http import ( HttpResponse, HttpResponseRedirect,
                        HttpResponseNotFound, Http404 )
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator, InvalidPage, EmptyPage
import django.views.generic.simple
import img_web.settings as settings
from img_web.app.forms import *
from img_web.app.models import ImageJob
import time
from amqplib import client_0_8 as amqp
from tempfile import TemporaryFile, NamedTemporaryFile, mkdtemp
from django.core.servers.basehttp import FileWrapper
from img_web.utils.a2html import plaintext2html 
import ConfigParser
import sys, os

config = ConfigParser.ConfigParser()
config.read(settings.IMGCONF)

amqp_host = config.get('amqp', 'amqp_host')
amqp_user = config.get('amqp', 'amqp_user')
amqp_pwd = config.get('amqp', 'amqp_pwd')
amqp_vhost = config.get('amqp', 'amqp_vhost')

if settings.USE_BOSS:
  from RuoteAMQP.launcher import Launcher
  boss_host = config.get('boss', 'amqp_host')
  boss_user = config.get('boss', 'amqp_user')
  boss_pwd = config.get('boss', 'amqp_pwd')
  boss_vhost = config.get('boss', 'amqp_vhost')
  notify_process = """Ruote.process_definition :name => 'notification' do
              sequence do
                notify :template => '%s', :subject => 'Image creation request', :debug_dump => 'True'
              end
            end"""

  test_image = """Ruote.process_definition :name => 'testing' do
              sequence do
                set 'status' => 'SUCCESS'
                test_image
              end
            end"""

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
        formset = extraReposFormset(request.POST)
        if form.is_valid() and formset.is_valid():
            if 'ksfile' in request.FILES and request.POST['template'] != 'None':
                return render_to_response('app/upload.html', {'form': form, 'formset' : formset, 'formerror': {"Error" : ["Please choose a template or upload a kickstart, not both!"]} }, context_instance=RequestContext(request))
            if 'ksfile' not in request.FILES and request.POST['template'] == 'None': 
                return render_to_response('app/upload.html', {'form': form, 'formset' : formset, 'formerror': {"Error" : ["Please choose either a template or upload a kickstart file."]} }, context_instance=RequestContext(request))

            data = form.cleaned_data 
            data2 = formset.cleaned_data

            conf = {'Template' : '', 'Projects' : [], 'Groups' : [], 'Packages' : []} 
            for prj in data2:
                if prj['obs'] == 'None':
                    continue
                if prj['obs'] != 'None' and prj['repo'] == '':
                    return render_to_response('app/upload.html', {'form': form, 'formset' : formset, 'formerror': {"Error" : ["You choose an extra OBS without adding a corresponding repository."]} }, context_instance=RequestContext(request))
                
                repo = prj['obs'] + prj['repo'].replace(':',':/')
                conf["Projects"].append(repo)

            if data['template'] != 'None':
                template = data['template']
                conf["Template"] =  open(str(settings.TEMPLATESDIR) + template).read()
                if template.endswith('.ks'):
                    template = template[0:-3]
            elif 'ksfile' in request.FILES:
                conf["Template"] =  data['ksfile'].read()
                template = data['ksfile'].name
                if template.endswith('.ks'):
                    template = template[0:-3]

            overlay = data['overlay']
            if overlay == None:
                overlay = ''

            packages = overlay.split(',')
            for pkg in packages:
                if pkg: 
                    if pkg.startswith('@'):
                        conf["Groups"].append(pkg)
                    else:
                        conf["Packages"].append(pkg)

            email = data['email']
            username = request.user.username
            imagetype = data['imagetype']
            arch = data['architecture']
            release = data['release']
            uuid = time.strftime('%Y%m%d-%H%M%S') 

            params = {'email':email, 'username':username, 'imagetype':imagetype, 'id':uuid, 'name':template, 'release':release, 'arch':arch, 'config':conf}
            sys.stdout.flush()
            msgdata = json.dumps(params)
            msg = amqp.Message(msgdata, message_id=uuid)
            conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
            chan = conn.channel() 
            chan.basic_publish(msg,exchange="image_exchange",routing_key="ks")
            chan.close()
            conn.close()
            imgjob = ImageJob()
            imgjob.task_id = uuid 
            imgjob.email = email
            imgjob.type = imagetype
            imgjob.user = request.user
            imgjob.status = "IN QUEUE"
            if settings.USE_BOSS:
                imgjob.notify = data['notify'] if 'notify' in data else False 
                imgjob.devicegroup = data['devicegroup'] if 'devicegroup' in data else False 
                imgjob.test_image = data['test_image'] if 'test_image' in data else False
            imgjob.save()
            return HttpResponseRedirect(reverse('img-app-queue')) # Redirect after POST
        else:
            form.errors['Error'] = ["Invalid data, please try again."]
            return render_to_response('app/upload.html', {'form': form, 'formset' : formset, 'formerror': form.errors}, context_instance=RequestContext(request))
            
    else:
        if settings.USE_BOSS:
            form = UploadFileForm({'devicegroup':settings.DEVICEGROUP, 'email':request.user.email})
        else:
            form = UploadFileForm({'email':request.user.email})
        formset = extraReposFormset()
    return render_to_response('app/upload.html', {'form' : form, 'formset' : formset}, context_instance=RequestContext(request))

def get_or_none(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None


def update_status():
    #get 5 messages at a time if any
    msg = None
    for round in range(1,5):
      conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
      chan = conn.channel()
      msg = chan.basic_get("status_queue")
      if msg:
          chan.basic_ack(msg.delivery_tag)
      chan.close()
      conn.close()
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
              if settings.USE_BOSS:
                  if job.status == "DONE":
                      print "Done"
                      if job.notify:
                        print "going to notify"
                        l = Launcher(amqp_host=boss_host,  amqp_user=boss_user, amqp_pass=boss_pwd, amqp_vhost=boss_vhost)
                        l.launch(notify_process % ("image_created"), { 'email' : [job.email], 'status' : job.status, 'url' : data['url'], 'image' :data['image'], 'name' : data['name'], 'arch' : data["arch"], 'status' : 'SUCCESS'})
                      if job.test_image:
                        l = Launcher(amqp_host=boss_host,  amqp_user=boss_user, amqp_pass=boss_pwd, amqp_vhost=boss_vhost)
                        l.launch(test_image, { 'email' : [job.email], 'image' :data['image'], 'id' : data['id'], 'product' : 'ilmatar', 'devicegroup' : job.devicegroup })
                  if job.status == "ERROR":
                      if job.notify or job.test_image:
                        print "Error"
                        print notify_process % ("image_failed")
                        l = Launcher(amqp_host=boss_host,  amqp_user=boss_user, amqp_pass=boss_pwd, amqp_vhost=boss_vhost)
                        print "connected"
                        l.launch(notify_process % ("image_failed"), { 'email' : [job.email], 'status' : job.status, 'url' : data['url'], 'name' : data['name'],  'arch' : data["arch"], 'status' : 'FAILED'})
                        print "Launched"



def update(request):
    update_status()
    return HttpResponse("") 

@login_required
def queue(request, filter=False):
    update_status()
    if filter:
        q = ImageJob.objects.filter(email=request.user.email).order_by('created').reverse()
    else:
        q = ImageJob.objects.all().order_by('created').reverse()
    p = Paginator(q, 30)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        queue = p.page(page)
    except (EmptyPage, InvalidPage):
        queue = p.page(p.num_pages)
    return render_to_response('app/queue.html', {'queue':queue}, context_instance=RequestContext(request))
    
@permission_required('app.delete_imagejob')
def clear(request):
    for job in ImageJob.objects.all():
        job.delete()
    return HttpResponseRedirect(reverse('img-app-queue'))
    
@login_required
def download(request, msgid):
    d = msgid
    job = ImageJob.objects.get(task_id__exact=d)
    if job.user:
      d = os.path.join(job.user.username , d)
    return HttpResponseRedirect(settings.REPOURL + "/" + settings.IMGURL + "/" + d)
    
@login_required
def remove(request): 
    if request.method == 'POST':
      for key in request.POST.keys():
        if key.startswith("job-"):
          obj_id = request.POST[key]
          try:
            imgjob = ImageJob.objects.get(task_id__exact=obj_id)
            if not request.user.is_superuser and request.user.email != imgjob.email :
              return render_to_response('app/remove.html', {'errors': {'Error' : ['You are not authorized to delete this job!']}}, context_instance=RequestContext(request)) 
          except:
            return render_to_response('app/remove.html', {'errors': {'Error' : ['No job with this id was found!']}}, context_instance=RequestContext(request)) 
          try:
            imgjob.delete()
          except Exception, e :
            return render_to_response('app/remove.html', {'errors': {'Error' : ['There was an error removing this job! %s' % e]}}, context_instance=RequestContext(request)) 
            

    return HttpResponseRedirect(reverse('img-app-queue'))

@login_required
def confirm_remove(request, msgid): 
    try:
      job = ImageJob.objects.get(task_id__exact=msgid)
    except:
      return render_to_response('app/remove.html', {'errors': {'Error' : ['No job with this id was found!']}}, context_instance=RequestContext(request)) 
    if not request.user.is_superuser and request.user.email != job.email :
      return render_to_response('app/remove.html', {'errors': {'Error' : ['You are not authorized to delete this job!']}}, context_instance=RequestContext(request)) 
    try:
      d = job.task_id
      if job.user:
        d = os.path.join(job.user.username, job.task_id)
      topdir = os.path.join(settings.IMGDIR, d) + os.sep
      if os.path.exists(topdir):
        walker = os.walk(topdir)
        file_list=[]
        for dirpath, dirnames, filenames in walker:
          for filename in filenames:
            file_list.append(os.path.join(dirpath.replace(topdir,"") , filename))
        return render_to_response('app/remove.html', {'jobid' : job.task_id, 'file_list' : file_list}, context_instance=RequestContext(request))
    except:
      pass
    return render_to_response('app/remove.html', {'errors': {'Error' : ['The job directory is not accessible, please contact the administrator to remove this job.']}}, context_instance=RequestContext(request)) 

@login_required
def job(request, msgid): 
    imgjob = ImageJob.objects.get(task_id__exact=msgid)
    if imgjob.logfile:
        print imgjob.logfile
        try:
            if imgjob.logfile.startswith('http'):
                res = urllib2.urlopen(imgjob.logfile).read()    
            elif imgjob.logfile.startswith('/'):
                res = open(imgjob.logfile).read() 
            res = plaintext2html(res)
            return render_to_response('app/job_details.html', {'job':res}, context_instance=RequestContext(request))
        except IOError, e:
            pass
    elif imgjob.error and imgjob.error != "":
        return render_to_response('app/job_details.html', {'errors': {'Error' : [imgjob.error]}}, context_instance=RequestContext(request)) 
    return render_to_response('app/job_details.html', {'errors': {'Error' : ['No logfile has been created yet.']}}, context_instance=RequestContext(request)) 

def index(request):
    return render_to_response('index.html', context_instance=RequestContext(request))
