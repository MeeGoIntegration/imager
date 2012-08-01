test_vm_image participant configuration 
=======================================

This is a simple VM based QA worker. Instances can be installed
on multiple systems connected to the same IMG/BOSS instance. It 
will use create KVM and run tests inside it.

This is the defalt configuration in /etc/skynet/test_vm_image.conf 

.. literalinclude:: ../../src/img_boss/test_vm_image.conf

The two important configuration options are base_url and base_dir:

* base_dir points at the place where the test results will be saved to.
* base_url sets the URL at which base_dir is served using HTTP. This can
  either be from the worker itself or a central location where base_dir is 
  shared to using NFS.

.. attention ::
   Instructions on setting up the NFS sharing are beyond the scope of this
   documentation

Supported testing tools
-----------------------

The testing script included will use rpm to find all packages that contain
a tests.xml file and then uses testrunner-lite to execute those tests.

QA requirements
---------------

Being rather simple, the QA only supports i586 rootfs images.
