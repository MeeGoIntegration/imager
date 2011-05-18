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
import os, sys
import time
import random
import copy
from img.common import get_worker_config

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

def getport():
    return random.randint(49152, 65535)

def find_largest_file(indir):
    fmap = {}
    for path, dirs, files in os.walk(indir):    
        for file_ in files:
            fullpath = os.path.join(path, file_)
            size = int(os.path.getsize(fullpath))
            fmap[fullpath] = size
    items = fmap.items()
    # Map back the items and sort using size, largest will be the last
    backitems = [ [v[1], v[0]] for v in items ]
    backitems.sort()
    sizesortedlist=[ backitems[i][1] for i in range(0,len(backitems)) ]
    # Its a path, don't worry
    largest_file = sizesortedlist[-1]

    return largest_file

class Commands(object):

    def __init__(self):

        self.port = getport()

        self.sudobase = [
                     'sudo', '-n'
                   ]

        self.overlaybase = [
                        '/usr/bin/qemu-img', 'create', '-b',\
                        img_conf.base_img, '-f', 'qcow2'
                      ]

        self.sopts = [ 
                  '-lroot', '-i%s' % img_conf.id_rsa,
                  '-o', 'ConnectTimeout=60',
                  '-o', 'ConnectionAttempts=4',
                  '-o', 'UserKnownHostsFile=/dev/null',
                  '-o', 'StrictHostKeyChecking=no'
                ]

        self.sshbase = [ 
                    '/usr/bin/ssh', 
                    '-p%s' % port,
                    '127.0.0.1'
                  ]

        self.scpbase = [ 
                    '/usr/bin/scp',
                    '-P%s' % port,
                    '-r'
                  ]

        self.kvmbase = [
                    '/usr/bin/qemu-kvm',
                    '-nographic',
                    '-daemonize',
                    '-m', '256M',
                    '-net', 'nic,model=virtio',
                    '-net', 'user,hostfwd=tcp:127.0.0.1:%s-:22' % port,
                    '-drive', 'index=0,if=virtio,file=%s' % self._kvmimage
                  ]

        self.micbase = [
                    'mic-image-creator',
                    '--config=%s' % self._tmpname,
                    '--format=%s' % self._type,
                    '--cache=%s' % mic_cache_dir,
                  ]

        if self._type == "fs":
            self._micargs.append('--package=tar.gz')
        if arch:
            self._arch = arch
            self._micargs.append('--arch='+arch)
        if self._release:
            self._micargs.append('--release='+self._release)
        for arg in self._micargs:
            sshargs.append(arg)
        if mic_args:
            for micarg in mic_args.split(','):
                sshargs.append(micarg)
        if mic_args:
            custom_args = copy.copy(self._micargs)
            for arg in mic_args.split(','):
                custom_args.append(arg)

    def run(self, command, verbose=False):
        if verbose:
            print command
        if execute:
            sub.check_call(command, shell=False, stdout=self._logfile, 
                           stderr=self._logfile, stdin=sub.PIPE)

    def scpto(self, source="", dest=""):
        scp_comm = copy(self.scpbase)
        scp_comm.extend(self.sopts)
        scp_comm.append(source)
        scp_comm.append("127.0.0.1:%s" % dest)
        self.run(scp_comm)

    def scpfrom(self, source="", dest=""):
        scp_comm = copy(self.scpbase)
        scp_comm.extend(self.sopts)
        scp_comm.append("127.0.0.1:%s" % source)
        scp_comm.append(dest)
        self.run(scp_comm)

    def ssh(self, command=""):
        ssh_comm = copy(self.sshbase)
        ssh_comm.extend(self.sopts)
        ssh_comm.extend(command)
        self.run(ssh_comm)

    def overlaycreate(self, tmpoverlay):
        overlay_comm = copy(self.overlaybase)
        overlay_comm.append(tmpoverlay)
        self.run(overlay_comm)

    def runkvm(self):
        kvm_comm = copy(self.kvmbase)
        if use_sudo:
            sudo = copy(self.sudobase)
            kvm_comm = sudo.extend(kvm_comm)
        self.run(kvm_comm)

    def runmic(ssh=False):
        mic_comm = copy(self.micbase)
        if ssh:
            self.ssh(mic_comm)
        else:
            if use_sudo:
                sudo = copy(self.sudobase)
                mic_comm = sudo.extend(mic_comm)
            self.run(mic_comm)



class ImageWorker(object):

    def __init__(self, image_id=None, ksfile_name=None, image_type=None,
                 logfile_name=None, image_dir=None, port=None,
                 name=None, release=None, arch=None, dir_prefix=None):
        
        self.config = get_worker_config()
        
        self.commands = Commands()

        self._tmpname = tmpname
        self._type = type
        self._logfile = logfile
        self._dir = dir
        self._dir_prefix = dir_prefix
        self._base_url_dir = base_url + '/' + self._dir_prefix + '/'
        self._image_id = image_id
        self._image =None
        self._release = release
        self._name = name

    
    def build(self):

        commands = Commands()

        if self.config.use_kvm == "yes" and os.path.exists('/dev/kvm'):
            try:

                kvmimage = os.path.join(self.config.img_tmp, 
                                        'overlay-%s-port-%s' % (self._image_id, 
                                                                self._port))
                commands.overlaycreate(self._kvmimage)

                commands.runkvm()

                time.sleep(20)

                commands.scpto(source='/etc/mic2/mic2.conf',
                               dest='/etc/mic2/')

                commands.scpto(source='/etc/sysconfig/proxy',
                               dest='/etc/sysconfig/')

                commands.ssh(['mkdir', '-p', self._dir])

                commands.scpto(source=self._tmpname,
                               dest=self._dir)

                commands.runmic(ssh=True)

                commands.scpfrom(source=self._dir+'/*',
                                 dest=self._dir+'/')

            except Exception, err:
                print "error %s"%err
                return False

            finally:

                try:
                    commands.ssh(['poweroff', '-f'])
                except:
                    #FIXME: try -KILL using PID if set (where?)
                    pass

                os.remove(self._kvmimage)

        elif not self.config.use_kvm == 'yes':
            try:

                commands.runmic(ssh=False)

            except Exception, err:

                print "error %s" % err
                return False
        else:
            return False

    image_file = find_largest_file(base_dir)

    self._image = self._base_url_dir+self._id+'/' + image_file

    return True
