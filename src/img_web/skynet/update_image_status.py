#!/usr/bin/python
""" Image status update participant """
import os
from urllib2 import urlopen, HTTPError

os.environ['DJANGO_SETTINGS_MODULE'] = 'img_web.settings'

from img_web.app.models import ImageJob
from img_web.utils.a2html import plaintext2html

def get_or_none(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None

class ParticipantHandler(object):

    """ Participant class as defined by the SkyNET API """

    #def __init__(self):
    #    self.obs = None

    def handle_wi_control(self, ctrl):
        """ job control thread """
        pass
    
    def handle_lifecycle_control(self, ctrl):
        """ participant control thread """
        #if ctrl.message == "start":
        #    if ctrl.config.has_option("obs", "oscrc"):
        pass

    def handle_wi(self, wid):

        """ actual job thread """

        # We may want to examine the fields structure
        if wid.fields.debug_dump or wid.params.debug_dump:
            print wid.dump()

        wid.result = False
        if not wid.fields.msg:
            wid.fields.msg = []
        
        if not wid.fields.image.image_id:
            wid.fields.__error__ = "Mandatory field: image.image.id "\
                                   "does not exist."
            wid.fields.msg.append(wid.fields.__error__)
            raise RuntimeError("Missing mandatory field")

        job = get_or_none(ImageJob, image_id__exact=wid.fields.image.image_id)
        if job:
            print "Matched %s job with %s" % (job.image_id, \
                                              wid.fields.image.image_id)
            if wid.params.status:
                job.status = wid.params.status
                if wid.params.status == "ERROR" and wid.fields.__error__:
                    job.error = wid.fields.__error__
                if wid.params.status == "DONE":
                    job.files_url = wid.fields.image.files_url
                    job.image_url = wid.fields.image.image_url
                if wid.params.status == "DONE, TESTED":
                    job.test_result = wid.fields.image.test_result

            if job.status == "BUILDING":
                if wid.fields.image.logfile_url:
                    job.logfile_url = wid.fields.image.logfile_url

            if job.logfile_url.startswith('http'):
                try:
                    print "Getting logfile %s" % job.logfile_url
                    res = urlopen(job.logfile_url).read()
                    res = plaintext2html(res)
                    job.log = res
                except HTTPError as error:
                    print error
                    print error.code

            job.save()
            wid.result = True
        else:
            wid.fields.__error__ = "No %s job found" % wid.fields.image.image_id
            wid.fields.msg.append(wid.fields.__error__)


