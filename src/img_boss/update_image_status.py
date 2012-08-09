#!/usr/bin/python
"""Private participant used by imager to catch status update processes pushed by
the build_image participants

.. warning ::

   * You probably don't want to use this participant in your process, it is
     used privately by the build_image participants

:term:`Workitem` fields IN:

:Parameters:
   :image.image_id (string):
      Unique ID of this image job
   :image.logfile_url (string):
      Copied to the database when the job enters "BUILDING" state and then used
      to download the image building logfile
   :image.files_url (string):
      Copied to the database when the job enters "DONE" or "ERROR" state
   :image.image_url (string):
      Copied to the database when the job enters "DONE" state
   :image.test_result (string):
      Copied to the database when the job enters "DONE, TESTED" state
      
:term:`Workitem` params IN

:Parameters:
   :status (string):
      one of "DONE", "DONE, TESTED", "ERROR"

:term:`Workitem` fields OUT:

:Returns:
   :result (Boolean):
      True if everything was OK, False otherwise
"""

import os
from datetime import datetime
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
            self.log.info("Matched %s job with %s" % (job.image_id, \)
                                              wid.fields.image.image_id)
            if wid.params.status:
                job.status = wid.params.status
                if wid.params.status == "ERROR" and wid.fields.__error__:
                    job.done = datetime.now()
                    job.error = wid.fields.__error__
                    if wid.fields.image.files_url:
                        job.files_url = wid.fields.image.files_url
                if wid.params.status == "DONE":
                    job.done = datetime.now()
                    job.files_url = wid.fields.image.files_url
                    job.image_url = wid.fields.image.image_url
                if wid.params.status == "DONE, TESTED":
                    job.test_result = wid.fields.image.test_result

            if job.status == "BUILDING":
                if wid.fields.image.logfile_url:
                    job.logfile_url = wid.fields.image.logfile_url

            job.save()
            wid.result = True
        else:
            wid.fields.__error__ = "No %s job found" % wid.fields.image.image_id
            wid.fields.msg.append(wid.fields.__error__)

