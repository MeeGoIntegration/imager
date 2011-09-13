build_ks participant configuration
==================================

This participant validates and manipulates the kickstart file. Eg when
extra repositories and packages are added to a ks this participant
manages that. Usually only one of these needs to be running.

To configure, edit /etc/skynet/build_ks.conf

.. literalinclude:: ../../src/img_boss/build_ks.conf


Set '''reposerver''' to point to the OBS http repository server (the
user-facing download server, not the backend bs_reposrv system).

Set '''ksstore''' to point to the location that will hold the
default kickstart files.
