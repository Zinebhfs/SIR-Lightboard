# -*- coding: utf-8 -*-

import random
import string
from tkinter import *
import time

def getPassword():
    #Définir les caractères à utiliser pour la génération
    str = string.ascii_letters
    #Génération du mot de passe aléatoire sur 10 caractères
    return ''.join(random.choice(str) for i in range(10))
    
def close_window():
    #Destruction de la fenêtre
    fen.destroy()
    
def showStatus(title, status, color):
    #Titre de la fenêtre
    fen.title(title)
    #Dimensionnement de la fenêtre
    fen.geometry("800x150")
    myMsg=StringVar()
    myMsg.set(status)
    texteLabel = Label(fen, textvariable = myMsg, font=("Cambria", 80), fg=color)
    texteLabel.pack()
    fen.after(5000, close_window)
    
    #Placement de la fenêtre en bas à droite
    screen_width = fen.winfo_screenwidth()
    screen_height = fen.winfo_screenheight()
    x_position = screen_width - 1000
    y_position = screen_height - 200
    fen.geometry(f"{1000}x{200}+{x_position}+{y_position}")

    fen.mainloop()

password = getPassword()
fen=Tk()
showStatus("L'enregistrement est en cours !", "EN COURS", "green")
fen=Tk()
showStatus("L'enregistrement est terminé !", "TERMINÉ", "red")
fen=Tk()
showStatus("Mot de passe pour accéder à la vidéo !", password, "black")
