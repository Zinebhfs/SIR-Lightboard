#! /bin/sh

# This script need to be launch after the gui is fully loaded

set -ex

obs &

wget https://github.com/Zinebhfs/SIR-Lightboard/archive/main.tar.gz
tar -xvf main.tar.gz
cd SIR-Lightboard-glue
pip install -r requirements.txt --break-system-packages
python main.py
