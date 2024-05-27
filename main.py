import os
import glob
import pickle
import keyboard
import discord
import asyncio
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from obswebsocket import obsws, requests as obs_requests
from dotenv import load_dotenv
from tkinter import Tk, Label
import nest_asyncio
import threading
import queue
from keyboard import KeyboardEvent

nest_asyncio.apply()

OBS_HOST = "192.168.1.22"
OBS_PORT = 4455
CLIENT_SECRETS_FILE = 'client_secret.json'
TOKEN_FILE = 'token.pkl'
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
VIDEO_FOLDER = r'C:\Users\alain\Videos'

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

def find_latest_video(directory_path):
    video_files = glob.glob(os.path.join(directory_path, '*.mkv'))
    if not video_files:
        return None
    return max(video_files, key=os.path.getmtime)

client_obs = obsws(OBS_HOST, OBS_PORT)
client_obs.connect()

# YouTube OAuth2 setup
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
    gui_queue.put(("update_status", "Recording started!", "IN PROGRESS", "green"))

def stop_recording():
    client_obs.call(obs_requests.StopRecord())
    gui_queue.put(("update_status", "Recording stopped!", "COMPLETED", "red"))
    gui_queue.put(("upload_video",))

def upload_video():
    video_file = find_latest_video(VIDEO_FOLDER)
    if not video_file:
        return
    body = {
        'snippet': {'title': 'Video TC INSA Lyon', 'description': '', 'tags': ['tag1', 'tag2']},
        'status': {'privacyStatus': 'unlisted'}
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
    response = youtube.videos().insert(part='snippet,status', body=body, media_body=media).execute()
    video_id = response['id']
    video_url = f'https://www.youtube.com/watch?v={video_id}'
    print("Video URL:", video_url)
    send_discord_message(video_url)

def on_press(event: KeyboardEvent):
    if event.name == '1':
        print("Record key pressed: starting recording")
        start_recording()
    elif event.name == '2':
        print("Stop key pressed: stopping recording")
        stop_recording()
    elif event.name == '3':
        print("Quit key pressed")
        keyboard.unhook_all()
        client_obs.disconnect()
        gui_queue.put(("quit",))
        exit()

# Tkinter pop-up to show status
def create_status_window():
    root = Tk()
    root.title("Status")
    root.geometry("800x150")
    root.attributes('-topmost', True)
    root.geometry(f"{1000}x{200}+{root.winfo_screenwidth() - 1000}+{root.winfo_screenheight() - 200}")
    label = Label(root, text="", font=("Cambria", 80))
    label.pack()
    return root, label

def update_status(message, status, color):
    label.config(text=message, fg=color)
    root.update()

def process_gui_queue():
    while not gui_queue.empty():
        task = gui_queue.get()
        if task[0] == "update_status":
            update_status(task[1], task[2], task[3])
        elif task[0] == "upload_video":
            pass
            #upload_video()
        elif task[0] == "quit":
            root.quit()
    root.after(100, process_gui_queue)

root, label = create_status_window()

# Discord bot function
async def send_message_to_channel(channel_id, message):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(channel_id)
        if channel:
            await channel.send(message)
        else:
            print("The channel ID is incorrect, right-click the channel to get the ID")
        await client.close()

    await client.start(BOT_TOKEN)

def send_discord_message(url):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    message = f"Here is the URL of the latest video that has been published: \n{url}"
    loop.run_until_complete(send_message_to_channel(CHANNEL_ID, message))

gui_queue = queue.Queue()

keyboard_thread = threading.Thread(target=lambda: keyboard.on_press(on_press))
keyboard_thread.daemon = True
keyboard_thread.start()

root.after(100, process_gui_queue)
root.mainloop()
