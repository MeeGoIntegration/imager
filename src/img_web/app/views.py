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

import os
import time
import re
from urllib2 import urlopen, HTTPError

from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.contrib import messages
from django.forms.formsets import formset_factory

import img_web.settings as settings
from img_web.app.forms import ImageJobForm, extraReposFormset, extraTokensFormset, TagForm, SearchForm, BasePostProcessFormset, PostProcessForm
from img_web.app.models import ImageJob, Queue, Token, PostProcess
from django.db import transaction, IntegrityError

@login_required
@transaction.autocommit
def submit(request):    
    """
    GET: returns an unbound ImageJobForm

    POST: process a user submitted UploadFileForm
    """
    postProcessFormset = formset_factory(PostProcessForm, formset=BasePostProcessFormset, extra=PostProcess.objects.filter(active=True).count())

    if request.method == 'GET':
        jobform = ImageJobForm(initial = {'devicegroup':settings.DEVICEGROUP,
                               'email':request.user.email}
                               )
        reposformset = extraReposFormset()
        tokensformset = extraTokensFormset()
        ppformset = postProcessFormset()
        return render_to_response('app/upload.html',

                                  {'jobform' : jobform, 'reposformset' : reposformset, 'tokensformset' : tokensformset,
                                   'ppformset' : ppformset}, context_instance=RequestContext(request)
                                  )

    if request.method == 'POST':
        jobform = ImageJobForm(request.POST, request.FILES)
        reposformset = extraReposFormset(request.POST)
        tokensformset = extraTokensFormset(request.POST)
        ppformset = postProcessFormset(request.POST)

        if not jobform.is_valid() or not reposformset.is_valid() or not ppformset.is_valid():
            return render_to_response('app/upload.html',
                                      {'jobform': jobform, 'reposformset' : reposformset, 'tokensformset' : tokensformset,
                                       'ppformset' : ppformset},
                                       context_instance=RequestContext(request)
                                       )
        jobdata = jobform.cleaned_data
        reposdata = reposformset.cleaned_data
        tokensdata = tokensformset.cleaned_data[0]

        imgjob = ImageJob()

        ks = ""
        ksname = ""
        ks_type = ""

        if 'template' in jobdata and jobdata['template']:
            ksname = jobdata['template']
            filename = os.path.join(settings.TEMPLATESDIR, ksname)
            with open(filename, mode='r') as ffd:
                ks = ffd.readlines()

        elif 'ksfile' in jobdata and jobdata['ksfile']:
            ksname = jobdata['ksfile'].name
            ks =  jobdata['ksfile'].readlines()

        imgjob.kickstart = "\n".join(ks)

        for line in ks:
            if re.match(r'^#.*?KickstartType:.+$', line):
                ks_type = line.split(":", 1)[1].strip()
                break

        if ksname.endswith('.ks'):
            ksname = ksname[0:-3]

        extra_repos = set()
        for repo in reposdata:
            if repo.get('obs', None):
                reponame = repo['repo']
                if not reponame.startswith('/'):
                    reponame = "/%s" % reponame
                repo_url = repo['obs'] + repo['project'].replace(':', ':/') + reponame
                extra_repos.add(repo_url)

        overlay = set([ x for x in jobdata['overlay'].split(',') if x.strip()])
        if 'features' in jobdata:
            for feat in jobdata['features']:
                print feat
                repos_type = 'repositories-%s' % ks_type
                if not ks_type or not repos_type in feat:
                    repos_type = 'repositories'

                extra_repos.update(feat.get(repos_type, set()))
                overlay.update(feat.get('pattern', ''))
                overlay.update(feat.get('packages', set()))

        tokenmap = {}
        for token in Token.objects.all():
            if token.name in tokensdata:
                tokenvalue = tokensdata[token.name]
            else:
                tokenvalue = token.default

            if token.name == "RNDFLAVOUR":
                rndpattern = ":/%s" % tokenvalue
                if tokenvalue == "devel":
                    rndpattern = ""
                tokenmap["RNDPATTERN"] = rndpattern

            if token.name == "RELEASE":
                if tokenvalue == "":
                    tokenmap["RELEASEPATTERN"] = ""
                else:
                    tokenmap["RELEASEPATTERN"] = ":/%s" % tokenvalue

            if " " in tokenvalue:
                tokenvalue = '"%s"' % tokenvalue

            tokenmap[token.name] = tokenvalue

        archtoken = jobdata['architecture']
        if archtoken == "i686":
            archtoken = "i586"
        tokenmap["ARCH"] = archtoken

        tokens_list = []
        extra_repos_tmp = []
        for token, tokenvalue in tokenmap.items(): 
            ksname = ksname.replace("@%s@" % token, tokenvalue)
            tokens_list.append("%s:%s" % (token, tokenvalue))
            for repo in extra_repos:
                extra_repos_tmp.append(repo.replace("@%s@" % token, tokenvalue))
            extra_repos = extra_repos_tmp[:]
            extra_repos_tmp = []
        
        imgjob.name = ksname
        imgjob.arch = jobdata['architecture']
        imgjob.tokenmap = ",".join(tokens_list)

        imgjob.image_id = "%s-%s" % ( request.user.id, 
                                      time.strftime('%Y%m%d-%H%M%S') )
        imgjob.email = jobdata['email']
        imgjob.image_type = jobdata['imagetype']
        imgjob.user = request.user

        if "test_image" in jobdata.keys():
            imgjob.devicegroup = jobdata['devicegroup']
            imgjob.test_image = jobdata['test_image']

        if "notify_image" in jobdata.keys():
            imgjob.notify = jobdata["notify_image"]


        imgjob.extra_repos = ",".join(extra_repos)
        imgjob.overlay = ",".join(overlay)

        imgjob.queue = Queue.objects.get(name="web")
        imgjob.save()
        
        if jobdata["pinned"]:
            imgjob.tags.add("pinned")
        if jobdata["tags"]:
            tags = [tag.replace(" ","_") for tag in jobdata["tags"].split(",")]
            imgjob.tags.add(*tags)
        
        return HttpResponseRedirect(reverse('img-app-queue'))


@login_required
def search(request, tag=None):
    """
    GET: returns an unbound SearchForm

    POST: process a user submitted SearchForm
    """
    
    if request.method == 'GET':
        form = SearchForm(initial={"searchterm":tag})
        alltags = []
        for x in ImageJob.tags.all():
            if len(ImageJob.objects.filter(tags__name__icontains = x.name)):
                alltags.append(x.name)

        results = []
        if tag:
            results = ImageJob.objects.filter(tags__name__icontains = tag)
        return render_to_response('app/search.html',
                                  {'searchform' : form,
                                   'alltags' : alltags, 'results' : results },
                                  context_instance=RequestContext(request)
                                  )

    if request.method == 'POST':
        form = SearchForm(request.POST)
        if not form.is_valid():
            return render_to_response('app/search.html',
                                      {'searchform': form},
                                       context_instance=RequestContext(request)
                                       )
        data = form.cleaned_data
        results = ImageJob.objects.filter(tags__name__icontains = data["searchterm"])
        return render_to_response('app/search.html',
                                  {'searchform' : form,
                                   'results' : results},
                                  context_instance=RequestContext(request)
                                  )

@login_required
def queue(request, queue_name=None, dofilter=False):
    """ Shows the job queue state

    :param request: request object
    :param queu_name: Queue name to display
    :param dofilter: if True shows only current user's object
    """
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
def toggle_pin_job(request, msgid):
    """ Request deletion of an ImageJob

    :param msgid: ImageJob ID
    """
    imgjob = ImageJob.objects.get(image_id__exact=msgid)
    if imgjob.pinned:
        imgjob.tags.remove("pinned")
        messages.add_message(request, messages.INFO, "Image %s unpinned." % imgjob.image_id)
    else:
        imgjob.tags.add("pinned")
        messages.add_message(request, messages.INFO, "Image %s pinned." % imgjob.image_id)
        
    return HttpResponseRedirect(request.META.get('HTTP_REFERER',
                                reverse('img-app-queue')))
@login_required
def retest_job(request, msgid):
    """ Request retest of an ImageJob

    :param msgid: ImageJob ID
    """
    job = ImageJob.objects.get(image_id__exact=msgid)
    job.status = "DONE"
    job.test_image = True
    #job.test_result = None
    job.test_options = ",".join(["update", job.test_options])
    job.save()
    messages.add_message(request, messages.INFO, "Image %s was set for testing." % job.image_id)
        
    return HttpResponseRedirect(reverse('img-app-queue'))

@login_required
def retry_job(request, msgid):
    """ Request retry of an ImageJob

    :param msgid: ImageJob ID
    """
    oldjob = ImageJob.objects.get(image_id__exact=msgid)

    imgjob = ImageJob()
    imgjob.image_id = "%s-%s" % ( request.user.id, 
                                  time.strftime('%Y%m%d-%H%M%S') )
    imgjob.user = request.user
    imgjob.image_type = oldjob.image_type
    imgjob.overlay = oldjob.overlay
    imgjob.tokenmap = oldjob.tokenmap
    imgjob.arch = oldjob.arch
    imgjob.extra_repos = oldjob.extra_repos
    imgjob.kickstart = oldjob.kickstart
    imgjob.name = oldjob.name
    imgjob.queue = oldjob.queue

    imgjob.save()
    messages.add_message(request, messages.INFO, "Image resubmitted with new id %s." % imgjob.image_id)
        
    return HttpResponseRedirect(reverse('img-app-queue'))
    
@login_required
def delete_job(request, msgid):
    """ Request deletion of an ImageJob

    :param msgid: ImageJob ID
    """
    imgjob = ImageJob.objects.get(image_id__exact=msgid)
    url = request.META.get('HTTP_REFERER', reverse('img-app-queue'))

    if request.user != imgjob.user and ( not request.user.is_staff \
       or not request.user.is_superuser ):
        messages.add_message(request, messages.ERROR, "Sorry, only admins are allowed to delete other people's images.")
        return HttpResponseRedirect(url)
    if imgjob.pinned:
        messages.add_message(request, messages.ERROR, "Sorry, image is pinned and cannot be deleted.")
        return HttpResponseRedirect(url)

    else:
        imgjob.delete()
        messages.add_message(request, messages.INFO, "Image %s deleted." % imgjob.image_id)
        if "queue" not in url:
            url = reverse('img-app-queue')

    return HttpResponseRedirect(url)

@login_required
def job(request, msgid):
    """ Show details about an ImageJob which are either errors or the creation
    log

    :param msgid: ImageJob ID
    """
    imgjob = ImageJob.objects.get(image_id__exact=msgid)
    errors = None

    if request.method == 'POST':
        tagform = TagForm(request.POST)
        if not tagform.is_valid():
            return render_to_response('app/job_details.html',
                                      {'errors': errors,
                                       'obj': imgjob,
                                       'tagform': tagform},
                                       context_instance=RequestContext(request))
        tags = [tag.replace(" ","_") for tag in tagform.cleaned_data['tags']]
        imgjob.tags.set(*tags)

    if imgjob.status == "IN QUEUE":
        errors = { 'Error' : ["Job still in queue"] }
    elif imgjob.error and imgjob.error != "":
        errors = { 'Error' : [imgjob.error] }

    tagform = TagForm(initial = {'tags' : ",".join([tag.name for tag in imgjob.tags.all()])} )

    return render_to_response('app/job_details.html',
                              {'errors': errors,
                               'obj': imgjob,
                               'tagform': tagform},
                                context_instance=RequestContext(request))

def index(request):
    """ Index page """
    return render_to_response('index.html',
                              context_instance=RequestContext(request))
