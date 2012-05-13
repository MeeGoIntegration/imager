%define svdir %{_sysconfdir}/supervisor/conf.d/

Name: img
Version: 0.63.0
Release: 1

Group: Applications/Engineering
License: GPLv2+
URL: http://www.meego.com
Source0: %{name}_%{version}.orig.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildRequires: python, python-distribute, python-sphinx, python-boss-skynet, python-ruote-amqp, python-django, python-mysql, mic >= 0.4
BuildArch: noarch
Summary: Image creation service for MeeGo related products

%description
Image creation service for MeeGo related products

%define python python%{?__python_ver}
%define __python /usr/bin/%{python}
%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif

%package -n img-core
Group: Applications/Engineering
Requires: python >= 2.5.0, mic2, sudo, pykickstart, lvm2
Requires(pre): pwdutils
Summary: Image creation service for MeeGo related products, core package
%description -n img-core
This package provides the core worker logic of imager.
It builds images using mic2 optionally in a virtual machine.

%package -n img-web
Group: Applications/Engineering
Requires: python >= 2.5.0
Requires: python-xml
Requires: python-boss-skynet
Requires: python-django-taggit
Requires(post): python-boss-skynet
Requires: python-django, python-flup, python-mysql, mysql-client, mysql
Summary: Image creation service for MeeGo related products, django web interface
%description -n img-web
This package provides a django based web interface for imager that is part of BOSS.

%package -n img-worker
Group: Applications/Engineering
Requires: img-core
Requires: python-xml
Requires: python-boss-skynet
Requires(post): python-boss-skynet
Summary: Image creation service for MeeGo related products, BOSS participants
%description -n img-worker
This package provides imager participants that plugin into a BOSS system to 
fulfill image building steps of processes

%package -n img-ks
Group: Applications/Engineering
Requires: img-core
Requires: python-xml
Requires: python-buildservice
Requires: boss-standard-workflow-common
Requires: python-boss-skynet
Requires(post): python-boss-skynet
Summary: Image creation service for MeeGo related products, BOSS participants
%description -n img-ks
This package provides imager participants that plugin into a BOSS system to
handle kickstarts

%prep
%setup -q %{name}-%{version}

%build
make docs

%install
rm -rf %{buildroot}
make PREFIX=%{_prefix} DESTDIR=%{buildroot} install

%clean
rm -rf %{buildroot}

%pre -n img-core
getent group imgadm >/dev/null || groupadd -r imgadm
getent passwd img >/dev/null || \
    useradd -r -g imgadm -d /home/img -s /sbin/nologin \
    -c "IMG user" img
exit 0

%post -n img-worker
if [ $1 -ge 1 ] ; then
        skynet apply || true
        # can wait upto 2 hours
        skynet reload build_image &
fi

%post -n img-ks
if [ $1 -ge 1 ] ; then
    skynet apply || true
    skynet reload build_ks || true
fi

%post -n img-web
if [ $1 -ge 1 ] ; then
    skynet apply || true
    skynet reload update_image_status request_image || true
fi

%files -n img-core
%defattr(-,root,root)
%{_sysconfdir}/imager
%{python_sitelib}/img*egg-info
%{python_sitelib}/img

%files -n img-web
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/imager/img.conf
%{python_sitelib}/img_web
%{_datadir}/img_web
%{_datadir}/boss-skynet/update_image_status.py
%{_datadir}/boss-skynet/request_image.py
%config(noreplace) %{_sysconfdir}/skynet/request_image.conf
%config(noreplace) %{svdir}/request_image.conf
%config(noreplace) %{svdir}/update_image_status.conf
%config(noreplace) %{svdir}/img_web.conf
%dir /etc/supervisor
%dir /etc/supervisor/conf.d
%dir /usr/share/boss-skynet

%files -n img-worker
%defattr(-,root,root,-)
%{_datadir}/boss-skynet/build_image.py
%config(noreplace) %{_sysconfdir}/skynet/build_image.conf
%config(noreplace) %{svdir}/build_image.conf
%dir /etc/supervisor
%dir /etc/supervisor/conf.d
%dir /usr/share/boss-skynet

%files -n img-ks
%defattr(-,root,root,-)
%{_datadir}/boss-skynet/build_ks.py
%config(noreplace) %{_sysconfdir}/skynet/build_ks.conf
%config(noreplace) %{svdir}/build_ks.conf
%dir /etc/supervisor
%dir /etc/supervisor/conf.d
%dir /usr/share/boss-skynet
