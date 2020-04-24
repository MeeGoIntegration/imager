%define svdir %{_sysconfdir}/supervisor/conf.d/
%define python python%{?__python_ver}
%define __python /usr/bin/%{python}

Name: img
Version: 0.67.1
Release: 1

Group: Applications/Engineering
License: GPLv2+
URL: https://github.com/MeegoIntegration/imager.git
Source: %{name}-%{version}.tar.gz

BuildArch: noarch

BuildRequires:  python
BuildRequires:  python-setuptools
BuildRequires:  python-Django
BuildRequires:  python-distribute
BuildRequires:  python-sphinx
BuildRequires:  python-boss-skynet
BuildRequires:  python-ruote-amqp
BuildRequires:  pykickstart
BuildRequires:  python-django-taggit
BuildRequires:  python-buildservice

BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot

Summary: Image creation service for SailfishOS related products

%description
Image creation service for SailfishOS related products

%package -n img-core
Requires: python >= 2.5.0
Requires:  sudo
Requires:  pykickstart
Requires:  lvm2
Requires(pre): pwdutils
Requires(post): sudo
Requires(post): eat-host

Summary: Image creation service for SailfishOS related products, core package
%description -n img-core
This package provides the core worker logic of imager.
It builds images using mic optionally in a virtual machine.

%package -n img-web
Requires: python >= 2.5.0
Requires: python-xml
Requires: python-boss-skynet
Requires: python-django-taggit
Requires(post): python-boss-skynet
Requires: python2-Django1
Requires:  python-flup
Requires:  python-mysql
Summary: Image creation service for SailfishOS related products, django web interface
%description -n img-web
This package provides a django based web interface for imager that is part of BOSS.

%package -n img-worker
Requires: img-core
Requires: python-xml
Requires: python-boss-skynet
Requires(post): python-boss-skynet
Summary: Image creation service for SailfishOS related products, BOSS participants
%description -n img-worker
This package provides imager participants that plugin into a BOSS system to 
fulfill image building steps of processes

%package -n img-ks
Requires: python-xml
Requires: python-buildservice
# This is required by pykickstart
Requires: python-urlgrabber
Requires(pre): boss-standard-workflow-common
Requires: python-boss-skynet
Requires(post): python-boss-skynet
Summary: Image creation service for SailfishOS related products, BOSS participants
%description -n img-ks
This package provides imager participants that plugin into a BOSS system to
handle kickstarts

%package -n img-make-vdi
Requires: python-xml
Requires: python-buildservice
Requires: boss-standard-workflow-common
Requires: python-boss-skynet
Requires: virtualbox
Requires(post): python-boss-skynet
Summary: Image creation service for SailfishOS related products, BOSS participants
%description -n img-make-vdi
This package provides imager participants that plugin into a BOSS system to
handle VirtualBox VDI images

%package -n img-test-vm
Requires: img-core
Requires: python-xml
Requires: python-buildservice
Requires: python-boss-skynet
Requires(post): python-boss-skynet
Summary: Image creation service for SailfishOS related products, BOSS participants
%description -n img-test-vm
This package provides imager participant that can test images using VMs

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
    useradd -m -r -g imgadm -d /home/img -s /sbin/nologin \
    -c "IMG user" img
exit 0

%post -n img-core
if [ $1 -ge 1 ] ; then
  sudo -u img eat-install-host-key || true
fi

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

%post -n img-make-vdi
if [ $1 -ge 1 ] ; then
    skynet apply || true
    skynet reload make_vdi || true
fi

%post -n img-test-vm
if [ $1 -ge 1 ] ; then
    skynet apply || true
    skynet reload test_vm_image || true
fi

%post -n img-web
if [ $1 -ge 1 ] ; then
    if [ $1 -eq 2 ]; then
	# Only support upgrades - installation is done manually
	cd %{python_sitelib}/img_web
	export DJANGO_SETTINGS_MODULE=img_web.settings
	# These fail during the rpmlint test during build :/
	django-admin collectstatic --noinput || true
	django-admin migrate --noinput || true
    fi
    skynet apply || true
    skynet reload update_image_status request_image || true
fi

%files -n img-core
%defattr(-,root,root)
%dir %{_sysconfdir}/imager
%config(noreplace) %{_sysconfdir}/imager/img.conf
%{python_sitelib}/img*egg-info
%{python_sitelib}/img
%{_bindir}/img_vm_shutdown

%files -n img-web
%defattr(-,root,root,-)
%{python_sitelib}/img_web
%{_datadir}/img_web
%{_datadir}/boss-skynet/update_image_status.py
%{_datadir}/boss-skynet/update_symlinks.py
%{_datadir}/boss-skynet/request_image.py
%config(noreplace) %{_sysconfdir}/skynet/update_symlinks.conf
%config(noreplace) %{_sysconfdir}/skynet/request_image.conf
%config(noreplace) %{svdir}/request_image.conf
%config(noreplace) %{svdir}/update_image_status.conf
%config(noreplace) %{svdir}/update_symlinks.conf
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

%files -n img-make-vdi
%defattr(-,root,root,-)
%{_datadir}/boss-skynet/make_vdi.py
%config(noreplace) %{_sysconfdir}/skynet/make_vdi.conf
%config(noreplace) %{svdir}/make_vdi.conf
%dir /etc/supervisor
%dir /etc/supervisor/conf.d
%dir /usr/share/boss-skynet

%files -n img-test-vm
%defattr(-,root,root,-)
%{_bindir}/img_test_vm.sh
%{_bindir}/img_host_test.sh
%{_datadir}/boss-skynet/test_vm_image.py
%config(noreplace) %{_sysconfdir}/skynet/test_vm_image.conf
%config(noreplace) %{svdir}/test_vm_image.conf
%dir /etc/supervisor
%dir /etc/supervisor/conf.d
%dir /usr/share/boss-skynet
