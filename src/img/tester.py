#!/usr/bin/python
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

import os, sys
import hashlib
import subprocess as sub
from multiprocessing import Process, TimeoutError
import time, datetime
import random
from copy import copy
import pycurl

# We should ignore SIGPIPE when using pycurl.NOSIGNAL - see
# the libcurl tutorial for more info.
#try:
#    import signal
#    from signal import SIGPIPE, SIG_IGN
#    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
#except ImportError:
#    pass

from img.common import getport, fork

class Commands(object):
    """Commands object for running various image building commands"""

    def __init__(self, logfn=None,
                 vgname=None, ssh_key=None,
                 timeout=3600, vm_kernel=None, device_ip="127.0.0.1"):
        """Constructor, creates the object with necessary parameters to run 
        commands
        
        :param log_filename: Filename to pipe the output to.
        :param timeout: integer value used to set an alarm signal that
           interrupts any command that runs for too long

        """
        self.port = getport()

        self._logf = logfn

        self.timeout = timeout

        self.vgname = vgname

        self.device_ip = device_ip

        self.sudobase = [
                     'sudo', '-n'
                   ]

        self.killkvmbase = [
                     'pkill', '-f'
                   ]

        self.mkfsbase = [ 'mkfs', '-t' ]

        self.overlaybase = [
                        '/usr/bin/qemu-img', 'create', '-f', 'qcow2', '-b'
                      ]

        self.lvcreate = [
                        '/sbin/lvcreate', '-L', '10G', '-n'
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
                  '-o', 'ConnectionAttempts=60',
                  '-o', 'UserKnownHostsFile=/dev/null',
                  '-o', 'StrictHostKeyChecking=no',
                  '-o', 'PasswordAuthentication=no'
                ]

        self.sshbase = [ 
                    '/usr/bin/ssh', 
                    '-p%s' % self.port,
                    self.device_ip
                  ]

        self.scpbase = [ 
                    '/usr/bin/scp',
                    '-P%s' % self.port,
                    '-r'
                  ]

        self.kvmbase = [
                    '/usr/bin/qemu-kvm',
                    '-nographic', '-no-reboot',
                    '-daemonize', '-m', '1G',
                    '-kernel', vm_kernel,
                    '-append',
                    'root=/dev/vda panic=1 quiet rw elevator=noop ip=dhcp',
                    '-net', 'nic,model=virtio',
                    '-net', 'user,hostfwd=tcp:%s:%s-:22' % (self.device_ip, self.port)
                ]

        self.kvmbase.extend([
                    '-drive', 'index=0,if=virtio,media=disk,cache=writeback,' \
                              'file=@KVMIMAGEFILE@'
                  ])

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
        scp_comm.append("root@%s:%s" % (self.device_ip, dest))
        self.run(scp_comm)

    def scpfrom(self, source="", dest=""):
        """Generic ssh copy file method, from host to KVM.

        :param source: file to copy
        :param dest: destination file to copy to
        """
        scp_comm = copy(self.scpbase)
        scp_comm.extend(self.sopts)
        scp_comm.append("root@%s:%s" % (self.device_ip, source))
        scp_comm.append(dest)
        self.run(scp_comm)

    def ssh(self, command, user="root", ignore_error=False):
        """Execute an arbitrary command in the KVM guest.
        
        :param command: Arbitary command to run over ssh inside kvm
        """
        ssh_comm = copy(self.sshbase)
        ssh_comm.extend(["-l%s" % user])
        ssh_comm.extend(self.sopts)
        ssh_comm.extend(command)
        try:
            self.run(ssh_comm)
        except sub.CalledProcessError:
            if ignore_error:
                pass
            else:
                raise

    def is_lvm(self, img):
        """Returns true if a file is recognized by lvdisplay as an LV

        :param img: path to file to be checked
        :returns: True if the file is an lvm logical volume, False otherwise
        """
        lvd_comm = copy(self.sudobase)
        lvd_comm.extend(copy(self.lvdisplay))
        lvd_comm.append(img)
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
            overlay_comm = copy(self.sudobase)
            overlay_comm.extend(copy(self.lvmsnapshot))
            overlay_comm.extend([copy(overlay_img), baseimg])
            overlay_img = os.path.join(os.path.dirname(baseimg), overlay_img)
        else:
            overlay_img = os.path.join(overlay_img_tmp, overlay_suffix)
            overlay_comm = copy(self.overlaybase)
            overlay_comm.extend([baseimg, overlay_img])
        self.run(overlay_comm)
        return overlay_img

    def mklv(self, lvname):
        """Create an lv.
        
        :param lvname: name of lv to create

        :returns: path to the new created lv
        """
        lvcreate_comm = copy(self.sudobase)
        lvcreate_comm.extend(copy(self.lvcreate))
        lvcreate_comm.extend([lvname, self.vgname])
        self.run(lvcreate_comm)
        return "/dev/%s/%s" % (self.vgname, lvname)

    def mkfs(self, partition, fstype):
        mkfs_comm = copy(self.sudobase)
        mkfs_comm.extend(copy(self.mkfsbase))
        mkfs_comm.extend([fstype, partition])
        self.run(mkfs_comm)
        
    def mount(self, target, partition):
        mount_comm = copy(self.sudobase)
        mount_comm.extend(["/bin/mount", partition, target])
        print mount_comm
        self.run(mount_comm)

    def umount(self, partition):
        umount_comm = copy(self.sudobase)
        umount_comm.extend(["/bin/umount", partition])
        self.run(umount_comm)
        return

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
        """Remove a temporary KVM overlay; can either be an LV snapshot
        or qcow2 overlay
        """
        if self.is_lvm(overlayimg):
            lvrm_comm = copy(self.sudobase)
            lvrm_comm.extend(copy(self.lvremove))
            lvrm_comm.append(overlayimg)
            self.run(lvrm_comm)
        else:
            os.remove(overlayimg)

    def download_extract(self, url, xdir):
        print url
        print xdir
        unc = None
        if url.endswith("gz"):
            unc = "z"
        elif url.endswith("bz2"):
            unc = "j"
        else:
            raise RuntimeError("unsupported compression in url")

        cmd = ['sudo', '-n', '/bin/tar', '-p', '--numeric-owner', '-C', xdir, '-%sx' % unc]
        tarpipe = sub.Popen(cmd, stdin=sub.PIPE)
        
        try:
            c = pycurl.Curl()
            c.setopt(pycurl.FOLLOWLOCATION, 1)
            c.setopt(pycurl.MAXREDIRS, 5)
            c.setopt(pycurl.CONNECTTIMEOUT, 30)
            c.setopt(pycurl.TIMEOUT, 300)
            c.setopt(pycurl.NOSIGNAL, 1)
            c.setopt(pycurl.SSL_VERIFYPEER, 0)
            c.setopt(pycurl.SSL_VERIFYHOST, 0)
            c.fp = tarpipe.stdin
            c.setopt(pycurl.URL, url)
            c.setopt(pycurl.WRITEDATA, c.fp)
            c.filename = os.path.basename(url)
            c.url = url

            result = False
            c.perform()
            httpcode = c.getinfo(pycurl.HTTP_CODE)
        except pycurl.error, err:
            print "Failed: ", err
            result = False
        else:
            if httpcode == 200:
                print "Success:", c.filename, c.url, c.getinfo(pycurl.EFFECTIVE_URL)
                result = True
            else:
                print "Failed: ", c.filename, c.url
                result = False
        finally:
            c.fp.close()
            c.fp = None
            tarpipe.poll()
            if not tarpipe.returncode:
                tarpipe.wait()

        return result

class ImageTester(object):
    """Tester class that does vm based testing"""

    def __init__(self, config=None, job_args=None, test_packages={}):
        """Initialize the tester using a config and job args.

        :param config: Worker config in a hash proxy object
        :param job_args: hash proxy object describing the image job 
        
        """

        self.result = False
        self.testtools_repourl = config["testtools_repourl"]
        self.test_script = config["test_script"]
        self.test_user = config["test_user"]
        self.test_packages = test_packages
        self.vm_pub_ssh_key = config["vm_pub_ssh_key"]
        self.vm_wait =  config["vm_wait"]

        if not "outdir" in job_args:
            job_args["outdir"] = os.path.join(config["base_dir"], job_args["prefix"],
                                              job_args["image_id"])

        self.results_dir = os.path.join(job_args["outdir"], "results")

        self.results_url = "%s/%s" % (job_args["files_url"], "results")

        self.logfile_name = os.path.join(job_args["outdir"],
                                         "%s.log" % job_args["name"])

        # If a base image is provided we will create a snapshot of it
        # and upgrade it using zypper
        self.img_url = None 
        self.base_img = None

        if config["use_base_img"] and job_args.get("use_upgrade", None):
            self.base_img = config["vm_base_img"]
            self.kernel = config["vm_kernel"]
            self.repos = job_args["repos"]

        # Otherwise a new image will be downloaded and used everytime
        else:
            self.img_url = job_args["image_url"]
            self.img_file = os.path.join(job_args["outdir"], os.path.basename(job_args["image_url"]))
            self.img_type = job_args["image_type"] 

        print self.logfile_name
        #setup commands object
        self.commands = Commands(logfn=self.logfile_name,
                                 vgname=config["vg_name"],
                                 timeout=int(config["timeout"]),
                                 ssh_key=config["vm_priv_ssh_key"],
                                 vm_kernel=config["vm_kernel"],
                                 device_ip=config["device_ip"]
                                 )
    def create_vm(self):
        #snapshot base_img if any
        if self.base_img:
            #create snapshot
            raise RuntimeError("upgrade based testing not yet supported")
        else:
            if self.img_type == "fs":
                print "create empty lvm"
                lvname = self.commands.mklv(hashlib.md5(self.img_url).hexdigest())
                self.vmdisk = lvname
                print lvname
                print "format partition"
                self.commands.mkfs(lvname, "ext3")
                print "formatting done"
                try:
                    target = "/var/tmp/%s" % os.path.basename(lvname)
                    print target
                    os.mkdir(target)
                    print "mount"
                    self.commands.mount(target, lvname)
                    print "download image and extract it"
                    count = 1
                    result = False
                    while count < 3 and not result:
                        print self.img_url
                        print target
                        result = self.commands.download_extract(str(self.img_url), str(target))
                        count = count + 1
                    #copy auth ssh key
                    self.commands.run(['sudo', '-n', 'mkdir', '-p', "%s/root/.ssh/" % target])
                    self.commands.run(['sudo', '-n', 'cp', self.vm_pub_ssh_key, "%s/root/.ssh/authorized_keys" % target])
                    self.commands.run(['sudo', '-n', 'chown', '-R', 'root:root', "%s/root/.ssh/" % target])
                    self.commands.run(['sudo', '-n', 'chmod', '-R', 'o+rwx,g-rwx,o-rwx', "%s/root/.ssh/" % target])

                finally:
                    try:
                        print "umount"
                        self.commands.umount(lvname)
                    finally:
                        print "rmdir"
                        os.rmdir(target)
            else:
                raise RuntimeError("unspported image type %s" % self.img_type)

        if not self.vmdisk:
            raise RuntimeError("something went wrong while setting up vm disk")
    
    def boot_vm(self):

        print "runkvm"
        self.commands.runkvm(self.vmdisk)
        self.kvm_run = True

    def wait_for_vm(self):

        print "vm_wait"
        time.sleep(int(self.vm_wait))

        print "copying /etc/sysconfig/proxy"
        if os.path.exists('/etc/sysconfig/proxy'):
            self.commands.scpto(source='/etc/sysconfig/proxy',
                           dest='/etc/sysconfig/')

        print "copying /etc/resolv.conf"
        if os.path.exists('/etc/resolv.conf'):
            self.commands.scpto(source='/etc/resolv.conf',
                           dest='/etc/')

    def upgrade_vm(self):

        if self.base_img:
            #add repos from workitem
            #upgrade
            raise RuntimeError("upgrade based testing not yet supported")

    def install_tests(self):
        if self.test_packages:
            print "adding test repo"
            addrepo_comm = ['zypper', '-n', 'ar', '-f', '-G']
            addrepo_comm.extend([self.testtools_repourl])
            self.commands.ssh(addrepo_comm)
            packages = []
            patterns = []
            for name in self.test_packages.keys():
                if name.startswith('@'):
                    patterns.append(name[1:])
                else:
                    packages.append(name)
            if packages:
                print "installing test packages"
                install_comm = ['zypper', 'in', '-y', '-f', '--force-resolution']
                install_comm.extend(packages)
                self.commands.ssh(install_comm)
            if patterns:
                print "installing test patterns"
                install_comm = ['zypper', 'in', '-y', '-f', '--force-resolution', '-t', 'pattern']
                install_comm.extend(patterns)
                self.commands.ssh(install_comm)

    def run_tests(self):

        self.commands.run(['mkdir', '-p', self.results_dir])

        print "inserting test script"
        self.commands.scpto(self.test_script, '/var/tmp/test_script.sh') 
        
        self.commands.ssh(['chmod', '+x', '/var/tmp/test_script.sh'])
        try:
            print "running test script"
            test_comm = ['/var/tmp/test_script.sh']
            test_comm.extend(self.test_packages.keys())
            self.commands.ssh(test_comm, user=self.test_user)
        except:
            raise
        finally:
            try:
                print "trying to get any test results"
                self.commands.scpfrom("/tmp/results/*.xml", self.results_dir)
            except:
                pass

    def cleanup(self):

        try:
            if self.kvm_run:
                self.commands.ssh(['sync'])
                time.sleep(int(self.vm_wait))
                self.commands.ssh(['shutdown', 'now'], ignore_error=True)
        except (sub.CalledProcessError, TimeoutError), err:
            try:
                if self.kvm_run:
                    print "error %s trying to kill kvm" % err
                    self.commands.killkvm()
            except (sub.CalledProcessError, TimeoutError), err:
                print "error %s" % err
        finally:
            try:
                self.commands.removeoverlay(self.vmdisk)
            except (sub.CalledProcessError, TimeoutError), err:
                print "error %s" % err

    def test(self):
        """Test the image"""
        self.vmdisk = None
        self.kvm_run = False
        try:

            self.create_vm()

            self.boot_vm()

            self.wait_for_vm()

            self.upgrade_vm()

            self.install_tests()

            self.run_tests()

            self.result = True

        except (sub.CalledProcessError, TimeoutError), err:
            print "error %s" % err
            self.error = str(err)
            self.result = False
        
        finally:
            self.cleanup()

    def get_results(self):
        """Returns the results in a dictionary.

        :returns: results dictionary
        """
        results = {
                    "result"     : self.result,
                    "results_dir": self.results_dir,
                    "results_url": self.results_url
                  }

        return results
