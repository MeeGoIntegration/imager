#!/usr/bin/python

import datetime , os
os.environ['DJANGO_SETTINGS_MODULE'] = 'img_web.settings'
from img_web.app import models
for i in models.ImageJob.objects.filter(created__lte = datetime.datetime.now() - datetime.timedelta(14)):
  print "deleting %s" % i.task_id
  i.delete()

