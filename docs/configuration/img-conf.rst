Imager WebUI configuration 
==========================

IMG UI is a django web application which uses different extra 
servers to work:

 * HTTP server to serve the web based requests.
 * SQL DB to store information about the images.
 * OPTIONAL LDAP server for authentication.
 * OPTIONAL OTS server for testing images.

This is the default configuration at /etc/imager/img.conf

.. literalinclude:: ../../src/img_web/img.conf

The code and instructions have been tested with MySQL and Lighttpd on Debian 
squeeze.

MySQL Configuration
-------------------

MySQL is installed by default and during installation a root account
will have been created. The password is needed to create an img user.

Ammend the IDENTIFIED BY 'img' to use an appropriate img password ::

 mysql -u root -p
 create database imgdb CHARACTER SET utf8;
 GRANT ALL ON imgdb.* TO 'img'@'localhost' IDENTIFIED BY 'img';
 exit


Django Configuration
--------------------

Edit /etc/imager/img.conf and set the configuration values.

Create locations for the images and templates::

 install -d -m 0777 /var/www/img/images
 install -d -m 0777 /var/www/img/templates

Setup django (add a superuser), Debian::

 export DJANGO_SETTINGS_MODULE=img_web.settings
 django-admin syncdb
 django-admin collectstatic

openSUSE::

 export DJANGO_SETTINGS_MODULE=img_web.settings
 django-admin.py syncdb
 django-admin.py collectstatic

Configure Lighttpd
------------------

This is only an example, your installation may vary::

 mkdir -p /etc/lighttpd/vhosts.d
 cat > /etc/lighttpd/vhosts.d/img.conf << 'EOF'
 var.namebasedir = "/img"
 
 $HTTP["url"] =~ "^" + namebasedir {
         dir-listing.activate = "disable"
 }
 
 url.redirect += (
   "^" + namebasedir + "$" => namebasedir + "/"
 )
 
 fastcgi.server += (
     "/img.fcgi" => (
         "main" => (
             "host" => "127.0.0.1",
             "port" => "9299",
             "check-local" => "disable",
         )
     ),
 )
 
 url.rewrite-if-not-file += (
    "^(" + namebasedir + "/.*)$" => "/img.fcgi/$1"
 )
 EOF

Edit /etc/lighttpd/lighttpd.conf and enable mod_rewrite;
then add the following line at the end ::

 include_shell "cat /etc/lighttpd/vhosts.d/*.conf"

Then run::

 lighttpd-enable-mod fastcgi
 lighttpd-enable-mod accesslog
 lighttpd-enable-mod dir-listing
 service lighttpd force-reload

Configure nginx
---------------

This is only an example, your installation may vary::

 cat > /etc/nginx/vhosts.d/img.conf << 'EOF'
 upstream imgweb {
   server 127.0.0.1:9299;
 }

 server {
    listen 80;
    access_log  /var/log/nginx/imgweb.log;

    server_name img;

    location /images/ {
        alias /srv/www/img/images/;
    } 
    location /img/site_media/ {
        alias /srv/www/img/site_media/;
    } 
    location /img {

        include /etc/nginx/fastcgi_params;
        fastcgi_param  SCRIPT_NAME "";

        fastcgi_pass       imgweb;
    }

    location / {
        rewrite_log on;
        rewrite  ^/$  /img/ permanent;
    }
  }
  EOF


All done
--------

To start the img application server run::

 skynet reload img-web

If you use the config described here you should be able to login at
http://127.0.0.1/img/admin using the superuser. There you can add more
users.

The IMG application can then be reached at : http://127.0.0.1/img/
