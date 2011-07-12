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

import os, time
from urllib2 import urlopen, HTTPError
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage, EmptyPage

import img_web.settings as settings
from img_web.app.forms import UploadFileForm, extraReposFormset
from img_web.app.models import ImageJob, Queue, GETLOG
from django.db import transaction

@login_required
@transaction.autocommit
def submit(request):    
    
    if request.method == 'GET':
        form = UploadFileForm(initial = {'devicegroup':settings.DEVICEGROUP,
                               'email':request.user.email}
                               )
        formset = extraReposFormset()
        return render_to_response('app/upload.html',
                                  {'form' : form, 'formset' : formset},
                                  context_instance=RequestContext(request)
                                  )

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        formset = extraReposFormset(request.POST)
        if not form.is_valid() or not formset.is_valid():
            return render_to_response('app/upload.html',
                                      {'form': form, 'formset' : formset},
                                       context_instance=RequestContext(request)
                                       )
        data = form.cleaned_data 
        data2 = formset.cleaned_data
        imgjob = ImageJob()

        imgjob.image_id = "%s-%s" % ( request.user.id, 
                                      time.strftime('%Y%m%d-%H%M%S') )
        imgjob.email = data['email']
        imgjob.image_type = data['imagetype']
        imgjob.user = request.user

        imgjob.overlay = data['overlay']
        imgjob.release = data['release']
        imgjob.arch = data['architecture']

        if "test_image" in data.keys():
            imgjob.devicegroup = data['devicegroup']  
            imgjob.test_image = data['test_image']

        if "notify" in data.keys():
            imgjob.notify = data["notify"]

        conf = []
        for prj in data2:
            if prj['obs']:
                repo = prj['obs'] + prj['repo'].replace(':',':/')
                conf.append(repo)

        imgjob.extra_repos = ",".join(conf)

        ksname = ""
        if 'template' in data and data['template']:
            ksname = data['template']
            filename = os.path.join(settings.TEMPLATESDIR, ksname)
            with open(filename, mode='r') as ffd:
                imgjob.kickstart = ffd.read()

        elif 'ksfile' in data and data['ksfile']:
            ksname = data['ksfile'].name
            imgjob.kickstart =  data['ksfile'].read()

        if ksname.endswith('.ks'):
            ksname = ksname[0:-3]

        imgjob.name = ksname

        imgjob.queue = Queue.objects.get(name="web")

        imgjob.save()
        
        return HttpResponseRedirect(reverse('img-app-queue'))


@login_required
def queue(request, queue_name=None, dofilter=False):
    imgjobs = ImageJob.objects.all().order_by('created').reverse()
    if dofilter:
        imgjobs = imgjobs.filter(user = request.user)
    if queue_name:
        imgjobs = imgjobs.filter(queue__name = queue_name)

    paginator = Paginator(imgjobs, 30)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        queue_page = paginator.page(page)
    except (EmptyPage, InvalidPage):
        queue_page = paginator.page(paginator.num_pages)
    return render_to_response('app/queue.html',
                              {'queue' : queue_page,
                               'queues': Queue.objects.all(),
                               'queue_name' : queue_name,
                               'filtered' : dofilter,
                               },
                              context_instance=RequestContext(request))
    
@login_required
def job(request, msgid): 
    imgjob = ImageJob.objects.get(image_id__exact=msgid)
    error = "" 
    if imgjob.status == "IN QUEUE":
        error = "Job still in queue"
    elif imgjob.error and imgjob.error != "":
        error = imgjob.error
    else:
        # signal to launch getlog process
        GETLOG.send(sender=request, image_id = imgjob.image_id)

        return render_to_response('app/job_details.html', {'job':imgjob.log},
                                  context_instance=RequestContext(request))

    return render_to_response('app/job_details.html',
                              {'errors': {'Error' : [error]},
                               'job':imgjob.log}, 
                                context_instance=RequestContext(request)) 

def index(request):
    return render_to_response('index.html',
                              context_instance=RequestContext(request))
