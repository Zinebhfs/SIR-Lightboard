#! /bin/sh

set -ex

# Config 
lb config --bootappend-live "boot=live locales=fr_FR.UTF-8 keyboard-layouts=fr" --mode "debian" --system "live" --distribution "bookworm" --archive-areas "main contrib non-free non-free-firmware" --binary-images "iso-hybrid"

# Bootloader
mkdir -p config/bootloaders/isolinux
cp ../isolinux.cfg config/bootloaders/isolinux/

# Install some packages
echo task-cinnamon-desktop > config/package-lists/desktop.list.chroot
echo obs-studio >> config/package-lists/desktop.list.chroot
echo pip >> config/package-lists/desktop.list.chroot
echo wget >> config/package-lists/desktop.list.chroot
echo kbd >> config/package-lists/desktop.list.chroot
echo python3-tk >> config/package-lists/desktop.list.chroot

# Copy xsessionrc and monscript.sh as startup script
mkdir -p config/includes.chroot_after_packages/etc/skel/
cp ../obs.xsession config/includes.chroot_after_packages/etc/skel/.xsessionrc
chmod +777 config/includes.chroot_after_packages/etc/skel/.xsessionrc
cp ../monscript.sh config/includes.chroot_after_packages/etc/skel/monscript.sh
chmod +777 config/includes.chroot_after_packages/etc/skel/monscript.sh

# Copy obs global config
mkdir -p config/includes.chroot_after_packages/etc/skel/.config/obs-studio/
cp ../obs-global-config.ini config/includes.chroot_after_packages/etc/skel/.config/obs-studio/global.ini
chmod +777 config/includes.chroot_after_packages/etc/skel/.config/obs-studio/global.ini

# Copy obs profile
mkdir -p config/includes.chroot_after_packages/etc/skel/.config/obs-studio/basic/profiles/MyProfile
cp ../obs-profile-config.ini config/includes.chroot_after_packages/etc/skel/.config/obs-studio/basic/profiles/MyProfile/basic.ini
chmod +777 config/includes.chroot_after_packages/etc/skel/.config/obs-studio/basic/profiles/MyProfile/basic.ini

# Copy obs scene
mkdir -p config/includes.chroot_after_packages/etc/skel/.config/obs-studio/basic/scenes
cp ../obs-scene-config.json config/includes.chroot_after_packages/etc/skel/.config/obs-studio/basic/scenes/MyScene.json
chmod +777 config/includes.chroot_after_packages/etc/skel/.config/obs-studio/basic/scenes/MyScene.json

# These config file for the main python app is not in git, because it's sensistive (API keys)
echo "These config file for the main python app is not in git, because it's sensistive (API keys). If they are not present, this script will fail."
mkdir -p config/includes.chroot_after_packages/etc/skel/SIR-Lightboard-main
cp ../../.env config/includes.chroot_after_packages/etc/skel/SIR-Lightboard-main/.env
chmod +777 config/includes.chroot_after_packages/etc/skel/SIR-Lightboard-main/.env
cp ../../token.pkl config/includes.chroot_after_packages/etc/skel/.config/obs-studio/basic/scenes/MyScene.json
chmod +777 config/includes.chroot_after_packages/etc/skel/.config/obs-studio/basic/scenes/MyScene.json
cp ../../client_secret.json config/includes.chroot_after_packages/etc/skel/SIR-Lightboard-main/client_secret.json
chmod +777 config/includes.chroot_after_packages/etc/skel/SIR-Lightboard-main/client_secret.json
