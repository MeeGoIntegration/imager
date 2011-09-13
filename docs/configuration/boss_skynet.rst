BOSS / SkyNET
=============

The configuration is done in /etc/skynet/skynet.conf

The main value that needs to be set is the amqp_host and this should
point to the pre-existing BOSS installation.

SkyNET launches participants without any system environment. Some
installations may need to set proxy information. This can be done in:
/etc/skynet/skynet.env

Start and Register
------------------

Once a participant has been installed and configured it should be started and
registered. To see the installed participants do ::

   skynet list

Enable (start) the participant ::

   skynet enable build_image
   skynet enable build_ks

Register the participant to SkyNET ::

   skynet register build_image
   skynet register build_ks

See the SkyNET page for more details.

