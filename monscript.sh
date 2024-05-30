#!/bin/sh

# This script need to be launch after the gui is fully loaded

set -ex

cd /home/user/SIR-Lightboard

# Copy obs global config
mkdir -p /home/user/.config/obs-studio/
cp /home/user/SIR-Lightboard/obs/obs-global-config.ini /home/user/.config/obs-studio/global.ini
chmod +777 /home/user/.config/obs-studio/global.ini

# Copy obs profile
mkdir -p /home/user/.config/obs-studio/basic/profiles/MyProfile
cp /home/user/SIR-Lightboard/obs/obs-profile-config.ini /home/user/.config/obs-studio/basic/profiles/MyProfile/basic.ini
chmod +777 /home/user/.config/obs-studio/basic/profiles/MyProfile/basic.ini

# Copy obs scene
mkdir -p /home/user/.config/obs-studio/basic/scenes
cp /home/user/SIR-Lightboard/obs/obs-scene-config.json /home/user/.config/obs-studio/basic/scenes/MyScene.json
chmod +777 /home/user/.config/obs-studio/basic/scenes/MyScene.json

sudo pip install -r requirements.txt --break-system-packages

obs &

sudo /usr/bin/python3 /home/user/SIR-Lightboard/main.py 2> /home/user/error.txt &
