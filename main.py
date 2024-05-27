from tkinter import *


#POUR LE FICHIER PASSWORD.PY C'EST BON JE GENERE BIEN MES FENETRES ETC... TOP
from password import showStatus, getPassword, close_window
#POUR LE FICHIER SCRIPT_BOT.PY C'EST BON J'IMPORTE BIEN MON BOT ET J'ENVOIE BIEN UN URL... TOP
from script_bot import sendURL

#INITIALISATION DES VARIABLES

password = getPassword()

#APPEL DES POP-UP
fen=Tk()
showStatus("L'enregistrement est en cours !", "EN COURS", "green")
fen=Tk()
showStatus("L'enregistrement est terminé !", "TERMINÉ", "red")
fen=Tk()
showStatus("Mot de passe pour accéder à la vidéo !", password, "black")

#ENVOI D'UN URL
#sendURL("https://google.com")