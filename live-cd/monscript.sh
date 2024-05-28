#! /bin/sh

# This script need to be launch after the gui is fully loaded

set -ex

wget https://github.com/Zinebhfs/SIR-Lightboard/archive/main.tar.gz
tar -xvf main.tar.gz
cd SIR-Lightboard-main
pip install -r requirements.txt --break-system-packages
python3 main.py
