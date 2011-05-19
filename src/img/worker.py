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

import subprocess as sub
import os
import time
import random
from copy import copy

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
    sizesortedlist = [ backitems[i][1] for i in range(0, len(backitems)) ]
    # Its a path, don't worry
    largest_file = sizesortedlist[-1]

    return largest_file

class Commands(object):

    def __init__(self, use_sudo=None, ssh_key=None, log_filename=None):

        self.port = getport()

        self._logf = log_filename

        if use_sudo:
            self.use_sudo = True

        self.sudobase = [
                     'sudo', '-n'
                   ]

        self.overlaybase = [
                        '/usr/bin/qemu-img', 'create', '-f', 'qcow2', '-b'
                      ]

        self.sopts = [ 
                  '-i%s' % ssh_key,
                  '-o', 'ConnectTimeout=60',
                  '-o', 'ConnectionAttempts=4',
                  '-o', 'UserKnownHostsFile=/dev/null',
                  '-o', 'StrictHostKeyChecking=no'
                ]

        self.sshbase = [ 
                    '/usr/bin/ssh', 
                    '-p%s' % self.port,
                    '-lroot',
                    '127.0.0.1'
                  ]

        self.scpbase = [ 
                    '/usr/bin/scp',
                    '-P%s' % self.port,
                    '-r'
                  ]

        self.kvmbase = [
                    '/usr/bin/qemu-kvm',
                    '-nographic',
                    '-daemonize',
                    '-m', '256M',
                    '-net', 'nic,model=virtio',
                    '-net', 'user,hostfwd=tcp:127.0.0.1:%s-:22' % self.port,
                    '-drive', 'index=0,if=virtio,media=disk,cache=writeback,' \
                              'file=@KVMIMAGEFILE@'
                  ]

        self.micbase = [
                    'mic-image-creator'
                  ]


    def run(self, command):
        with open(self._logf, 'a+b') as logf:
            logf.write(" ".join(command))
            sub.check_call(command, shell=False, stdout=logf, 
                           stderr=logf, stdin=sub.PIPE)

    def scpto(self, source="", dest=""):
        scp_comm = copy(self.scpbase)
        scp_comm.extend(self.sopts)
        scp_comm.append(source)
        scp_comm.append("root@127.0.0.1:%s" % dest)
        self.run(scp_comm)

    def scpfrom(self, source="", dest=""):
        scp_comm = copy(self.scpbase)
        scp_comm.extend(self.sopts)
        scp_comm.append("root@127.0.0.1:%s" % source)
        scp_comm.append(dest)
        self.run(scp_comm)

    def ssh(self, command=""):
        ssh_comm = copy(self.sshbase)
        ssh_comm.extend(self.sopts)
        ssh_comm.extend(command)
        self.run(ssh_comm)

    def overlaycreate(self, baseimg, tmpoverlay):
        overlay_comm = copy(self.overlaybase)
        overlay_comm.extend([baseimg, tmpoverlay])
        self.run(overlay_comm)

    def runkvm(self, overlayimg):
        kvm_comm = copy(self.kvmbase)
        filearg = kvm_comm.pop()
        filearg = filearg.replace("@KVMIMAGEFILE@", overlayimg)
        kvm_comm.append(filearg)
        if self.use_sudo:
            sudo = copy(self.sudobase)
            kvm_comm = sudo.extend(kvm_comm)
        self.run(kvm_comm)

    def runmic(self, ssh=False, job_args=job_args):
        mic_comm = copy(self.micbase)
        mic_comm.append('--config=%s' % job_args["ksfile_name"])
        mic_comm.append('--format=%s' % job_args["image_type"])
        mic_comm.append('--arch=%s' % job_args["arch"])
        mic_comm.append('--outdir=%s' % job_args["outdir"])

        # Workaround until bug is fixed in mic2
        if job_args["image_type"] == "fs":
            mic_comm.append('--package=tar.gz')

        if "release" in job_args.keys():
            mic_comm.append('--release=%s' % job_args["release"])

        if "extra_opts" in job_args.keys():
            for opt in job_args["extra_opts"]:
                mic_comm.append(opt)

        if ssh:
            self.ssh(mic_comm)
        else:
            if self.use_sudo:
                sudo = copy(self.sudobase)
                mic_comm = sudo.extend(mic_comm)
            self.run(mic_comm)


class ImageWorker(object):

    def __init__(self, config=None, job_args=None):

        self.config = config
        
        self._image_dir = os.path.join(config.base_dir, job_args["prefix"],
                                       job_args["image_id"])

        self._image_dir = "%s/" % self._image_dir

        job_args["outdir"] = self._image_dir
        
        self.logfile_name = os.path.join(self._image_dir,
                                         "%s.log" % job_args["name"])
        self.files_url = "%s/%s/%s" % (config.base_url, job_args["prefix"], 
                                       job_args["image_id"])
        
        self.job_args = job_args
        self.image_file = None
        self.image_url = None
    
    def build(self):

        commands = Commands(use_sudo=self.config.use_sudo,
                            ssh_key=self.config.ssh_key,
                            log_filename=self.logfile_name)

        os.makedirs(self._image_dir, 0775)

        ksfile_name = os.path.join(self._image_dir, "%s.ks" %\
                                   self.job_args["name"])

        with open(ksfile_name, mode='w+b') as ksfile:
            ksfile.write(self.job_args["kickstart"])
        os.chmod(ksfile_name, 0644)

        self.job_args['kickstart_file'] = ksfile_name

        if self.config.use_kvm and os.path.exists('/dev/kvm'):
            try:

                overlayimg = os.path.join(self.config.img_tmp, \
                                         'overlay-%s-port-%s' % \
                                         (self.job_args["image_id"], \
                                          commands.port))

                commands.overlaycreate(self.config.base_img, overlayimg)

                commands.runkvm(overlayimg)

                time.sleep(20)

                commands.scpto(source='/etc/mic2/mic2.conf',
                               dest='/etc/mic2/')

                commands.scpto(source='/etc/sysconfig/proxy',
                               dest='/etc/sysconfig/')

                commands.ssh(['mkdir', '-p', self._image_dir])

                commands.scpto(source=ksfile_name,
                               dest=self._image_dir)

                commands.runmic(ssh=True, job_args=self.job_args)

                commands.scpfrom(source="%s*" % self._image_dir,
                                 dest=self._image_dir)

            except Exception, err:
                print "error %s" % err
                return False

            finally:

                try:
                    commands.ssh(['poweroff', '-f'])
                except Exception, err:
                    #FIXME: try -KILL using PID if set (where?)
                    print "error %s" % err
                finally:
                    os.remove(overlayimg)

        elif not self.config.use_kvm:
            try:

                commands.runmic(ssh=False, job_args=self.job_args)

            except Exception, err:
                print "error %s" % err
                return False
        else:
            return False

        self.image_file = find_largest_file(self._image_dir)
    
        self.image_url = self.image_file.replace(self.config.base_dir,
                                                 self.config.base_url)
        return True

    def get_results(self):
        results = {
                    "files_url"  : self.files_url,
                    "image_file" : self.image_file,
                    "image_url"  : self.image_url,
                    "log_file"   : self.logfile_name
                  }

        return results
