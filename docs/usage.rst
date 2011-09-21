Usage
*****

Once a participant has been installed and configured it should be started and
registered. To see the installed participants do ::

   skynet list

Worker ::

   skynet enable build_image
   skynet register build_image

Web UI ::

   service lighttpd start
   service img-web start
   skynet enable request_image
   skynet enable update_image_status
   skynet enable build_ks
   skynet register request_image
   skynet register update_image_status
   skynet register build_ks


Making lighttpd and img_web system services start by default on boot is a
sysadmin task and is distribution specific.

You should now be able to access the web interface and admin at ::

   http://$IP-address/img/
   http://$IP-address/img/admin/


