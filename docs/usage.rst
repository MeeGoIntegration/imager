Usage
*****

Start the needed services on their respective machines.

Worker ::

   skynet enable build_image

Web UI ::

   service lighttpd start
   service img_web start
   skynet enable request_image
   skynet enable update_image_status
   skynet enable build_ks


Making lighttpd and img_web system services start by default on boot is a
sysadmin task and is distribution specific.

You should now be able to access the web interface and admin at ::

   http://$IP-address/img/
   http://$IP-address/img/admin/


