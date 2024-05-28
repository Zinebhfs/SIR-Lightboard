#! /bin/sh

set -ex

# Launch obs and made it fullscreen
obs --profile /home/user/.config/obs-studio/profiles/untitled/basic &
sleep 10
WID=`xdotool search --name "OBS"`
echo $WID
xdotool windowfocus $WID.
xdotool mousemove --window $WID 0 0
xdotool mousemove --window $WID 100 100
xdotool click --window $WID 3
xdotool key Down Down Down Down Right Return


wget https://github.com/Zinebhfs/SIR-Lightboard/archive/refs/tags/rc.tar.gz
tar -xvf rc.tar.gz
cd SIR-Lightboard-rc
pip install -r requirements.txt -bre
python main.py
