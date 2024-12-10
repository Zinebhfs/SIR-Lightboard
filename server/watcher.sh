#!/bin/bash

cont=false

cat entete.html > index.html

for file in `ls download/*.lock`
do
  echo "traitement $file"
  tmp=$(echo $file | sed s/\.lock//)  
  shortfile=$(echo $tmp | sed s/\.mkv//)  
  sshortfile=$(echo $shortfile | sed s/download\\///)
  cp /tmp/$sshortfile.mkv download/$sshortfile.mkv
  rm -f $shortfile.mp4
  ffmpeg -i $shortfile.mkv -pix_fmt yuv420p -codec copy "$shortfile.mp4" -loglevel error
  ffmpeg -i $shortfile.mkv -frames:v 1 "$shortfile.jpg"
done
rm -f download/*.lock

for file in `ls -t download/*.mkv`
do
  shortfile=$(echo $file | sed s/\.mkv//)  
  sshortfile=$(echo $shortfile | sed s/download\\///)
  sizeH=$(du -h $shortfile.mp4 | cut -f 1)
  sizeB=$(du $shortfile.mp4 | cut -f 1)
  duration=$(ffprobe -sexagesimal -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $shortfile.mp4 | cut -f 1 -d '.')
  #fdate=$((date -r $shortfile.mp4 +"%d/%m/%y"))
  fdate=`date -r $shortfile.mp4 +"%d/%m/%y"`
  #echo "$shortfile --> $sizeH --> $duration --> $fdate"

  echo "<div class="video-item">" >> index.html
  echo "  <a href="$shortfile.mkv" download>" >> index.html
  echo "    <div class="video-preview">" >> index.html
  echo "      <video controls preload="none" poster="/$shortfile.jpg" width="220px"><source src="/$shortfile.mp4" /></video>" >> index.html
  echo "      <div class="video-details">" >> index.html
  echo "        <span>$duration</span>" >> index.html
  echo "        <span>$sizeH</span>" >> index.html
  echo "      </div>" >> index.html
  echo "    </div>" >> index.html
  echo "  </a>" >> index.html
  echo "  <div class="video-info">" >> index.html
  echo "    <div class="video-meta">" >> index.html
  echo "      Date: $fdate" >> index.html
  echo "    </div>" >> index.html
  echo "  </div>" >> index.html
  echo "</div>" >> index.html
done

echo "</div></div></body> </html>" >> index.html
