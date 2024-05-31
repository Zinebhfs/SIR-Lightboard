#!/bin/sh

while true; do
if ping -c 1 github.com >/dev/null 2>&1; then
    echo "github.com est accessible."
    break
  else
    echo "github.com n'est pas accessible, réessai dans 5 secondes..."
    sleep 5
  fi
done

# Get 
git clone https://github.com/Zinebhfs/SIR-Lightboard

# Execute the script
cd SIR-Lightboard/
sh ./monscript.sh
