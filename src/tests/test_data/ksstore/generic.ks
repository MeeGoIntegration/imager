#version=DEVEL
user --groups=audio,video --name=meego --password=meego
# Root password
rootpw --plaintext meego
# System authorization information
auth --useshadow --enablemd5
# System keyboard
keyboard us
# System language
lang en_US.UTF-8
# Installation logging level
logging --level=info

# System timezone
timezone --isUtc America/Los_Angeles
# Default Desktop Settings
desktop  --autologinuser=meego
repo --name="oss" --baseurl=http://repo.meego.com/MeeGo/releases/1.2.0/repos/oss/ia32/packages/ --gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-meego
repo --name="_Chalk_Trunk_standard" --baseurl=http://172.21.21.228:83/Chalk:/Trunk/standard
# System bootloader configuration
bootloader --location=mbr --timeout=5 --menus=
# Disk partitioning information
part / --fstype="ext2" --ondisk=sda --size=2048

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


echo > /boot/extlinux/extlinux.conf

cat << EOF >> /boot/extlinux/extlinux.conf

prompt 0
timeout 1

menu hidden
DEFAULT meego0

menu title Welcome to MeeGo!
label meego0
    menu label MeeGo (2.6.38.2-9.1)
    kernel vmlinuz-2.6.38.2-9.1
    append ro root=/dev/vda1  vga=current
    menu default

EOF

%end

%post --nochroot
if [ -n "$IMG_NAME" ]; then
    echo "BUILD: $IMG_NAME" >> $INSTALL_ROOT/etc/meego-release
fi
%end

%packages --excludedocs
@MeeGo Base
kernel

%end
