BOSS / SkyNET
=============

The configuration is done in /etc/skynet/skynet.conf. If you use more than
one (virtual) machine for Web UI and imager worker(s) this
configuration is required in all machines.


The main value that needs to be set is the amqp_host and this should
point to the pre-existing BOSS installation.

SkyNET launches participants without any system environment. Some
installations may need to set proxy information. This can be done in:
/etc/skynet/skynet.env
