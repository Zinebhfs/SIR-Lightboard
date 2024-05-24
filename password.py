# -*- coding: utf-8 -*-
"""
Created on Tue May 24 9:0:51 2024

@author: CAMBRAY-LAGASSY E
"""
import random
import string
from tkinter import *

def getPassword():
    #Définir les caractères à utiliser pour la génération
    str = string.ascii_letters
    #Génération du mot de passe aléatoire sur 10 caractères
    return ''.join(random.choice(str) for i in range(10))
    
def close_window():
    #Destruction de la fenêtre
    fen.destroy()

def showPassword(password):
    #Titre de la fenêtre
    fen.title("Mot de passe pour accéder à la vidéo")
    #Dimensionnement de la fenêtre
    fen.geometry("800x150")
    #Disposition, du mot de passe, dans le bon format
    myPassword=StringVar()
    myPassword.set(password)
    #Interaction avec la fenêtre
    texteLabel = Label(fen, textvariable = myPassword, font=("Cambria", 80))
    texteLabel.pack()
    fen.after(30000, close_window)
    fen.mainloop()
    

fen=Tk()
password = getPassword()
showPassword(password)
