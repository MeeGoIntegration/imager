#!/usr/bin/python2.6
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

import json
import subprocess as sub
from subprocess import CalledProcessError
import os
from tempfile import TemporaryFile, NamedTemporaryFile, mkdtemp
import shutil
import re
import time
import random
import copy
from threading import Thread
from multiprocessing import Process, Queue
from amqplib import client_0_8 as amqp
from imgsettings import *

class ImageWorker(object):
    def _getport(self):
        return random.randint(49152, 65535)
    def __init__(self, id, tmpname, type, logfile, dir, port=2222):
        print "init"
        self._amqp_conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
        self._amqp_chan = self._amqp_conn.channel()
        self._tmpname = tmpname
        self._type = type
        self._logfile = logfile
        self._dir = dir
        self._id = id
        self._port = self._getport()
        self._kvmimage = '/tmp/overlay-%s-port-%s'%(self._id, self._port)
        self._cacheimage = '/tmp/cache-image'#%self._id
        self._sshargs = ['/usr/bin/ssh','-o','UserKnownHostsFile=/dev/null','-o','StrictHostKeyChecking=no','-p%s'%self._port, '-lroot', '-i/usr/share/img/id_rsa', '127.0.0.1']        
        self._scpksargs = [ '/usr/bin/scp', '-o','UserKnownHostsFile=/dev/null','-o','StrictHostKeyChecking=no','-P%s'%self._port, '-i/usr/share/img/id_rsa', self._tmpname, "root@127.0.0.1:"+self._dir+"/"]
        self._imagecreate = ['/usr/bin/qemu-img', 'create', '-b','/usr/share/img/base.img', '-f','qcow', "%s"%self._kvmimage]        
        self._cachecreate = ['/usr/bin/qemu-img', 'create', '-f','raw', self._cacheimage, '3G']
        self._kvmargs = ['/usr/bin/sudo','/usr/bin/kvm']
        self._kvmargs.append('-nographic')
        self._kvmargs.append('-net')
        self._kvmargs.append('nic')        
        self._kvmargs.append('-net')
        self._kvmargs.append('user,hostfwd=tcp:127.0.0.1:%s-:22'%self._port)        
        self._kvmargs.append('-daemonize')
        self._kvmargs.append('-drive')
        self._kvmargs.append(str('file='+self._kvmimage+',index=0,media=disk'))
        #self._kvmargs.append('-drive')
        #self._kvmargs.append(str('file='+self._cacheimage+',index=1,media=disk'))
        print self._kvmargs
        
        self._micargs = ['/usr/bin/mic-image-creator', '-d', '-v']
        self._micargs.append('--config='+self._tmpname)
        self._micargs.append('--format='+self._type)
        self._micargs.append('--cache=/tmp/mycache')#+guest_mount_cache)
        self._micargs.append('--outdir='+dir)
        
        self._loopargs = []
        
    def build(self):        
        try:
            #data = json.dumps({'status':"VIRTUAL MACHINE, IMAGE CREATION", "url":base_url+self._id, 'id':self._id})
            #msg = amqp.Message(data)
            #self._amqp_chan.basic_publish(msg, exchange="django_result_exchange", routing_key="status") 
            #sub.check_call(self._imagecreate, shell=False, stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE, bufsize=-1)                        
            #data["status"] = "VIRTUAL MACHINE, RUNNING VM"
            #print data
            #msg = amqp.Message(data)
            #self._amqp_chan.basic_publish(msg, exchange="django_result_exchange", routing_key="status")
#            self._kvmproc = sub.Popen(self._kvmargs, shell=False, stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE, bufsize=-1)
#            time.sleep(90)                        
            #data["status"] = "VIRTUAL MACHINE, RUNNING MIC2"
            #msg = amqp.Message(data)
            #self._amqp_chan.basic_publish(msg, exchange="django_result_exchange", routing_key="status")
#            sshargs = copy.copy(self._sshargs)
#            for arg in self._micargs:
#                sshargs.append(arg)
#            mkdirargs = ['mkdir', '-p', '-v', self._dir]
#            mksshargs = copy.copy(self._sshargs)
#            for mkarg in mkdirargs:
#                mksshargs.append(mkarg)            
#            sub.check_call(mksshargs, shell=False, stdin=sub.PIPE, bufsize=-1)
#            print mksshargs
#            print self._scpksargs
#            sub.check_call(self._scpksargs, shell=False, stdin=sub.PIPE, bufsize=-1)
            sub.check_call(self._micargs, shell=False, stdin=sub.PIPE, stdout=self._logfile, stderr=self._logfile, bufsize=-1)    
            #self._kvmproc.kill()
            #os.kill(self._kvmproc.pid, 1)
        except CalledProcessError as err:
            print "error"
            error = json.dumps({'status':"ERROR","error":"%s"%err, 'id':str(self._id), 'url':base_url+self._id})
            errmsg = amqp.Message(error)
            self._amqp_chan.basic_publish(errmsg, exchange="django_result_exchange", routing_key="status")
            
            #self._kvmproc.kill()
            #os.kill(self._kvmproc.pid, 1)
            return       
        #self._kvmproc.kill()
        #os.kill(self._kvmproc.pid, 1)
        data = json.dumps({'status':"DONE", "url":base_url+self._id, 'id':self._id})
        msg = amqp.Message(data)
        self._amqp_chan.basic_publish(msg, exchange="django_result_exchange", routing_key="status")
        
