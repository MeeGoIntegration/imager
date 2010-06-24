Name: img
Version: 0.1
Release: 1%{?dist}
Summary: Meego Image Me Give, django frontend + service
Group: Applications/Engineering
License: GPLv2+
URL: http://www.meego.com
Source0: img-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: python,python-setuptools
Requires: python >= 2.6.0
Requires: lighttpd, lighttpd-fastcgi,PyYAML, python-sqlite,Django,python-flup
%description
An image creator and a django frontend for MeeGo.
%package -n img-svc
#Requires(pre): %insserv_prereq %fillup_prereq
Requires: rabbitmq-server, yum, mic2, pykickstart, bzip2, sudo, python-cheetah
Requires: python >= 2.6.0
Group: Applications/Engineering
Summary: Image Me Give, service package
%description -n img-svc
Image Me Give, service package

%prep
%setup -q
%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_initddir}
install -D -m 755 rpm/img-svc.init %{buildroot}/etc/init.d/img-svc
mkdir -p %{buildroot}%{_sbindir}
ln -sf %{_initrddir}/img-svc %{buildroot}%{_sbindir}/rcimg-svc
install -D -m 755 rpm/img.init %{buildroot}/etc/init.d/img
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
%clean
rm -rf %{buildroot}
%post -n img
PROJECTDIR=/var/www/django/img
$PROJECTDIR/meego_img/manage.py syncdb --noinput
%postun -n img
PROJECTDIR=/var/www/django/img
$PROJECTDIR/meego_img/manage.py sqlclear app
%files
%defattr(-,root,root,-)
%{_sbindir}/rcimg
/etc/init.d/img
/var/www/django/img/*
/usr/share/img/kickstarter/*
/etc/lighttpd/vhosts.d/img-lighttpd.conf
%files -n img-svc
%defattr(-,root,root,-)
%{_sbindir}/rcimg-svc
/etc/init.d/img-svc
/usr/bin/meego_image_creator
/usr/bin/meego_image_client