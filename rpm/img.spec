Name: img
Version: 0.3
Release: 1

Group: Applications/Engineering
License: GPLv2+
URL: http://www.meego.com
Source0: https://api.opensuse.org/public/source/Maemo:MeeGo-Infra/Meego-IMG/%{name}_%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildRequires: python 
BuildRequires: python-setuptools
BuildArch: noarch
Summary: Image creation service for MeeGo related products

%description
This package installs all the other imager packages.

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
Requires: python >= 2.5.0
Requires: mic2
Requires: python-amqplib
Requires: bzip2
Requires: sudo
Requires: python-daemon
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
Requires: python-yaml
Summary: Image creation service for MeeGo related products, django web interface
%description -n img-web
This package provides a django based web interface for imager. It can work with a standalone imager installation communicating over AMQP, or an installation that is part of BOSS.

%package -n img-amqp
Group: Applications/Engineering
BuildRequires: python >= 2.5.0
BuildRequires: python-setuptools
Requires: python >= 2.5.0
Requires: pykickstart
Requires: python-amqplib
Requires: img-core
Requires: python-simplejson
Summary: Image creation service for MeeGo related products, raw AMQP
%description -n img-amqp
This package provides the imager client components that communicate over AMQP with the worker to build images using mic2

%package -n img-boss
Group: Applications/Engineering
BuildRequires: python >= 2.5.0
BuildRequires: python-setuptools
Requires: python >= 2.5.0
Requires: pykickstart
Requires: img-amqp
Requires: ruote-amqp-pyclient
Requires: python-air
Requires: img-core
Summary: Image creation service for MeeGo related products, BOSS participants
%description -n img-boss
This package provides imager participants that plugin into a BOSS system to fulfill image building steps of processes

%prep
%setup -q

%build
python setup.py build

%install
rm -rf %{buildroot}
python setup.py -q install --root=$RPM_BUILD_ROOT --prefix=%{_prefix} --record=INSTALLED_FILES
install -D -m 755 rpm/img-web.init %{buildroot}/etc/init.d/img-web
install -D -m 755 rpm/img-amqp.init %{buildroot}/etc/init.d/img-amqp

%clean
rm -rf %{buildroot}

%files -n img-core
%defattr(-,root,root)
%config %{_sysconfdir}/imager/img.conf
%{_sysconfdir}/imager
%{python_sitelib}/img-0.1-py2.6.egg-info
%{python_sitelib}/img

%files -n img-web
%defattr(-,root,root,-)
%{python_sitelib}/img_web
%{_datadir}/img_web
%{_sysconfdir}/init.d/img-web

%files -n img-amqp
%defattr(-,root,root,-)
%{_bindir}/build_image.py
%{_bindir}/img_client.py
%{_sysconfdir}/init.d/img-amqp

%files -n img-boss
%defattr(-,root,root,-)
%{_bindir}/boss_build_image.py
%{_bindir}/boss_build_ks.py 
%{_bindir}/boss_img_client.py

%changelog
* Mon Oct 11 2010 Aleksi Suomalainen <aleksi.suomalainen@nomovok.com> 0.4
- Daemonization code added
- Code refactoring
* Sun Sep 26 2010 Islam Amer <islam.amer@nokia.com> 0.3
- Major restructure and themeing.
* Thu Sep 23 2010 Islam Amer <islam.amer@nokia.com> 0.2
- Increment version to build new package
* Fri Aug 13 2010 Islam Amer <islam.amer@nokia.com> 0.1
- Added kickstarter participant package
* Fri Jul 23 2010 Marko Helenius <marko.helenius@nomovok.com> 0.1
- Fixed Spec

