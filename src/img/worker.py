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

try:
     import json
except ImportError:
     import simplejson as json
import subprocess as sub
from subprocess import CalledProcessError
import os,  sys
from tempfile import TemporaryFile, NamedTemporaryFile, mkdtemp
import shutil
import re
import time
import random
import copy

from amqplib import client_0_8 as amqp
import ConfigParser

config = ConfigParser.ConfigParser()
config.read('/etc/imager/img.conf')
base_url = config.get('worker', 'base_url')
base_dir = config.get('worker', 'base_dir')
post = config.get('worker', 'post_creation')
use_kvm = config.get('worker', 'use_kvm')
mic_args = config.get('worker', 'mic_opts')
mic_cache_dir = config.get('worker', 'mic_cache_dir')

class ImageWorker(object):
    def _getport(self):
        return random.randint(49152, 65535)
    def __init__(self, id, tmpname, type, logfile, dir, port=2222, chan=None, work_item=None, name=None, release=None, arch=None):
        print "init"
        self._tmpname = tmpname
        self._type = type
        self._logfile = logfile
        self._dir = dir
        self._id = id
        self._image =None
        self._release = release
        self._name = name
        self._port = self._getport()
        self._work_item = work_item
        self._amqp_chan = chan
        self._kvmimage = '/tmp/overlay-%s-port-%s'%(self._id, self._port)
        self._cacheimage = '/tmp/cache-image'#%self._id
        self._sshargs = ['/usr/bin/ssh','-o','ConnectTimeout=60', '-o', 'ConnectionAttempts=4','-o','UserKnownHostsFile=/dev/null','-o','StrictHostKeyChecking=no','-p%s'%self._port, '-lroot', '-i/usr/share/img/id_rsa', '127.0.0.1']        
        self._scpksargs = [ '/usr/bin/scp', '-o','UserKnownHostsFile=/dev/null','-o','StrictHostKeyChecking=no','-P%s'%self._port, '-i/usr/share/img/id_rsa']
        self._imagecreate = ['/usr/bin/qemu-img', 'create', '-b','/usr/share/img/base.img','-o','preallocation=metadata', '-o', 'cluster_size=2M', '-f','qcow2', "%s"%self._kvmimage]        
        self._cachecreate = ['/usr/bin/qemu-img', 'create', '-f','raw', self._cacheimage, '3G']
        self._kvmargs = ['/usr/bin/sudo','/usr/bin/kvm']        
        self._kvmargs.append('-nographic')
        self._kvmargs.append('-net')
        self._kvmargs.append('nic,model=virtio')        
        self._kvmargs.append('-net')
        self._kvmargs.append('user,hostfwd=tcp:127.0.0.1:%s-:22'%self._port)        
        self._kvmargs.append('-daemonize')
        self._kvmargs.append('-drive')
        self._kvmargs.append(str('file='+self._kvmimage+',index=0,if=virtio,boot=on'))#,index=0,media=disk'))
        #self._kvmargs.append('-drive')
        #self._kvmargs.append(str('file='+self._cacheimage+',index=1,media=disk'))        
        
        self._micargs = ['mic-image-creator', '-d', '-v']
        self._micargs.append('--config='+self._tmpname)
        self._micargs.append('--format='+self._type)
        self._micargs.append('--cache='+mic_cache_dir)
        self._micargs.append('--outdir='+dir)
        if arch:
            self._micargs.append('--arch='+arch)
        if self._release:
            self._micargs.append('--release='+self._release)
        self._loopargs = []
    def _update_status(self, datadict):
        data = json.dumps(datadict)
        if self._amqp_chan:
            msg = amqp.Message(data)
            self._amqp_chan.basic_publish(msg, exchange="django_result_exchange", routing_key="status") 
        if self._work_item:
            if "status" in datadict:
                fields = self._work_item.fields()
                fields["Status"] = datadict["status"]
                self._work_item.set_fields(fields)
            if "url" in datadict:
                self._work_item.set_field("URL", datadict['url'])
            if "error" in datadict:
                self._work_item.set_field("Error", datadict['error'])
                self._work_item.set_result(None)
            if "image" in datadict:
                self._work_item.set_field("Image", datadict['image'])
                self._work_item.set_result(True)
            if "log" in datadict:
                self._work_item.set_field("Log", datadict['log'])
    def _post_copying(self, datadict):
        for file in os.listdir(self._dir):                
            if os.path.isdir(self._dir+'/'+file):
                for cont in os.listdir(self._dir+'/'+file):                        
                    if not cont.endswith('.xml'):                            
                        self._imagepath = self._dir+'/'+file+'/'+cont
                        self._image = base_url+self._id+'/'+file+'/'+cont
                if self._imagepath and self._name:
                    shutil.move(self._imagepath, self._dir+'/'+self._name+'.'+self._type)
                    self._image = base_url+self._id+'/'+self._name+'.'+self._type
    def build(self):
        logurl = base_url+self._id+'/'+str(os.path.split(self._logfile.name)[-1])
        if use_kvm == "yes":
            try:
                datadict = {'status':"VIRTUAL MACHINE, IMAGE CREATION", "url":base_url+self._id, 'id':self._id}
                self._update_status(datadict)
                sub.check_call(self._imagecreate, shell=False, stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE)                        
                self._update_status(datadict)
                self._kvmproc = sub.Popen(self._kvmargs, shell=False, stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE)
                datadict["status"] = "VIRTUAL MACHINE, WAITING FOR VM"
                self._update_status(datadict)
                time.sleep(15)                        
                datadict["status"] = "VIRTUAL MACHINE, RUNNING MIC2"
                print datadict
                self._update_status(datadict)
                sshargs = copy.copy(self._sshargs)
                for arg in self._micargs:
                    sshargs.append(arg)
                if mic_args:
                    for micarg in mic_args.split(','):
                        sshargs.append(micarg)
                mkdirargs = ['mkdir', '-p', self._dir]
                mksshargs = copy.copy(self._sshargs)
                for mkarg in mkdirargs:
                    mksshargs.append(mkarg)            
                sub.check_call(mksshargs, shell=False, stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE)
                print mksshargs
                print self._scpksargs
                print sshargs            
                toargs = [self._tmpname, "root@127.0.0.1:"+self._dir+"/"]
                scptoargs = copy.copy(self._scpksargs)
                for arg in toargs:
                    scptoargs.append(arg)
                print scptoargs
                sub.check_call(scptoargs, shell=False, stdout=sub.PIPE, stderr=sub.PIPE, stdin=sub.PIPE)            
                sub.check_call(sshargs, shell=False, stdin=sub.PIPE, stdout=self._logfile, stderr=self._logfile, bufsize=-1)  
                fromargs = ['-r',"root@127.0.0.1:"+self._dir+'/*', self._dir+'/']
                scpfromargs = copy.copy(self._scpksargs)
                for arg in fromargs:
                    scpfromargs.append(arg)
                datadict["status"] = "VIRTUAL MACHINE, COPYING IMAGE"
                self._update_status(datadict)
                sub.check_call(scpfromargs, shell=False, stdout=sub.PIPE, stderr=sub.PIPE, stdin=sub.PIPE)            
                self._post_copying(datadict)
                if post:
                    postsshargs = copy.copy(self._sshargs)
                    postscpargs = copy.copy(self._scpksargs)
                    post_toargs = [post, "root@127.0.0.1:"+post]
                    for arg in post_toargs:
                        postscpargs.append(arg)
                    sub.check_call(postscpargs, shell=False, stdout=sub.PIPE, stderr=sub.PIPE, stdin=sub.PIPE)
                    postsshargs.append(post)
                    sub.check_call(postsshargs, shell=False, stdout=sub.PIPE, stderr=sub.PIPE, stdin=sub.PIPE)
		data = {'status':"DONE", "url":base_url+self._id, 'id':self._id, 'log':logurl, 'image':self._image}
                self._update_status(data)
            except CalledProcessError as err:
                print "error %s"%err
                error = {'status':"ERROR","error":"%s"%err, 'id':str(self._id), 'url':base_url+self._id, 'log':logurl}
                self._update_status(error)
                haltargs = copy.copy(self._sshargs)
                haltargs.append('halt')
                print haltargs
                sub.check_call(haltargs, shell=False, stdout=sub.PIPE, stderr=sub.PIPE, stdin=sub.PIPE)
                os.remove(self._kvmimage)
                return   
        else:
            try:
                datadict = {'status':"RUNNING MIC2", "url":base_url+self._id, 'id':self._id, 'log':logurl}                
                self._update_status(datadict)
                micargs = copy.copy(self._micargs)
                if mic_args:
                    for micarg in mic_args.split(','):
                        micargs.append(micarg)
                sub.check_call(micargs, shell=False, stdin=sub.PIPE, stdout=self._logfile, stderr=self._logfile, bufsize=-1) 
                self._post_copying(datadict)
                datadict["image"] = self._image
                datadict['status'] = "DONE"
                self._update_status(data)
            except CalledProcessError as err:
                print "error %s"%err
                error = {'status':"ERROR","error":"%s"%err, 'id':str(self._id), 'url':base_url+self._id, 'log':logurl}
                self._update_status(error)                
                return 
        
