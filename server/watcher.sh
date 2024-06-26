#!/bin/bash

cont=false

tee index.html<<EOF
<html>
<head>
<style>
.center {
  display: flex;
  justify-content: start;
  align-items: center;
  text-decoration: none;
}

.center video {
  margin-right: 8px;
}
</style>
</head>

<body>
Bienvenue sur wired, vous pouvez récupérez votre vidéo pour la traiter ou la transférer où vous le souhaitez. <br>
Par exemple : https://videos.insa-lyon.fr
<br>

Les vidéos sont supprimées tous les matins à 4h.
<br>

<table>
<tr><td class=center><video controls width=250> <source src=/download/720p.mp4 /> </video><div></td></tr>
EOF

for file in `ls download/*.lock`
do
  tmp=$(echo $file | sed s/\.lock//)  
  shortfile=$(echo $tmp | sed s/\.mkv//)  
  sshortfile=$(echo $shortfile | sed s/download\\///)
  cp /tmp/$sshortfile.mkv download/$sshortfile.mkv
  ffmpeg -i $shortfile.mkv -codec copy "$shortfile.mp4" -loglevel error
done
rm -f download/*.lock

for file in `ls -t download/*.mkv`
do
  shortfile=$(echo $file | sed s/\.mkv//)  
  sshortfile=$(echo $shortfile | sed s/download\\///)
  echo "<tr><td class=center><video controls width="250"> <source src="/$shortfile.mp4" /> </video><div> ou au format <a href="/$shortfile.mkv">mkv</a></div></td></tr>" >> index.html

done

echo "</table></body></html>" >> index.html
