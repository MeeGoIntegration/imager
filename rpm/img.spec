Name: img
Version: 0.60.0
Release: 1

Group: Applications/Engineering
License: GPLv2+
URL: http://www.meego.com
Source0: %{name}_%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildRequires: python 
BuildRequires: python-setuptools
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
This package provides the core worker logic of imager. It builds images using mic2 optionally in a virtual machine.

%package -n img-web
Group: Applications/Engineering
BuildRequires: python >= 2.5.0
BuildRequires: python-setuptools
Requires: python >= 2.5.0
Requires: lighttpd
Requires: python-django
Requires: python-flup
Requires: python-django-south
Requires(post): boss-skynet
Summary: Image creation service for MeeGo related products, django web interface
%description -n img-web
This package provides a django based web interface for imager. It can work with a standalone imager installation communicating over AMQP, or an installation that is part of BOSS.

%package -n img-boss
Group: Applications/Engineering
BuildRequires: python >= 2.5.0
BuildRequires: python-setuptools
Requires: img-core
Requires: python-boss-skynet >= 0.2.2
Requires(post): boss-skynet
Summary: Image creation service for MeeGo related products, BOSS participants
%description -n img-boss
This package provides imager participants that plugin into a BOSS system to fulfill image building steps of processes

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

%files -n img-boss
%defattr(-,root,root,-)
%{_datadir}/boss-skynet/*.py
%config(noreplace) %{_sysconfdir}/skynet/build_image.conf
%config(noreplace) %{_sysconfdir}/skynet/build_ks.conf
%config(noreplace) %{_sysconfdir}/skynet/request_image.conf
