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

import os
import subprocess as sub
from multiprocessing import Process, TimeoutError
import time, datetime
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

def fork(logfile, command):
    with open(logfile, 'a+b') as logf:
        sub.check_call(command, shell=False, stdout=logf, 
                       stderr=logf, stdin=sub.PIPE)


class Commands(object):
    """Commands object for running various image building commands"""

    def __init__(self, vm_kernel, ssh_key=None, log_filename=None,
                 timeout=3600):
        """Constructor, creates the object with necessary parameters to run 
        commands
        
        :param vm_kernel: linux kernel to boot the vm
        :param ssh_key: Path to the ssh private key used to connect to the base
           KVM image.
        :param log_filename: Filename to pipe the output to. Used by both KVM
           and MIC2
        :param timeout: integer value used to set an alarm signal that
           interrupts any command that runs for too long

        """
        self.port = getport()

        self._logf = log_filename

        self.timeout = timeout

        self.sudobase = [
                     'sudo', '-n'
                   ]

        self.killkvmbase = [
                     'pkill', '-f'
                   ]

        self.overlaybase = [
                        '/usr/bin/qemu-img', 'create', '-f', 'qcow2', '-b'
                      ]

        self.lvmsnapshot = [
                        '/sbin/lvcreate', '-s', '-l', '100%ORIGIN', '-n'
                      ]

        self.lvdisplay = [
                        '/sbin/lvdisplay', '-c'
                      ]

        self.lvremove = [
                        '/sbin/lvremove', '-f'
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

        # use the existence if mic-image-creator as a sign mic2 is installed
        # even inside the kvm which could be incorrect, but good for now
        if os.path.exists("/usr/bin/mic-image-creator"):
            self.micbase = [
                        'mic-image-creator'
                      ]
            self.ict = "mic2"
        elif os.path.exists("/usr/bin/mic"):
            self.micbase = [
                        'mic', 'create'
                      ]
            self.ict = "newmic"
        # could kiwi or debootstrap be supported ? ;)
        else:
            raise RuntimeError("Couldn't find a supported mic tool")

        self.kvm_comm = None

    def run(self, command):
        """Method to run an arbitrary command and pipe the log output to a file.
        Uses subprocess.check_call to properly execute and catch if any errors
        occur.

        :param command: Arbitary command to run
        """
        with open(self._logf, 'a+b') as logf:
            logf.write("\n%s : %s\n" % (datetime.datetime.now(),
                                        " ".join(command)))
            logf.flush()
        proc = Process(target=fork, args=(self._logf, command))
        proc.start()
        proc.join(self.timeout)
        if proc.is_alive():
            with open(self._logf, 'a+b') as logf:
                logf.write("\n%s : Command still running after %s seconds" %
                          (datetime.datetime.now(), self.timeout))
                logf.flush()

            proc.terminate()
            raise TimeoutError("Command was still running after %s "\
                               "seconds" % self.timeout)
        elif not proc.exitcode == 0:
            raise sub.CalledProcessError(int(proc.exitcode), " ".join(command))

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

    def is_lvm(self, img):
        """Returns true if a file is recognized by lvdisplay as an LV

        :param img: path to file to be checked
        :returns: True if the file is an lvm logical volume, False otherwise
        """
        lvd_comm = copy(self.lvdisplay)
        lvd_comm.append(img)
        lvd_comm.extend(copy(self.sudobase))
        try:
            self.run(lvd_comm)
        except sub.CalledProcessError:
            return False
        else:
            return True

    def overlaycreate(self, overlay_img_tmp, baseimg, overlay_suffix):
        """Create an overlay image based on a base image, usually a minimal OS
        with ssh-key access and capable of running MIC.
        
        :param overlay_img_tmp: directory for temporary overlay images
        :param baseimg: path to base image (qcow2 file or LV device node)
        :param overlay_suffix: suffix to make overlay name unique

        :returns: path to the new created overlay image
        """
        if self.is_lvm(baseimg):
            overlay_img = "%s-%s" % (os.path.basename(baseimg), overlay_suffix)
            overlay_comm = copy(self.lvmsnapshot)
            overlay_comm.extend([overlay_img, baseimg])
            overlay_comm.extend(copy(self.sudobase))
        else:
            overlay_img = os.path.join(overlay_img_tmp, overlay_suffix)
            overlay_comm = copy(self.overlaybase)
            overlay_comm.extend([baseimg, overlay_img])
        self.run(overlay_comm)
        return overlay_img

    def runkvm(self, overlayimg):
        """Run KVM using the created overlay image.

        :param overlayimg: path to qcow2 overlay based on the configured 
           minimal KVM image
        """
        kvm_comm = copy(self.kvmbase)
        filearg = kvm_comm.pop()
        filearg = filearg.replace("@KVMIMAGEFILE@", overlayimg)
        kvm_comm.append(filearg)
        self.kvm_comm = kvm_comm
        self.run(kvm_comm)

    def killkvm(self):
        """Kill the KVM instance launched by the command we recorded"""
        killkvm_comm = copy(self.killkvmbase)
        killkvm_comm.append(" ".join(self.kvm_comm))
        self.run(killkvm_comm)

    def removeoverlay(self, overlayimg):
        if self.is_lvm(overlayimg):
            lvrm_comm = copy(self.lvremove)
            lvrm_comm.append(overlayimg)
            lvrm_comm.extend(copy(self.sudobase))
            self.run(lvrm_comm)
        else:
            os.remove(overlayimg)

    def runmic(self, ssh=False, job_args=None):
        """Run MIC2, using ssh or executing on the host, with arguments.

        :param ssh: wether to use ssh
        :pram job_args: Arguments for MIC2
        """
        mic_comm = copy(self.micbase)
        if self.ict == "mic2":
            mic_comm.append('--format=%s' % job_args.image_type)
            mic_comm.append('--config=%s' % job_args.ksfile_name)
        elif self.ict == "newmic":
            mic_comm.append('%s' % job_args.image_type)
            mic_comm.append('%s' % job_args.ksfile_name)

        mic_comm.append('--arch=%s' % job_args.arch)
        mic_comm.append('--outdir=%s' % job_args.outdir)

        if job_args.image_type == "fs":
            mic_comm.append('--compress-disk-image=tar.bz2')

        if job_args.release:
            mic_comm.append('--release=%s' % job_args.release)
        if job_args.extra_opts:
            for opt in job_args.extra_opts:
                if opt:
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
                            log_filename=self.logfile_name,
                            timeout=int(self.config.timeout))

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

                overlay_suffix = 'overlay-%s-port-%s' % \
                                 (self.job_args.image_id, commands.port)

                overlayimg = commands.overlaycreate(self.config.img_tmp,
                                                    self.config.vm_base_img,
                                                    overlay_suffix)

                commands.runkvm(overlayimg)

                time.sleep(20)

                if self.ict == "mic2":
                    commands.scpto(source='/etc/mic2/mic2.conf',
                                   dest='/etc/mic2/')
                elif self.ict == "newmic":
                    commands.scpto(source='/etc/mic/mic.conf',
                                   dest='/etc/mic/')

                if os.path.exists('/etc/sysconfig/proxy'):
                    commands.scpto(source='/etc/sysconfig/proxy',
                                   dest='/etc/sysconfig/')

                commands.ssh(['mkdir', '-p', self._image_dir])

                commands.scpto(source=ksfile_name,
                               dest=self._image_dir)

                commands.runmic(ssh=True, job_args=self.job_args)

                commands.scpfrom(source="%s*" % self._image_dir,
                                 dest=self._image_dir)

                self.result = True

            except (sub.CalledProcessError, TimeoutError), err:
                print "error %s" % err
                self.error = str(err)
                self.result = False

            finally:

                try:
                    commands.ssh(['poweroff', '-f'])
                except (sub.CalledProcessError, TimeoutError), err:
                    try:
                        print "error %s trying to kill kvm" % err
                        commands.killkvm()
                    except (sub.CalledProcessError, TimeoutError), err:
                        print "error %s" % err
                finally:
                    try:
                        commands.removeoverlay(overlayimg)
                    except (sub.CalledProcessError, TimeoutError), err:
                        print "error %s" % err

        elif not self.config.use_kvm:
            try:

                commands.runmic(ssh=False, job_args=self.job_args)
                self.result = True

            except (sub.CalledProcessError, TimeoutError), err:
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
