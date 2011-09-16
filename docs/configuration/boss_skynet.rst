BOSS / SkyNET
=============

The configuration is done in /etc/skynet/skynet.conf

The main value that needs to be set is the amqp_host and this should
point to the pre-existing BOSS installation.

SkyNET launches participants without any system environment. Some
installations may need to set proxy information. This can be done in:
/etc/skynet/skynet.env
