lang en_US.UTF-8
keyboard us
timezone --utc America/Los_Angeles
auth --useshadow --enablemd5
part / --size 1024 --ondisk sda --fstype=ext3
rootpw meego
# xconfig --startxonboot
bootloader --timeout=5
# desktop --autologinuser=meego  --defaultdesktop=DUI --session="/usr/bin/mcompositor"
user --name meego  --groups audio,video --password meego

repo --name=oss --baseurl=http://repo.meego.com/MeeGo/releases/1.2.0/repos/oss/ia32/packages/ --gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-meego
repo --name=tools --baseurl=http://download.meego.com/live/Tools:/Building/Trunk/ --gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-meego
repo --name=dhcpcd --baseurl=http://repo.pub.meego.com/home:/iamer:/dhcpcd/MeeGo_1.2.0/

%packages  --excludedocs
@MeeGo Base

kernel

openssh
openssh-clients
openssh-server

dhcpcd

mic2
qemu-arm-static

%end
%post

# save a little bit of space at least...
# rm -f /boot/initrd*

# make sure there aren't core files lying around
rm -f /core*

# Prelink can reduce boot time
if [ -x /usr/sbin/prelink ]; then
    /usr/sbin/prelink -aRqm
fi

# work around for poor key import UI in PackageKit
rm -f /var/lib/rpm/__db*
rpm --rebuilddb

cat << EOF >> /etc/rc.local

echo 0 > /proc/sys/vm/vdso_enabled
mount -t binfmt_misc -o nodev,noexec,nosuid binfmt_misc /proc/sys/fs/binfmt_misc/
echo ':arm:M::\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x28\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/usr/bin/qemu-arm-static:' > /proc/sys/fs/binfmt_misc/register
ifconfig lo up
/sbin/dhcpcd eth0

EOF

# setup ssh for root
mkdir -p -m 0700 /root/.ssh
/usr/bin/ssh-keygen -q -C "img vm" -t rsa -f /root/.ssh/id_rsa -N ''
cp /root/.ssh/id_rsa.pub /root/.ssh/authorized_keys

echo
echo "**********************************"
echo "SSH private key for this image :"
cat /root/.ssh/id_rsa
echo "**********************************"
echo

%end

%post --nochroot
if [ -n "$IMG_NAME" ]; then
    echo "BUILD: $IMG_NAME" >> $INSTALL_ROOT/etc/meego-release
fi
%end
