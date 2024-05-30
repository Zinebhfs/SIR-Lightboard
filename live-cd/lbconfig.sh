#! /bin/sh

set -ex

# Config 
lb config --bootappend-live "boot=live locales=fr_FR.UTF-8 keyboard-layouts=fr username=user" --mode "debian" --system "live" --distribution "bookworm" --archive-areas "main contrib non-free non-free-firmware" --binary-images "iso-hybrid" --apt-recommends "false"

# Bootloader
mkdir -p config/bootloaders/isolinux
cp ../isolinux.cfg config/bootloaders/isolinux/

# Install some packages
echo task-cinnamon-desktop > config/package-lists/desktop.list.chroot
echo user-setup >> config/package-lists/desktop.list.chroot
echo sudo >> config/package-lists/desktop.list.chroot
echo pip >> config/package-lists/desktop.list.chroot
echo git >> config/package-lists/desktop.list.chroot
echo obs-studio >> config/package-lists/desktop.list.chroot
echo kbd >> config/package-lists/desktop.list.chroot
echo python3-tk >> config/package-lists/desktop.list.chroot

# Copy xsessionrc and monscript.sh as startup script
mkdir -p config/includes.chroot_after_packages/etc/skel/
cp ../start.xsession config/includes.chroot_after_packages/etc/skel/.xsessionrc
chmod +777 config/includes.chroot_after_packages/etc/skel/.xsessionrc

# These config file for the main python app is not in git, because it's sensistive (API keys)
echo "These config file for the main python app is not in git, because it's sensistive (API keys). If they are not present, this script will fail."
cp ../../.env config/includes.chroot_after_packages/etc/skel/.env
chmod +777 config/includes.chroot_after_packages/etc/skel/.env
cp ../../token.pkl config/includes.chroot_after_packages/etc/skel/token.pkl
chmod +777 config/includes.chroot_after_packages/etc/skel/token.pkl
cp ../../client_secret.json config/includes.chroot_after_packages/etc/skel/client_secret.json
chmod +777 config/includes.chroot_after_packages/etc/skel/client_secret.json
