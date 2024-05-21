import obswebsocket
from obswebsocket import obsws, requests
from pynput import keyboard
import os
import requests as req
import json
import subprocess

# Config WebSocket OBS
host = "localhost"
port = 4455
password = "admin123" #mdp qu'on configure dans OBS Studio

ws = obsws(host, port, password)
ws.connect()

recording = False

def on_press(key):
    global recording
    try:
        if key.char == 'r' and not recording:
            ws.call(requests.StartRecording())
            recording = True
            print("Enregistrement démarré")
        elif key.char == 's' and recording:
            ws.call(requests.StopRecording())
            recording = False
            print("Enregistrement arrêté")
            # Attendre que l'enregistrement soit terminé
            while ws.call(requests.GetRecordStatus()).getRecording():
                pass
            upload_and_notify()
    except AttributeError:
        pass

def upload_and_notify():
    # Chemin de l'emplacement où sont enregistrées les vidéos
    video_path = "/home/..." #à compléter  

    # Uploader la vidéo via transfersh
    cmd = f"curl --upload-file {video_path} https://transfer.sh/{os.path.basename(video_path)}"
    upload_output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
    if "https://transfer.sh" in upload_output:
        print(f"Vidéo téléchargée : {upload_output}")
        # Envoyer le lien sur Discord
        notify_discord(upload_output)
    else:
        print("Erreur lors de l'upload de la vidéo")

def notify_discord(video_url):
    discord_webhook_url = "https://discord.com/api/webhooks/1242472660013813880/c1f5qb5joOtRlBjqxMhRQe9k9X5Q_0YHU0rA3FUbl_mgtlnV9Cz3i50-uqKbwJHGeYKZ"  # Remplacez par votre URL de webhook
    message = {
        "content": f"Nouvelle vidéo Lightboard disponible : {video_url}",
        "username": "Lightboard TC"
    }
    response = req.post(discord_webhook_url, json=message)
    if response.status_code == 204:
        print("Message envoyé sur Discord")
    else:
        print("Erreur lors de l'envoi du message sur Discord")

# Écouter les touches du clavier
listener = keyboard.Listener(on_press=on_press)
listener.start()
listener.join()
