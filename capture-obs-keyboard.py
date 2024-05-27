import os
import glob
import json
import requests
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from obswebsocket import obsws, requests as obs_requests
import keyboard  

OBS_HOST = "localhost"
OBS_PORT = 4455
CLIENT_SECRETS_FILE = 'client_secret.json'
TOKEN_FILE = 'token.pkl'
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
WEBHOOK_URL = 'https://discord.com/api/webhooks/1242472660013813880/c1f5qb5joOtRlBjqxMhRQe9k9X5Q_0YHU0rA3FUbl_mgtlnV9Cz3i50-uqKbwJHGeYKZ'
VIDEO_FOLDER = '/home/user/Videos'  

def find_latest_video(directory_path):
    video_files = glob.glob(os.path.join(directory_path, '*.mkv'))
    if not video_files:
        return None
    return max(video_files, key=os.path.getmtime)

client_obs = obsws(OBS_HOST, OBS_PORT)
client_obs.connect()

try:
    with open(TOKEN_FILE, 'rb') as token:
        credentials = pickle.load(token)
except FileNotFoundError:
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_local_server(port=0)
    with open(TOKEN_FILE, 'wb') as token:
        pickle.dump(credentials, token)
youtube = build('youtube', 'v3', credentials=credentials)

def start_recording():
    client_obs.call(obs_requests.StartRecord())

def stop_recording():
    client_obs.call(obs_requests.StopRecord())

def upload_video():
    video_file = find_latest_video(VIDEO_FOLDER)
    if not video_file:
        return
    body = {
        'snippet': {'title': 'Vidéo TC INSA Lyon', 'description': '', 'tags': ['tag1', 'tag2']},
        'status': {'privacyStatus': 'unlisted'}
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
    response = youtube.videos().insert(part='snippet,status', body=body, media_body=media).execute()
    video_id = response['id']
    video_url = f'https://www.youtube.com/watch?v={video_id}'
    print("Lien de la vidéo:", video_url)
    send_discord_notification(video_url)

def send_discord_notification(video_url):
    data = {"content": f'Regardez la nouvelle vidéo disponible : {video_url}', "username": "Bot Lightboard"}
    result = requests.post(WEBHOOK_URL, json=data)
    print(result.text)

def on_press(event):
    if event.name == '1':
        print("Touche 'record' pressée : démarrage de l'enregistrement")
        start_recording()
    elif event.name == '2':
        print("Touche 'stop' pressée : arrêt de l'enregistrement")
        stop_recording()
        upload_video()
    elif event.name == '3':
        print("Touche pressée : quitter")
        keyboard.unhook_all()
        client_obs.disconnect()

return video_url
keyboard.on_press(on_press)

keyboard.wait('esc')