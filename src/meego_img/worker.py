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
from threading import Thread
from multiprocessing import Process, Queue
from amqplib import client_0_8 as amqp

amqp_host = "localhost:5672"
amqp_user = "img"
amqp_pwd = "imgpwd"
amqp_vhost = "imgvhost"

class ImageWorker(object):
    def __init__(self, id, tmpname, type, logfile, dir, port=2222):
        self._tmpname = tmpname
        self._type = type
        self._logfile = logfile
        self._dir = dir
        self._id = id
        self._port = port
        self._kvmimage = '/tmp/overlay-%s-port-%s'%(self._id, self._port)
        self._sshargs = ['/usr/bin/sudo','/usr/bin/ssh', '-p%s'%port, '-lroot', '-i/usr/share/img/id_rsa', '127.0.0.1']
        self._imagecreate = ['/usr/bin/qemu-img', 'create', '-b /usr/share/img/base.img', '-f qcow', self._kvmimage]
        self._kvmargs = ['/usr/bin/kvm']
        self._kvmargs.append('-net nic')
        self._kvmargs.append('-net user,hostfwd=tcp:127.0.0.1:%s-:22,restrict=y'%port)
        self._kvmargs.append('-daemonize')
        self._kvmargs.append('-drive file=%s,index=0,media=disk'%(self._kvmimage))
        self._micargs = ['/usr/bin/sudo','/usr/bin/mic-image-creator', '-d', '-v']
        self._micargs.append('--config='+self._tmpname)
        self._micargs.append('--format='+self._type)
        self._micargs.append('--cache=/tmp/mycache/')
        self._micargs.append('--outdir='+self._dir)
        
    def build(self):
        sub.check_call(self._micargs, shell=False, stdout=self._logfile, stderr=self._logfile, bufsize=-1)        
