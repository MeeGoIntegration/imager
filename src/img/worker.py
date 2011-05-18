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
use_sudo = config.get('worker', 'use_sudo')
mic_args = config.get('worker', 'mic_opts')
mic_cache_dir = config.get('worker', 'mic_cache_dir')
img_home = config.get('worker', 'img_home')
img_tmp = config.get('worker', 'img_tmp')

id_rsa = os.path.join(img_home, 'id_rsa')
base_img = os.path.join(img_home, 'base.img')

class ImageWorker(object):
    def _getport(self):
        return random.randint(49152, 65535)
    def __init__(self, \
        id, \
        tmpname, \
        type, \
        logfile, \
        dir, \
        port=2222, \
        name=None, \
        release=None, \
        arch='i686', \
        dir_prefix="unknown"\
        ):
        print "init"
        sys.stdout.flush()
        self._tmpname = tmpname
        self._type = type
        self._logfile = logfile
        self._dir = dir
        self._dir_prefix = dir_prefix
        self._base_url_dir = base_url + '/' + self._dir_prefix + '/'
        self._id = id
        self._image =None
        self._release = release
        self._name = name
        self._port = self._getport()
        self._kvmimage = os.path.join(img_tmp, 
                'overlay-%s-port-%s' % (self._id, self._port))
        self._cacheimage = os.path.join(img_tmp, 'cache-image')#%self._id
        self._sshargs = [ '/usr/bin/ssh',\
                '-o',\
                'ConnectTimeout=60', \
                '-o', \
                'ConnectionAttempts=4', \
                '-o', \
                'UserKnownHostsFile=/dev/null',\
                '-o', \
                'StrictHostKeyChecking=no', \
                '-p%s'%self._port, \
                '-lroot', \
                '-i%s'%id_rsa, \
                '127.0.0.1' ] 
        self._scpksargs = [ '/usr/bin/scp', \
        '-o', \
        'UserKnownHostsFile=/dev/null', \
        '-o', \
        'StrictHostKeyChecking=no', \
        '-P%s'%self._port, \
        '-i%s'%id_rsa]
        self._imagecreate = ['/usr/bin/qemu-img', \
        'create', \
        '-b', \
        base_img ,\
        '-o', \
        'preallocation=metadata', \
        '-o', \
        'cluster_size=2048', \
        '-f', \
        'qcow2', \
        "%s"%self._kvmimage]
        self._kvmargs = ['/usr/bin/qemu-kvm']
        self._kvmargs.append('-nographic')
        self._kvmargs.append('-m')
        self._kvmargs.append('256M')
        self._kvmargs.append('-net')
        self._kvmargs.append('nic,model=virtio')
        self._kvmargs.append('-net')
        self._kvmargs.append('user,hostfwd=tcp:127.0.0.1:%s-:22' % self._port)
        self._kvmargs.append('-daemonize')
        self._kvmargs.append('-drive')
        self._kvmargs.append(str('file=' + self._kvmimage + ',index=0,if=virtio'))
        self._micargs = ['mic-image-creator', '-d', '-v']
        self._micargs.append('--config='+self._tmpname)
        self._micargs.append('--format='+self._type)
        if self._type == "fs":
            self._micargs.append('--package=tar.gz')
        self._micargs.append('--cache='+mic_cache_dir)
        self._micargs.append('--outdir='+dir)
        if arch:
            self._arch = arch
            self._micargs.append('--arch='+arch)
        if self._release:
            self._micargs.append('--release='+self._release)
        self._loopargs = []
        if use_sudo=='yes':
            self._kvmargs.insert(0,'/usr/bin/sudo')
            self._kvmargs.insert(1,'-n')
            self._imagecreate.insert(0,'/usr/bin/sudo')
            self._imagecreate.insert(1,'-n')
    def _update_status(self, datadict):
        pass
    def _post_copying(self):
        fmap = {}
        for path, dirs, files in os.walk(self._dir):    
            for file_ in files:
                fullpath = os.path.join(path,file_)
                size = int(os.path.getsize(fullpath))
                fmap[fullpath] = size
        items = fmap.items()
        # Map back the items and sort using size, largest will be the last
        backitems = [ [v[1], v[0]] for v in items]
        backitems.sort()
        sizesortedlist=[ backitems[i][1] for i in range(0,len(backitems))]
        # Its a path, don't worry
        largest_file = sizesortedlist[-1].split(self._dir)[-1]
        self._image = self._base_url_dir+self._id+'/'+largest_file
    def _append_to_base_command_and_run(self,base,command,execute=True,verbose=False):
        copy_base = copy.copy(base)        
        copy_base = copy_base + command
        if verbose:
            print copy_base
            sys.stdout.flush()
        if execute:
            sub.check_call(copy_base, shell=False, stdout=self._logfile, stderr=self._logfile, stdin=sub.PIPE)
    
    def build(self):
        if use_kvm == "yes" and os.path.exists('/dev/kvm'):
            try:
                print self._imagecreate
                sub.check_call(self._imagecreate, shell=False, stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE)
                print self._kvmargs
                self._kvmproc = sub.Popen(self._kvmargs, shell=False, stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE)
                time.sleep(20)
                sshargs = copy.copy(self._sshargs)
                for arg in self._micargs:
                    sshargs.append(arg)
                if mic_args:
                    for micarg in mic_args.split(','):
                        sshargs.append(micarg)
                mic2confargs = ['/etc/mic2/mic2.conf','root@127.0.0.1:/etc/mic2/']
                self._append_to_base_command_and_run(self._scpksargs, mic2confargs)
                proxyconfargs = ['/etc/sysconfig/proxy','root@127.0.0.1:/etc/sysconfig/']
                self._append_to_base_command_and_run(self._scpksargs, proxyconfargs)
                mkdirargs = ['mkdir', '-p', self._dir]
                self._append_to_base_command_and_run(self._sshargs, mkdirargs)
                toargs = [self._tmpname, "root@127.0.0.1:"+self._dir+"/"]
                self._append_to_base_command_and_run(self._scpksargs, toargs)
                if mic_args:
                    custom_args = copy.copy(self._micargs)
                    for arg in mic_args.split(','):
                        custom_args.append(arg)
                    self._append_to_base_command_and_run(self._sshargs, custom_args,verbose=True)
                else:
                    self._append_to_base_command_and_run(self._sshargs, self._micargs, verbose=True)
                fromargs = ['-r',"root@127.0.0.1:"+self._dir+'/*', self._dir+'/']
                self._append_to_base_command_and_run(self._scpksargs, fromargs, verbose=True)
                self._post_copying()
                #if post:
                #    post_toargs = [post, "root@127.0.0.1:"+post]
                #    self._append_to_base_command_and_run(self._scpksargs, post_toargs,verbose=True)
                #    self._append_to_base_command_and_run(self._sshargs, post,verbose=True)
                sys.stdout.flush() 
                return True
            except Exception,err:
                print "error %s"%err
                return False
            try:
                self._append_to_base_command_and_run(self._sshargs, ['poweroff', '-f'], verbose=True)
            except:
                pass
            os.remove(self._kvmimage)
            sys.stdout.flush()
            return
        elif use_kvm=='no':
            try:
                if mic_args:
                    self._append_to_base_command_and_run(self._micargs, [''], verbose=True)
                else:
                    self._append_to_base_command_and_run(self._micargs, mic_args,verbose=True)
                self._post_copying()
                sys.stdout.flush()
                return True
            except Exception,err:
                print "error %s"%err
                sys.stdout.flush()
                return False
        else:
            return False
