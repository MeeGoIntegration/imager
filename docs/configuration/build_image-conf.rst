build_image participant configuration 
=====================================

This is the actual image building worker. Instances can be installed
on multiple systems connected to the same IMG/BOSS instance. Depending
on its configuration it will either use sudo to launch mic2 or boot a
kvm image and run mic2 inside that.

This is the defalt configuration in /etc/skynet/build_image.conf 

.. literalinclude:: ../../src/img_boss/build_image.conf

The two important configuration options are base_url and base_dir:

* base_dir points at the place where the images will be saved to.
* base_url sets the URL at which base_dir is served using HTTP. This can
  either be from the worker itself or a central location where base_dir is 
  shared to using NFS.

.. attention ::
   Instructions on setting up the NFS sharing are beyond the scope of this
   documentation

You also need to create the directory you set as the value of base_dir ::

   install -o img -g www-data -d -m 0777 /var/www/images

Supported image creation tools
------------------------------

Imager was originally created as a service wrapper around "mic2" the MeeGo image
creation tool. Later a newer version "mic" was released in association with Tizen.
mic is also being used for Mer which is the current focus of MINT tools.

Both are supported, and at runtime if mic2 (mic-image-creator) is found it is used.
If not, then mic (mic create) is used.

Without KVM
-----------

In order to run the mic2 tool, the img user needs sudo rights to
mic-image-creator ::

 cat >> /etc/sudoers.d/img << EOF
 img ALL=(ALL)NOPASSWD:/usr/bin/mic-image-creator
 EOF
 chmod 0440 /etc/sudoers.d/img

In case you are using the new mic tool, then the sudo rights would look like
this ::

 cat >> /etc/sudoers.d/img << EOF
 img ALL=(ALL)NOPASSWD:/usr/bin/mic
 EOF
 chmod 0440 /etc/sudoers.d/img

Make sure the sudoers file contains a line that looks like ::

 #includedir /etc/sudoers.d

The # is correct and not an error. Use the visudo command to edit the file
because it validates your changes.

On Debian and openSuse in this mode mic2 will usually create a bootstrap rootfs
on first run, using packages grabbed from the "mainrepo" deduced from the kickstart
being built. If the mainrepo does not contain the needed packages (as is the case 
with minimal Mer core) it will fail. A needed workaround is to manually create
the initial bootstrap. The instructions on how to do that for Mer (non-meego distro) can be found here :
http://wiki.merproject.org/wiki/Image_Creation_For_Beginners

The new mic tool seems to be able to run natively without bootstrap, however it can be
configured to do so by adding "runtime= bootstrap" to the create section of /etc/mic/mic.conf
and configuring the appropriate bootstrap section with the repositories that contain the needed packages.
(zypper package manager will be used here regardless of any configurations to use yum)

Extra configurations can be added to /etc/mic2/mic2.conf or /etc/mic/mic.conf
depending on which version you installed. Useful configurations to know about :

* "pkgmgr = yum" : when zypper appears to be buggy for some use cases, switching to yum can get you going.

Using KVM
---------

In KVM mode, IMG first creates an overlay image from the base image
(not distributed) and then starts it using the overlay image as the
hard disk. Virtio is used as a speed optimisation method for KVM. When
a specific amount of time has passed, it will copy the kickstart and
mic config file to the guest VM. Then it runs mic in the VM with
parameters specified in the init method. After mic has run, the image
is copied from the guest using scp.

.. attention ::

   The img user is added to the kvm system group (on Debian) so it can launch virtual
   machines without root privileges. This is more secure. The main requirement
   is /dev/kvm should be rw for the img user or a group it belongs to

.. attention ::

   The img user is added to the disk system group (on Debian) so that the KVM vm can use the 
   created LV nodes without root privileges. This is more secure. The main requirement
   is /dev/dm-* should be rw for the img user or a group it belongs to

A suitable KVM image would have 20Gb of disk space and boots in 20 seconds or
less and can run mic. It can run any Linux distribution but it is recommended
to generate a minimal MeeGo VM otherwise mic2 will just create a bootstrap.

IMG can also use an lvm LV as root disk for the KVM vm. For this to work vm_base_img should point to the
base LV that contains the minimal rootfs discussed earlier. Next allow img to run the following three
privileged commands ::

 cat >> /etc/sudoers.d/img << EOF
 img ALL=(ALL)NOPASSWD:/sbin/lvdisplay
 img ALL=(ALL)NOPASSWD:/sbin/lvcreate
 img ALL=(ALL)NOPASSWD:/sbin/lvremove
 EOF
 chmod 0440 /etc/sudoers.d/img

For every job run IMG will create a 1:1 snapshot of the base LV and use it to build the requested image.
Then the snapshot is discarded. Thus it requires the following resources :

* base LV or image big enough to create the biggest image you anticipate ex: 20Gb
* 1 processor for each worker
* 256M RAM for each worker
* 20Gb free space in the volume group that contains the base LV for each worker or in the partition 
  that will hold the temporary overlays.

If you run 4 workers the calculation becomes : 4 processors, 1Gb RAM, 100Gb disk space.

.. attention ::

   A new experimental feature has been introduced in 0.63.0 which allows sharing a cache directory among IMG KVM workers
   on the same machine. This can greatly improve the speed and efficiency of image creation, but is not thoroughly tested
   yet. The guest VM kernel needs to be at least 2.6.37 and include support for 9p virtio. More reading at :
   http://wiki.qemu.org/Documentation/9psetup

Generating the KVM image
------------------------

There are two ways to get this working :
* Old: mic2 + MeeGo + qcow2
* New: mic + Mer + LVM

Mic2 and MeeGo and qcow2
^^^^^^^^^^^^^^^^^^^^^^^^

The following commands were tested on a Debian testing host that has recent mic2
and qemu installed.

* Generate a loop file using mic2 and the included kickstart at [#f1]_ ::

   sudo -n mic-image-creator --config=meego-core-ia32-mint.ks --format=loop --arch=i586 --outdir=./mint/ --save-kernel --suffix=""

* Expand the loop file to 20Gb ::

   dd if=/dev/zero of=./mint/<name of image> bs=1M count=1 seek=20480

* Resize the filesystem inside the loop file ::

   fsck.ext3 -f ./mint/*.img
   resize2fs ./mint/*.img
   fsck.ext3 -f ./mint/*.img
   tune2fs -c 0 -i 0 ./mint/*.img

* Convert it to qcow2 format ::

   qemu-img convert -p -O qcow2 -o preallocation=off ./mint/*.img ./mint/meego-core-ia32-mint.qcow2

* Open the mic2 log and look for lines that look like ::

   **********************************
   SSH private key for this image

And paste the ssh key to a file

* Move the ssh key, qcow2 file and kernel vmlinuz files to somewhere like 
  /home/img/ on the worker machine and make sure they are readable by the img
  user ::

   chown img:imgadm /home/img/*
   chmod 0600 /home/img/id_rsa
   chmod 0770 /home/img/meego-core-ia32-mint.qcow2 /home/img/vmlinuz

* Set the files' locations in /etc/skynet/build_image.conf

Mic and Mer and LVM
^^^^^^^^^^^^^^^^^^^

The following commands were tested on a Debian testing host that has recent mic installation.

* Generate a tarball file using mic and the included kickstart at [#f2]_ ::

   mic create fs mer-core-i586-vm.ks --arch=i686 --outdir=./mint/ --compress-disk-image=tar.bz2

* Create 20Gb LV (replace vg with your volume group name) ::

   lvcreate -L 20G -n img_base vg

* Creat filesystem on the LV (replace vg with your volume group name) ::

   mkfs.ext4 /dev/vg/img_base
   tune2fs -c 0 -i 0 /dev/vg/img_base

* Mount it and untar the rootfs on the LV and copy the needed files 
  and setup ssh access ::

   mkdir /tmp/img_base
   mount /dev/vg/img_base /tmp/img_base
   tar -C /tmp/img_base ./mint/*.tar.bz2
   cp -L /tmp/img_base/boot/vmlinuz /home/img/vmlinuz

   mkdir -p -m 0700 /tmp/img_base/root/.ssh
   ssh-keygen -q -C "img vm" -t rsa -f /root/.ssh/id_rsa -N ''
   cp /tmp/img_base/root/.ssh/id_rsa.pub /tmp/img_base/root/.ssh/authorized_keys
   cp /tmp/img_base/root/.ssh/id_rsa /home/img/id_rsa

   chown img:imgadm /home/img/*
   chmod 0600 /home/img/id_rsa

   umount /tmp/img_base

* Set the various files' locations in /etc/skynet/build_image.conf

.. rubric:: Footnotes

.. [#f1] This kickstart works out all the details :

   .. literalinclude:: ../../doc/meego-core-ia32-mint.ks

.. [#f2] Mer VM SDK rootfs kickstart :

   .. literalinclude:: ../../doc/mer-core-i586-sdkvm.ks
