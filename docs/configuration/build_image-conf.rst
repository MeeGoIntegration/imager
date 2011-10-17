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

Without KVM
-----------

In order to run the mic2 tool, the img user needs sudo rights to
mic-image-creator ::

 cat >> /etc/sudoers.d/img << EOF
 img ALL=(ALL)NOPASSWD:/usr/bin/mic-image-creator
 EOF
 chmod 0440 /etc/sudoers.d/img

Make sure the sudoers file contains a line that looks like ::

 #includedir /etc/sudoers.d

The # is correct and not an error. Use the visudo command to edit the file
because it validates your changes.

Using KVM
---------

In KVM mode, IMG first creates an overlay image from the base image
(not distributed) and then starts it using the overlay image as the
hard disk. Virtio is used as a speed optimisation method for KVM. When
a specific amount of time has passed, it will copy the kickstart and
mic2 config file to the guest VM. Then it runs mic2 in the VM with
parameters specified in the init method. After mic2 has run, the image
is copied from the guest using scp.

.. attention ::

   The img user is added to the kvm system group so it can launch virtual
   machines without root privileges. This is more secure. The main requirement
   is /dev/kvm should be rw for the img user or a group it belongs to

A suitable KVM image would have 20Gb of diskspace and boots in 20 seconds or
less and can run mic2. It can run any Linux distrobution but it is recommended
to generate a minimal MeeGo VM otherwise mic2 will just create a bootstrap.

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


.. rubric:: Footnotes

.. [#f1] This kickstart works out all the details :

   .. literalinclude:: ../../doc/meego-core-ia32-mint.ks
