BOSS / SkyNET
=============

Shared configuration is done in /etc/skynet/skynet.conf. If you use
more than one (virtual) machine for Web UI and imager worker(s) this
configuration is required in all machines.

The main value that needs to be set is the amqp_host and this should
point to the pre-existing BOSS installation. However, if you are doing a single
system installation ( aka appliance ) then the defaults should be fine.

SkyNET launches participants without any system environment. Some
installations may need to set proxy information. This can be done in:
/etc/skynet/skynet.env

All programs are spawned and monitored by supervisor. For more information
about supervisor check : http://supervisord.org

skynet is a wrapper that tries make it easy to handle the system. Check 
skynet --help for a list of available commands.

To check the status of participants use the command::

 skynet status

To tail -f the log messages of a participant, for example img_web::

 skynet log img_web

All of them at once::

 skynet log --all

Participant Registry
--------------------
To register all the participants so that they can talk to each other over
ruote AMQP, issue the following command::

 skynet register --all

If you have installed to several machines, you need  to issue the command
on each one.

Troubleshooting and Debugging
-----------------------------

If you face issues with the ruote AMQP system, or if you are just curious about
the inner workings you can try out boss viewer. It can be installed using::

 apt-get install boss-viewer

or::

 zypper in boss-viewer

After installation check that it is RUNNING in skynet status and browse to :
http://127.0.0.1:9292/_ruote/
