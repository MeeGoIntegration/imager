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

   install -d -m 0777 /var/www/img/images

Using sudo
----------

In order to run the mic2 tool, the img user needs sudo rights to
mic-image-creator ::

 cat >> /etc/sudoers.d/img << EOF
 img ALL=(ALL)NOPASSWD:/usr/bin/mic-image-creator
 EOF
 chmod 0440 /etc/sudoers.d/nobody

Using KVM
---------

In KVM mode, IMG first creates an overlay image from the base image
(not distributed) and then starts it using the overlay image as the
hard disk. Virtio is used as a speed optimisation method for KVM. When
a specific amount of time has passed, it will copy the kickstart and
mic2 config file to the guest VM. Then it runs mic2 in the VM with
parameters specified in the init method. After mic2 has run, the image
is copied from the guest using scp.

TBD: KVM setup

