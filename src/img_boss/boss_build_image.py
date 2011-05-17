#!/usr/bin/python
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

import os, sys, traceback, ConfigParser, optparse, io, pwd, grp
from tempfile import TemporaryFile, NamedTemporaryFile, mkdtemp
import daemon

import random
from img.worker import ImageWorker
from img.common import mic2
try:
     import simplejson as json
except ImportError:
     import json
from SkyNET import (WorkItemCtrl, ParticipantCtrl, Workitem)



participant_name = "build_image"

# Fallback configuration. If you need to customize it, copy it somewhere 
# ( ideally to your system's configuration directory ), modify it and 
# pass it with the -c option
defaultconf = """[boss]
amqp_host = 127.0.0.1:5672
amqp_user = boss
amqp_pwd = boss
amqp_vhost = boss
[%s]
daemon = Yes 
logfile = /var/log/%s.log
runas_user = root
runas_group = root
[worker]
base_url = http://192.168.11.2/images/
base_dir = /var/www/images
num_workers = 2
post_creation = /bin/echo
use_kvm = yes
; Example, mic_opts = --save-kernel, --use_comps, so comma separated options
mic_opts =
""" % ( participant_name, participant_name )

try:
    conf = open('/etc/imager/img.conf')
except:
    # Fallback
    conf = io.BytesIO(defaultconf)

config = ConfigParser.ConfigParser()
config.readfp(conf)
conf.close()


config_logfile = config.get(participant_name, 'logfile')
num = options.num if options.num else '0'
config_logfile = config_logfile+'.boss.'+num+'.log'
config_pidfile = config.get(participant_name,'pidfile')
config_pidfile = config_pidfile+'.boss.'+num+'.pid'
runas_user = config.get(participant_name, 'runas_user')
runas_group = config.get(participant_name, 'runas_group')
uid = pwd.getpwnam(runas_user)[2]
gid = grp.getgrnam(runas_group)[2]

use_kvm = config.get('worker', 'use_kvm')
base_url = config.get('worker', 'base_url')
base_dir = config.get('worker', 'base_dir')
post = config.get('worker', 'post_creation')

# if not root...kick out
if not os.geteuid()==0:
    sys.exit("\nOnly root can run this script\n")
if not os.path.exists('/dev/kvm') and use_kvm == "yes":
    sys.exit("\nYou must enable KVM kernel module\n")

class ParticipantHandler(object):
    """ Participant class as defined by the SkyNET API """

    def __init__(self):
        pass

    def handle_wi_control(self, ctrl):
        """ job control thread """
        pass

    def handle_lifecycle_control(self, ctrl):
        pass

    def handle_wi(self, wid):
        try:
            wi = wid.fields
            email = wi.email
            kickstart = wi.kickstart
            iid = wi.id
            itype = wi.type
            name = wi.name
            release = wi.release
            arch = wi.arch
            print "Workitem: "
            print json.dumps(wi.to_h())
            prefix="requests"
            if "prefix" in fields.keys():
              prefix = fields["prefix"]
            if kickstart:
                mic2(iid, name, itype,  email, kickstart, release, arch, dir_prefix=prefix, work_item=wi)
            msg = wi.msg if 'msg' in wi else []
            msg.append('Test image build result was %s, details can be viewed here: %s ' % (wi.status, wi.url))
            wi.msg = msg
            result = True
        except Exception , error:            
            print error
            msg = wi.msg if 'msg' in wid.fields else []
            msg.append('Test image build result was FAILED, error was : %s ' % (error))
            wi.msg = msg
            traceback.print_exc(file=sys.stdout)
            wi.status = "FAILED"
            result = False
        sys.stdout.flush()
        wid.set_result(result)


