#! /bin/sh

set -ex

mkdir -p live/
cd live/

# Config 
lb config --bootappend-live "boot=live locales=fr_FR.UTF-8 keyboard-layouts=fr username=user" \
          --mode "debian" --system "live" --distribution "bookworm" \
          --archive-areas "main contrib non-free non-free-firmware" --binary-images "iso-hybrid"

# Bootloader
mkdir -p config/bootloaders/isolinux
cp ../isolinux.cfg config/bootloaders/isolinux/

# Install some packages, add the package name you want in the list if you want to install it
{
    echo task-cinnamon-desktop
    echo obs-studio
    echo pip
    echo git
    echo kbd
    echo python3-tk
} > config/package-lists/desktop.list.chroot    

# Copy xsessionrc and monscript.sh as startup script
mkdir -p config/includes.chroot_after_packages/etc/skel/
cp ../start.xsession config/includes.chroot_after_packages/etc/skel/.xsessionrc
chmod +777 config/includes.chroot_after_packages/etc/skel/.xsessionrc

# These config file for the main python app is not in git, because it's sensistive (API keys)
echo "These config file for the main python app is not in git, because it's sensistive (API keys). If they are not present, this script will fail."
cp ../../.env config/includes.chroot_after_packages/etc/skel/.env
chmod +777 config/includes.chroot_after_packages/etc/skel/.env

# SSH key
mkdir -p config/includes.chroot_after_packages/etc/skel/.ssh/
cp ../../id_rsa.dat config/includes.chroot_after_packages/etc/skel/.ssh/id_rsa.dat
chmod +777 config/includes.chroot_after_packages/etc/skel/.ssh/id_rsa.dat
cp ../../id_rsa.pub config/includes.chroot_after_packages/etc/skel/.ssh/id_rsa.pub
chmod +777 config/includes.chroot_after_packages/etc/skel/.ssh/id_rsa.pub