#!/usr/bin/python
# Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
# Contact: Ramez Hanna <ramez.hanna@nokia.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""MIC2 mic-image-creator wrapper"""

import os
import pipes
import subprocess as sub
from multiprocessing import Process, TimeoutError
import datetime
from copy import copy
from img.common import getmac, getport, fork, wait_for_vm_up, wait_for_vm_down


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
            if file_.startswith("."):
                continue
            fullpath = os.path.join(path, file_)
            size = int(os.path.getsize(fullpath))
            fmap[fullpath] = size
    items = fmap.items()
    # Map back the items and sort using size, largest will be the last
    backitems = [[v[1], v[0]] for v in items]
    backitems.sort()
    sizesortedlist = [backitems[i][1] for i in range(0, len(backitems))]
    # Its a path, don't worry
    largest_file = sizesortedlist[-1]

    return largest_file


class Commands(object):
    """Commands object for running various image building commands"""

    def __init__(self, vm_kernel, ssh_key=None, log_filename=None,
                 timeout=3600, mic_cachedir=None, mic_outputdir=None,
                 ict="mic"):
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

        self.mac = getmac()

        self._logf = log_filename

        self.timeout = timeout

        self.sudobase = ['sudo', '-n']

        self.killbase = ['pkill', '-f']

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

        self.mountcachebase = [
            'mount', '-t', '9p',
            '-otrans=virtio,version=9p2000.L',
            'mic_cache'
        ]

        self.mountoutputbase = [
            'mount', '-t', '9p',
            '-otrans=virtio,version=9p2000.L',
            'mic_output'
        ]

        self.sopts = [
            '-i%s' % ssh_key,
            '-o', 'ConnectTimeout=60',
            '-o', 'ConnectionAttempts=4',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'LogLevel=quiet',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'PasswordAuthentication=no'
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

        # TODO: detection of qemu version?
        self.kvmbase = [
            '/usr/bin/qemu-system-x86_64',
            '-machine', 'accel=kvm',
            '-display', 'none', '-no-reboot',
            '-daemonize', '-m', '1G',
            '-smp', '2',
            '-device', 'virtio-rng-pci',
            '-kernel', vm_kernel,
            '-append',
            'root=/dev/vda panic=1 quiet rw elevator=noop ip=dhcp',
            '-net', 'nic,model=virtio,macaddr=%s' % self.mac,
            '-net', 'user,hostfwd=tcp:127.0.0.1:%s-:22' % self.port
        ]

        if mic_cachedir:
            self.kvmbase.extend([
                '-device',
                'virtio-9p-pci,id=fs0,fsdev=fsdev0,mount_tag=mic_cache',
                '-fsdev',
                'local,security_model=mapped,id=fsdev0,path=%s' %
                mic_cachedir,
            ])
            self.kvmbase.extend([
                '-device',
                'virtio-9p-pci,id=fs1,fsdev=fsdev1,mount_tag=mic_output',
                '-fsdev',
                'local,security_model=none,id=fsdev1,path=%s' % mic_outputdir,
            ])

        self.kvmbase.extend([
            '-drive',
            'index=0,if=virtio,media=disk,cache=writeback,file=@KVMIMAGEFILE@'
        ])

        self.ict = ict

        if self.ict == "mic2":
            self.micbase = ['mic-image-creator']
        elif self.ict == "mic":
            self.micbase = ['/usr/bin/mic', 'create']
        # could kiwi or debootstrap be supported ? ;)
        else:
            raise RuntimeError("Couldn't find a supported mic tool")

        self.kvm_comm = None

    def run(self, command):
        """Method to run an arbitrary command and pipe the log output to a
        file.

        :param command: Arbitary command to run
        """
        with open(self._logf, 'a+b') as logf:
            logf.write(
                "\n%s : %s\n" % (
                    datetime.datetime.now(), " ".join(command)
                )
            )
            logf.flush()
        proc = Process(target=fork, args=(self._logf, command))
        proc.start()
        proc.join(self.timeout)
        if proc.is_alive():
            with open(self._logf, 'a+b') as logf:
                logf.write(
                    "\n%s : Command still running after %s seconds" % (
                        datetime.datetime.now(), self.timeout
                    )
                )
                logf.flush()

            kill_comm = copy(self.killbase)
            kill_comm.append(" ".join(command))
            self.run(kill_comm)
            proc.terminate()
            proc.join(self.timeout)

            raise TimeoutError(
                "Command was still running after %s seconds" % self.timeout
            )
        elif not proc.exitcode == 0:
            raise sub.CalledProcessError(
                int(proc.exitcode),
                "Command returned non 0 exit code %s" % proc.exitcode
            )

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

    def ssh(self, command):
        """Execute an arbitrary command in the KVM guest.

        :param command: Arbitary command to run over ssh inside kvm
        """
        ssh_comm = copy(self.sshbase)
        ssh_comm.extend(self.sopts)
        ssh_comm.extend([pipes.quote(arg) for arg in command])
        self.run(ssh_comm)

    def is_lvm(self, img):
        """Returns true if a file is recognized by lvdisplay as an LV

        :param img: path to file to be checked
        :returns: True if the file is an lvm logical volume, False otherwise
        """

        # lvdisplay returns 0 when run against stuff not in /dev.
        # It's not a problem even for /dev/shm/ qcow2 overlays, since
        # for non-LVs in /dev/, lvdisplay returns error 5.
        #
        # This makes sure that qcow2 images in /var won't be considered LVs.
        if not img.startswith("/dev/"):
            return False

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
        overlay_img = None
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
        killkvm_comm = copy(self.killbase)
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

    def mount_mic_cache(self, mic_cachedir):
        self.ssh(['mkdir', '-p', mic_cachedir])
        mount_comm = copy(self.mountcachebase)
        mount_comm.append(mic_cachedir)
        self.ssh(mount_comm)

    def mount_mic_output(self, mic_9p_outputdir):
        self.ssh(['mkdir', '-p', mic_9p_outputdir])
        mount_comm = copy(self.mountoutputbase)
        mount_comm.append(mic_9p_outputdir)
        self.ssh(mount_comm)

    def runmic(self, ssh=False, job_args=None):
        """Run MIC2, using ssh or executing on the host, with arguments.

        :param ssh: wether to use ssh
        :pram job_args: Arguments for MIC2
        """
        mic_comm = []
        mic_comm.extend(copy(self.micbase))

        if self.ict == "mic2":
            mic_comm.append('--format=%s' % job_args.image_type)
            mic_comm.append('--config=%s' % job_args.ksfile_name)
        elif self.ict == "mic":
            mic_comm.append('%s' % job_args.image_type)
            mic_comm.append('%s' % job_args.ksfile_name)

        mic_comm.append('--arch=%s' % job_args.arch)
        mic_comm.append('--outdir=%s' % job_args.outdir)

        if job_args.tokenmap:
            mic_comm.append('--tokenmap=%s' % job_args.tokenmap)
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
        :param job_args: hash proxy object describing the image job_args
        """
        self.config = config

        image_id = job_args.image_id
        self.image_id = "".join(
            c for c in image_id if c.isalnum() or c in ['_', '-']
        ).rstrip()

        self._image_dir = os.path.join(
            config.base_dir, job_args.prefix, self.image_id
        )

        self._image_dir = "%s/" % self._image_dir

        job_args.outdir = self._image_dir

        self.logfile_name = os.path.join(
            self._image_dir, "%s.log" % job_args.name
        )
        self.logfile_url = self.logfile_name.replace(
            self.config.base_dir, self.config.base_url
        )
        self.files_url = "%s/%s/%s" % (
            config.base_url, job_args.prefix, self.image_id
        )

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

        mic_cachedir = None
        if self.config.use_kvm and self.config.use_9p_cache:
            mic_cachedir = self.config.mic_cachedir
            if "SUPERVISOR_ENABLED" in os.environ:
                mic_cachedir = os.path.join(
                    mic_cachedir, os.environ["SUPERVISOR_PROCESS_NAME"]
                )
                try:
                    os.mkdir(mic_cachedir)
                except OSError as e:
                    print(e)

        commands = Commands(
            self.config.vm_kernel,
            ssh_key=self.config.vm_ssh_key,
            log_filename=self.logfile_name,
            timeout=int(self.config.timeout),
            mic_cachedir=mic_cachedir,
            mic_outputdir=self._image_dir,
            ict=self.config.ict
        )

        print(self._image_dir)
        try:
            os.makedirs(self._image_dir, 0o775)
        except OSError as e:
            if e.errno == 17:
                pass

        ksfile_name = os.path.join(
            self._image_dir, "%s.ks" % self.job_args.name
        )

        with open(ksfile_name, mode='w+b') as ksfile:
            ksfile.write(self.job_args.kickstart)
        os.chmod(ksfile_name, 0o644)

        self.job_args.ksfile_name = ksfile_name

        if self.config.use_kvm:

            if not os.path.exists('/dev/kvm'):
                self.error = "/dev/kvm does not exist or I am not allowed to "\
                    "access it. Is the appropriate kvm module loaded? "\
                    "Is img user in kvm group?"
                self.result = False
            elif not os.path.exists(self.config.vm_base_img):
                self.error = (
                    "%s does not exist or I am not allowed to access it. "
                    "Is img user in the disk group?" % self.config.vm_base_img
                )
                self.result = False
            else:
                try:
                    overlay_suffix = 'overlay-%s-port-%s' % (
                        self.image_id, commands.port
                    )

                    overlayimg = commands.overlaycreate(
                        self.config.img_tmp,
                        self.config.vm_base_img,
                        overlay_suffix,
                    )
                    if not overlayimg:
                        self.error = "Setting up the overlay image failed. "\
                            "Is img in the disk group for lvm? "\
                            "Is qemu-img working for qcow2?"
                        self.result = False
                    else:

                        commands.runkvm(overlayimg)

                        wait_for_vm_up(
                            '127.0.0.1', commands.port, self.config.vm_wait
                        )

                        if (
                            commands.ict == "mic2" and
                            os.path.exists('/etc/mic2/mic2.conf')
                        ):
                            commands.scpto(
                                source='/etc/mic2/mic2.conf',
                                dest='/etc/mic2/',
                            )
                        elif (
                            commands.ict == "mic" and
                            os.path.exists('/etc/mic/mic.conf')
                        ):
                            commands.scpto(
                                source='/etc/mic/mic.conf',
                                dest='/etc/mic/',
                            )
                        else:
                            print(
                                "WARNING! no mic conf file found, "
                                "please create one if needed."
                            )

                        if os.path.exists('/etc/sysconfig/proxy'):
                            commands.scpto(
                                source='/etc/sysconfig/proxy',
                                dest='/etc/sysconfig/',
                            )

                        if os.path.exists('/etc/resolv.conf'):
                            commands.scpto(
                                source='/etc/resolv.conf',
                                dest='/etc/',
                            )

                        if os.path.exists('/usr/bin/img_vm_shutdown'):
                            commands.scpto(
                                source='/usr/bin/img_vm_shutdown',
                                dest='/tmp/die',
                            )
                            commands.ssh(['chmod', '+x', '/tmp/die'])

                        commands.ssh(['mkdir', '-p', self._image_dir])

                        commands.scpto(
                            source=ksfile_name,
                            dest=self._image_dir,
                        )

                        if mic_cachedir:
                            commands.mount_mic_cache(
                                os.path.dirname(mic_cachedir)
                            )
                            commands.mount_mic_output(self._image_dir)

                        commands.runmic(ssh=True, job_args=self.job_args)

                        if not mic_cachedir:
                            commands.scpfrom(
                                source="%s*" % self._image_dir,
                                dest=self._image_dir,
                            )

                        commands.run(
                            ['chmod', '-R', 'g+rw,o+rw', self._image_dir]
                        )

                        self.success()
                        self.result = True

                except (sub.CalledProcessError, TimeoutError) as err:
                    print("error %s" % err)
                    self.error = str(err)
                    self.result = False

                finally:

                    try:
                        commands.ssh(['sync'])
                        if os.path.exists('/usr/bin/img_vm_shutdown'):
                            commands.ssh(['/tmp/die'])
                        else:
                            commands.ssh(['/sbin/shutdown', 'now'])

                        wait_for_vm_down(
                            commands.kvm_comm, self.config.vm_wait
                        )

                    except (
                        sub.CalledProcessError,
                        TimeoutError,
                        RuntimeError,
                    ) as err:
                        try:
                            print("error %s trying to kill kvm" % err)
                            commands.killkvm()
                        except (
                            sub.CalledProcessError,
                            TimeoutError,
                        ) as err:
                            print("error %s" % err)
                    finally:
                        if overlayimg:
                            try:
                                commands.removeoverlay(overlayimg)
                            except (
                                sub.CalledProcessError,
                                TimeoutError,
                            ) as err:
                                print("error %s" % err)

        elif not self.config.use_kvm:
            try:
                if (
                    commands.ict == "mic2" and
                    not os.path.exists("/usr/bin/mic-image-creator")
                ):
                    self.error = "/usr/bin/mic-image-creator does not exist"
                    self.result = False
                elif (
                    commands.ict == "mic" and
                    not os.path.exists("/usr/bin/mic")
                ):
                    self.error = "/usr/bin/mic does not exist"
                    self.result = False

                commands.runmic(ssh=False, job_args=self.job_args)
                self.success()
                self.result = True

            except (sub.CalledProcessError, TimeoutError) as err:
                print("error %s" % err)
                self.error = str(err)
                self.result = False

    def success(self):
        self.image_file = find_largest_file(self._image_dir)
        self.image_url = self.image_file.replace(
            self.config.base_dir, self.config.base_url
        )

    def get_results(self):
        """Returns the results in a dictionary.

        :returns: results dictionary
        """
        return {
            "result": self.result,
            "files_url": self.files_url,
            "image_url": self.image_url,
            "logfile_url": self.logfile_url,
            "error": self.error
        }
