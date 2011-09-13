Name: img
Version: 0.60.2
Release: 1

Group: Applications/Engineering
License: GPLv2+
URL: http://www.meego.com
Source0: %{name}_%{version}.orig.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildRequires: python, python-sphinx, python-setuptools, python-boss-skynet,python-ruote-amqp, python-django, python-mysql, mic2
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
BuildRequires: python >= 2.5.0
BuildRequires: python-setuptools
Requires: python >= 2.5.0, mic2, sudo, pykickstart
Summary: Image creation service for MeeGo related products, core package
%description -n img-core
This package provides the core worker logic of imager.
It builds images using mic2 optionally in a virtual machine.

%package -n img-web
Group: Applications/Engineering
BuildRequires: python >= 2.5.0
BuildRequires: python-setuptools
Requires: python >= 2.5.0
Requires: lighttpd
Requires: boss-skynet
Requires: python-xml
Requires(post): boss-skynet
Requires: python-django, python-flup, python-mysql, mysql-client, mysql
Summary: Image creation service for MeeGo related products, django web interface
%description -n img-web
This package provides a django based web interface for imager that is part of BOSS.

%package -n img-worker
Group: Applications/Engineering
BuildRequires: python >= 2.5.0
BuildRequires: python-setuptools
Requires: img-core
Requires: python-boss-skynet >= 0.2.2
Requires: boss-skynet
Requires: python-xml
Requires(post): boss-skynet
Summary: Image creation service for MeeGo related products, BOSS participants
%description -n img-worker
This package provides imager participants that plugin into a BOSS system to 
fulfill image building steps of processes

%package -n img-ks
Group: Applications/Engineering
BuildRequires: python >= 2.5.0
BuildRequires: python-setuptools
Requires: img-core
Requires: python-boss-skynet >= 0.2.2
Requires: boss-skynet
Requires: python-xml
Requires(post): boss-skynet
Summary: Image creation service for MeeGo related products, BOSS participants
%description -n img-ks
This package provides imager participants that plugin into a BOSS system to
handle kickstarts

%prep
%setup -q %{name}-%{version}

%build
make

%install
rm -rf %{buildroot}
install -D -m 755 rpm/img-web.init %{buildroot}/etc/init.d/img-web
make PREFIX=%{_prefix} DESTDIR=%{buildroot} install

%clean
rm -rf %{buildroot}

%post -n img-boss
if [ $1 -eq 1 ] ; then
        for i in \
            build_image \
            build_ks \
        ; do
        
        skynet make_participant -n $i -p /usr/share/boss-skynet/$i.py

    done
fi

%post -n img-web
if [ $1 -eq 1 ] ; then
        for i in \
            update_image_status \
            request_image \
        ; do
        
        skynet make_participant -n $i -p /usr/share/boss-skynet/$i.py

    done
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
%{_sysconfdir}/init.d/img-web
%{_datadir}/boss-skynet/update_image_status.py
%{_datadir}/boss-skynet/request_image.py
%config(noreplace) %{_sysconfdir}/skynet/request_image.conf

%files -n img-worker
%defattr(-,root,root,-)
%{_datadir}/boss-skynet/build_image.py
%config(noreplace) %{_sysconfdir}/skynet/build_image.conf

‰files -n img-ks
%defattr(-,root,root,-)
%{_datadir}/boss-skynet/build_ks.py
%config(noreplace) %{_sysconfdir}/skynet/build_ks.conf

