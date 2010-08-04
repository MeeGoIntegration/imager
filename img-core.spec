Name: img-core
Version: 0.1
Release: 1%{?dist}

Group: Applications/Engineering
License: GPLv2+
URL: http://www.meego.com
Source0: img-core-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
#Requires(pre): %insserv_prereq %fillup_prereq
BuildRequires: python, python-setuptools
Requires: yum, mic2, bzip2, python-amqplib, route-amqp-pyclient, python-air, python-simplejson
Requires: python >= 2.5.0
BuildArchitectures: noarch
Summary: Image Me Give, service package

%description
An image creation service and a django frontend for MeeGo.

%package -n img-web
Group: Applications/Engineering
BuildRequires: python >= 2.5.0, lighttpd
BuildRequires: -post-build-checks
Requires: lighttpd, lighttpd-fastcgi,PyYAML, python-sqlite, python-django,python-flup, python-simplejson
Summary: Meego Image Me Give, django frontend + service
%description -n img-web
Meego Image Me Give, service package: django frontend + service

%package -n img-control
Group: Applications/Engineering
Requires: python >= 2.5.0
Requires: python-amqplib, python-simplejson
Summary: MeeGo Image Me Give, a control client
%description -n img-control
Meego Image Me Give, control client package. For control.
%prep
%setup -q
%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_initddir}
install -D -m 755 rpm/img-www.init %{buildroot}/etc/init.d/img-webd
mkdir -p %{buildroot}%{_sbindir}
ln -sf %{_initrddir}/img-webd %{buildroot}%{_sbindir}/rcimg-webd
install -D -m 755 rpm/img-core.init %{buildroot}/etc/init.d/img-cored
ln -sf %{_initrddir}/img-cored %{buildroot}%{_sbindir}/rcimg-cored
mkdir -p %{buildroot}/var/www/django/img
cp -a src/meego_img %{buildroot}/var/www/django/img/
#cp src/meego_img/settings.py %{buildroot}/var/www/django/img/
#cp src/meego_img/manage.py %{buildroot}/var/www/django/img/
mkdir -p %{buildroot}/etc/imger
cp src/meego_img/img.conf %{buildroot}/etc/imger/
mkdir -p %{buildroot}/usr/share/img
cp -a kickstarter %{buildroot}/usr/share/img/
mkdir -p %{buildroot}/usr/bin
#install -D -m 755 src/meego_img/image_creator.py %{buildroot}/usr/bin/meego_image_creator
#install -D -m 755 src/meego_img/client.py %{buildroot}/usr/bin/meego_image_client
install -D -m 755 src/meego_img/boss_client.py %{buildroot}/usr/bin/boss_img_client
install -D -m 755 src/meego_img/participant.py %{buildroot}/usr/bin/boss_img_participant
install -D -m 755 src/meego_img/image_creator.py %{buildroot}/usr/bin/img_service
install -D -m 755 src/meego_img/client.py %{buildroot}/usr/bin/img_client
mkdir -p %{buildroot}/etc/lighttpd/vhosts.d
mkdir -p %{buildroot}/var/www/django/run
cp -a debian/img-lighttpd.conf %{buildroot}/etc/lighttpd/vhosts.d/
mkdir -p %{buildroot}/usr/share/doc/img
cp README INSTALL %{buildroot}/usr/share/doc/img/
mkdir -p %{buildroot}/etc/sysconfig
cp rpm/img_sysconfig %{buildroot}/etc/sysconfig/img
python setup.py install --prefix=/usr --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES 
%clean
rm -rf %{buildroot}

%post -n img-web
PROJECTDIR=/var/www/django/img
$PROJECTDIR/meego_img/manage.py syncdb --noinput
%postun -n img-web
PROJECTDIR=/var/www/django/img

%post -n img-core
#rabbitmqctl add_user img imgpwd
#rabbitmqctl add_vhost imgvhost
#rabbitmqctl set_permissions -p imgvhost img "" ".*" ".*"
%files -f INSTALLED_FILES  
%defattr(-,root,root)
%files -n img-web
%defattr(-,root,root,-)
%{_sbindir}/rcimg-webd
%config /etc/init.d/img-webd
/usr/share/doc/img/*
%config /etc/lighttpd/vhosts.d/img-lighttpd.conf
%doc /usr/share/img/kickstarter/*
%defattr(-, root, root, 0755)
/var/www/django/img/*

%files -n img-core -f INSTALLED_FILES
%defattr(-,root,root,-)
%{_sbindir}/rcimg-cored
%config /etc/init.d/img-cored
%config /etc/imger/img.conf
%config /etc/sysconfig/img
/usr/bin/boss_img_participant
/usr/bin/img_service


%files -n img-control
%defattr(-,root,root,-)
/usr/bin/boss_img_client
/usr/bin/img_client
%changelog
* Fri Jul 23 2010 Marko Helenius <marko.helenius@nomovok.com> 0.1
- Fixed Spec


