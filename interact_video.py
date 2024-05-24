# -*- coding: utf-8 -*-
"""
Created on Fri May 24 11:24:54 2024

@author: CAMBRAY-LAGASSY E
"""
#PIP INSTALL MOVIEPY
from moviepy.editor import *
from IPython.display import Video

def interactVideo(Input, Output):

    clip = VideoFileClip(Input)
    ipython_display(clip, maxduration=3600)
        
    #Interaction sur la variable clip qui est notre vidéo initiale
    ##Changer le volume sonore, il est multiplié par la constante
    clip = clip.volumex(0.5)
    
    ##A UN TEMPS X TU PRENDS EN CAPTURE save_frame(self, filename, t=0, withmask=True)[source]
    
    #Écriture du fichier.mkv après toutes les changements souhaités
    clip.write_videofile(Output)

interactVideo("test.mkv", "output.mp4")
