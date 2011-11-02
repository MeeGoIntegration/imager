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

Setup django (add a superuser)::

 export DJANGO_SETTINGS_MODULE=img_web.settings
 django-admin syncdb
 #then
 django-admin migrate
 #then
 django-admin collectstatic

.. note::

   Ignore any errors that are produced by the migrate command.

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
             "socket" => "/var/run/img_web/img_web" + ".socket",
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

To start the img application server run:
 service img-web start

If you use the config described here you should be able to login at
http://127.0.0.1/img/admin using the superuser. There you can add more
users.

The main IMG application can then be reached at : http://127.0.0.1/img/
