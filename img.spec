Name: img-core
Version: 0.1
Release: 1%{?dist}

Group: Applications/Engineering
License: GPLv2+
URL: http://www.meego.com
Source0: img-core-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
#Requires(pre): %insserv_prereq %fillup_prereq
Requires: rabbitmq-server, yum, mic2, pykickstart, bzip2, sudo, python-cheetah
Requires: python >= 2.5.0
Summary: Image Me Give, service package

%description
An image creation service and a django frontend for MeeGo.
%package -n img-web
Group: Applications/Engineering
Requires: python >= 2.5.0
Requires: lighttpd, lighttpd-fastcgi,PyYAML, python-sqlite,Django,python-flup
Summary: Meego Image Me Give, django frontend + service
%description -n img-web
Image Me Give, service package
%package -n img-control
Group: Applications/Engineering
Requires: python >= 2.5.0
Requires: python-amqplib
Summary: MeeGo Image Me Give, a control client
%description -n img-control
Image Me Give, control client package.
%prep
%setup -q
%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_initddir}
install -D -m 755 rpm/img-core.init %{buildroot}/etc/init.d/img-svc
mkdir -p %{buildroot}%{_sbindir}
ln -sf %{_initrddir}/img-svc %{buildroot}%{_sbindir}/rcimg-svc
install -D -m 755 rpm/img-www.init %{buildroot}/etc/init.d/img
ln -sf %{_initrddir}/img %{buildroot}%{_sbindir}/rcimg
mkdir -p %{buildroot}/var/www/django/img
cp -a src/meego_img %{buildroot}/var/www/django/img
mkdir -p %{buildroot}/usr/share/img
cp -a kickstarter %{buildroot}/usr/share/img/
mkdir -p %{buildroot}/usr/bin
install -D -m 755 src/meego_img/image_creator.py %{buildroot}/usr/bin/meego_image_creator
install -D -m 755 src/meego_img/client.py %{buildroot}/usr/bin/meego_image_client
mkdir -p %{buildroot}/etc/lighttpd/vhosts.d
mkdir -p %{buildroot}/var/www/django/run
cp -a debian/img-lighttpd.conf %{buildroot}/etc/lighttpd/vhosts.d/
mkdir -p %{buildroot}/usr/share/doc/img
cp README INSTALL %{buildroot}/usr/share/doc/img/
%clean
rm -rf %{buildroot}
%post -n img-web
PROJECTDIR=/var/www/django/img
$PROJECTDIR/meego_img/manage.py syncdb --noinput
%postun -n img-web
PROJECTDIR=/var/www/django/img
$PROJECTDIR/meego_img/manage.py sqlclear app
%post -n img-core
rabbitmqctl add_user img imgpwd
rabbitmqctl add_vhost imgvhost
rabbitmqctl set_permissions -p imgvhost img "" ".*" ".*"
%files -n img-web
%defattr(-,root,root,-)
%{_sbindir}/rcimg
/etc/init.d/img
/var/www/django/img/*
/usr/share/img/kickstarter/*
/etc/lighttpd/vhosts.d/img-lighttpd.conf
/usr/share/doc/img/*
%files -n img-core
%defattr(-,root,root,-)
%{_sbindir}/rcimg-svc
/etc/init.d/img-svc
/usr/bin/meego_image_creator
%files -n img-control
/usr/bin/meego_image_client