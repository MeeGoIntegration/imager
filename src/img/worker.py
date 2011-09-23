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
"""MIC2 mic-image-creator wrapper"""

import subprocess as sub
import os
import time
import random
from copy import copy

def getport():
    """Gets a random port for the KVM virtual machine communtication, target 
    always being the SSH port.

    :returns: random port number between 49152 and 65535
    """
    return random.randint(49152, 65535)

def find_largest_file(indir):
    """Find the largest file in a given directory string.
    indir: Directory to find as string
    Returns the largest file in the given directory
    BACKGROUND:
    Essentially Imager needs to return the url to the image and this is the 
    best way to find out which one is the image (biggest file is usually the 
    image).

    :param indir: Directory to search in

    :returns: largest file in the directory
    """
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
    """Commands object for running various image building commands"""

    def __init__(self, vm_kernel, ssh_key=None, log_filename=None):
        """Constructor, creates the object with necessary parameters to run 
        commands
        
        :param vm_kernel: linux kernel to boot the vm
        :param ssh_key: Path to the ssh private key used to connect to the base
           KVM image.
        :param log_filename: Filename to pipe the output to. Used by both KVM
           and MIC2

        """
        self.port = getport()

        self._logf = log_filename

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
                    '-nographic', '-no-reboot',
                    '-daemonize', '-m', '256M',
                    '-kernel', vm_kernel,
                    '-append', 'root=/dev/vda panic=1 quiet rw elevator=noop',
                    '-net', 'nic,model=virtio',
                    '-net', 'user,hostfwd=tcp:127.0.0.1:%s-:22' % self.port,
                    '-drive', 'index=0,if=virtio,media=disk,cache=writeback,' \
                              'file=@KVMIMAGEFILE@'
                  ]

        self.micbase = [
                    'mic-image-creator'
                  ]


    def run(self, command):
        """Method to run an arbitrary command and pipe the log output to a file.
        Uses subprocess.check_call to properly execute and catch if any errors
        occur.

        :param command: Arbitary command to run
        """
        with open(self._logf, 'a+b') as logf:
            logf.write(" ".join(command))
            sub.check_call(command, shell=False, stdout=logf, 
                           stderr=logf, stdin=sub.PIPE)

    def scpto(self, source="", dest=""):
        """Generic ssh copy file method, from KVM to host.

        :param source: file to copy
        :param dest: destination file to copy to
        """
        scp_comm = copy(self.scpbase)
        scp_comm.extend(self.sopts)
        scp_comm.append(source)
        scp_comm.append("root@127.0.0.1:%s" % dest)
        self.run(scp_comm)

    def scpfrom(self, source="", dest=""):
        """Generic ssh copy file method, from host to KVM.

        :param source: file to copy
        :param dest: destination file to copy to
        """
        scp_comm = copy(self.scpbase)
        scp_comm.extend(self.sopts)
        scp_comm.append("root@127.0.0.1:%s" % source)
        scp_comm.append(dest)
        self.run(scp_comm)

    def ssh(self, command=""):
        """Execute an arbitrary command in the KVM guest.
        
        :param command: Arbitary command to run over ssh inside kvm
        """
        ssh_comm = copy(self.sshbase)
        ssh_comm.extend(self.sopts)
        ssh_comm.extend(command)
        self.run(ssh_comm)

    def overlaycreate(self, baseimg, tmpoverlay):
        """Create an overlay image based on a base image, usually a minimal OS
        with a static ssh-key built-in, as long its capable of running MIC2.
        
        :param baseimg: path to base qcow2 file
        :param tmpoverlay: path to qcow2 overlay going to be created
        """
        overlay_comm = copy(self.overlaybase)
        overlay_comm.extend([baseimg, tmpoverlay])
        self.run(overlay_comm)

    def runkvm(self, overlayimg):
        """Run KVM using the created overlay image.

        :param overlayimg: path to qcow2 overlay based on the configured 
           minimal KVM image
        """
        kvm_comm = copy(self.kvmbase)
        filearg = kvm_comm.pop()
        filearg = filearg.replace("@KVMIMAGEFILE@", overlayimg)
        kvm_comm.append(filearg)
        sudo = copy(self.sudobase)
        sudo.extend(kvm_comm)
        kvm_comm = sudo
        self.run(kvm_comm)

    def runmic(self, ssh=False, job_args=None):
        """Run MIC2, using ssh or executing on the host, with arguments.

        :param ssh: wether to use ssh
        :pram job_args: Arguments for MIC2
        """
        mic_comm = copy(self.micbase)
        mic_comm.append('--config=%s' % job_args.ksfile_name)
        mic_comm.append('--format=%s' % job_args.image_type)
        mic_comm.append('--arch=%s' % job_args.arch)
        mic_comm.append('--outdir=%s' % job_args.outdir)

        if job_args.image_type == "fs":
            mic_comm.append('--compress-disk-image=tar.bz2')

        if job_args.release:
            mic_comm.append('--release=%s' % job_args.release)
        if job_args.extra_opts:
            for opt in job_args.extra_opts:
                mic_comm.append(opt)

        if ssh:
            self.ssh(mic_comm)
        else:
            sudo = copy(self.sudobase)
            sudo.extend(mic_comm)
            mic_comm = sudo
            self.run(mic_comm)


class ImageWorker(object):
    """Actual worker class that does the heavy lifting."""
    def __init__(self, config=None, job_args=None):
        """Initialize the worker using a config and job args.

        :param config: Worker config in a hash proxy object
        :param job_args: hash proxy object describing the image job 
        """
        self.config = config
        
        self._image_dir = os.path.join(config.base_dir, job_args.prefix,
                                       job_args.image_id)

        self._image_dir = "%s/" % self._image_dir

        job_args.outdir = self._image_dir
        
        self.logfile_name = os.path.join(self._image_dir,
                                         "%s.log" % job_args.name)
        self.logfile_url = self.logfile_name.replace(self.config.base_dir,
                                                     self.config.base_url)
        self.files_url = "%s/%s/%s" % (config.base_url, job_args.prefix, 
                                       job_args.image_id)
        
        self.job_args = job_args
        self.image_file = None
        self.image_url = None
        self.result = None
        self.error = None
    
    def build(self):
        """Build the image in KVM or in host.
        When building the image in KVM, first create an overlay and then use 
        it to create the VM. After the VM is running, copy the kickstart, MIC2 
        config and proxy settings to the guest. Then create the output 
        directory and then run MIC2. When its ready, copy the entire image 
        directory."""
        commands = Commands(self.config.vm_kernel,
                            ssh_key=self.config.vm_ssh_key,
                            log_filename=self.logfile_name)

        print self._image_dir
        os.makedirs(self._image_dir, 0775)

        ksfile_name = os.path.join(self._image_dir, "%s.ks" %\
                                   self.job_args.name)

        with open(ksfile_name, mode='w+b') as ksfile:
            ksfile.write(self.job_args.kickstart)
        os.chmod(ksfile_name, 0644)

        self.job_args.ksfile_name = ksfile_name

        if self.config.use_kvm and os.path.exists('/dev/kvm'):
            try:

                overlayimg = os.path.join(self.config.img_tmp, \
                                         'overlay-%s-port-%s' % \
                                         (self.job_args.image_id, \
                                          commands.port))

                commands.overlaycreate(self.config.vm_base_img, overlayimg)

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

                self.result = True

            except Exception, err:
                print "error %s" % err
                self.error = str(err)
                self.result = False

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
                self.result = True

            except Exception, err:
                print "error %s" % err
                self.error = str(err)
                self.result = False
        else:
            self.result = False

        self.image_file = find_largest_file(self._image_dir)
    
        self.image_url = self.image_file.replace(self.config.base_dir,
                                                 self.config.base_url)

    def get_results(self):
        """Returns the results in a dictionary.

        :returns: results dictionary
        """
        results = {
                    "result"     : self.result,
                    "files_url"  : self.files_url,
                    "image_url"  : self.image_url,
                    "logfile_url": self.logfile_url,
                    "error"      : self.error
                  }

        return results
