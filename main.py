import os
import glob
import pickle
import keyboard
import discord
import asyncio
from typing import Optional, Tuple
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaFileUpload
import googleapiclient.errors
from obswebsocket import obsws, requests as obs_requests
from dotenv import load_dotenv
from tkinter import Tk, Label
import nest_asyncio
import threading
import queue
from keyboard import KeyboardEvent
import time
nest_asyncio.apply()

# Load environment variables
load_dotenv()


class OBSRecorder:
    def __init__(self):
        self.host: str = os.getenv("OBS_HOST", "localhost")
        self.port: int = int(os.getenv("OBS_PORT", 4455))
        self.video_path: str = os.getenv("OBS_VIDEO_PATH", r'/home/user/Videos')
        self.client = obsws(self.host, self.port)
        self.client.connect()

    def start_recording(self) -> None:
        self.client.call(obs_requests.StartRecord())

    def stop_recording(self) -> None:
        self.client.call(obs_requests.StopRecord())

    def disconnect(self) -> None:
        self.client.disconnect()

    def find_latest_video(self) -> Optional[str]:
        video_files = glob.glob(os.path.join(self.video_path, '*.mkv'))
        if not video_files:
            return None
        return max(video_files, key=os.path.getmtime)


class YouTubeUploader:
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

    def __init__(self):
        self.client_secrets_file: str = os.getenv("CLIENT_SECRETS_FILE", 'client_secret.json')
        self.token_file: str = os.getenv("TOKEN_FILE", 'token.pkl')
        self.credentials = self.get_credentials()
        self.youtube: Resource = build('youtube', 'v3', credentials=self.credentials)

    def get_credentials(self):
        try:
            with open(self.token_file, 'rb') as token:
                return pickle.load(token)
        except FileNotFoundError:
            flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, self.SCOPES)
            credentials = flow.run_local_server(port=0)
            with open(self.token_file, 'wb') as token:
                pickle.dump(credentials, token)
            return credentials

    def upload_video(self, video_file: str) -> str:
        body = {
            'snippet': {'title': 'Video TC INSA Lyon', 'description': '', 'tags': ['tag1', 'tag2']},
            'status': {'privacyStatus': 'unlisted'}
        }
        media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
        response = self.youtube.videos().insert(part='snippet,status', body=body, media_body=media).execute()
        video_id = response['id']
        return f'https://www.youtube.com/watch?v={video_id}'


class DiscordNotifier:
    def __init__(self):
        self.channel_id: int = int(os.getenv("DISCORD_CHANNEL_ID", "1242449552850681958"))
        self.bot_token: str = os.getenv("DISCORD_BOT_TOKEN", "")

    async def send_message(self, message: str) -> None:
        intents = discord.Intents.default()
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready() -> None:
            channel = client.get_channel(self.channel_id)
            if channel:
                await channel.send(message)
            else:
                print("The channel ID is incorrect, right-click the channel to get the ID")
            await client.close()

        await client.start(self.bot_token)

    def send_discord_message(self, url: str) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        message = f"Here is the URL of the latest video that has been published: \n{url}"
        loop.run_until_complete(self.send_message(message))


class RecordingApp:
    def __init__(self):
        self.obs_recorder = OBSRecorder()
        self.youtube_uploader = YouTubeUploader()
        self.discord_notifier = DiscordNotifier()
        self.gui_queue: queue.Queue = queue.Queue()
        self.root, self.label = self.create_status_window()

    def create_status_window(self) -> Tuple[Tk, Label]:
        root = Tk()
        root.geometry("400x100")
        root.attributes('-topmost', True)
        root.overrideredirect(True)
        root.wm_attributes('-transparentcolor', root['bg'])
        root.geometry(f"{400}x{100}+{root.winfo_screenwidth() - 400}+{root.winfo_screenheight() - 100}")
        label = Label(root, text="", font=("Cambria", 50))
        label.pack()
        return root, label

    def update_status(self, message: str, status: str, color: str) -> None:
        self.label.config(text=message, fg=color)
        self.root.update()

    def process_gui_queue(self) -> None:
        while not self.gui_queue.empty():
            task = self.gui_queue.get()
            if task[0] == "update_status":
                self.update_status(task[1], task[2], task[3])
            elif task[0] == "upload_video":
                pass
                # self.upload_video()
            elif task[0] == "quit":
                self.root.quit()
        self.root.after(100, self.process_gui_queue)

    def start_recording(self) -> None:
        self.obs_recorder.start_recording()
        self.gui_queue.put(("update_status", "EN COURS", "IN PROGRESS", "green"))

    def stop_recording(self) -> None:
        self.obs_recorder.stop_recording()
        self.gui_queue.put(("update_status", "TERMINÉ", "COMPLETED", "red"))
        self.gui_queue.put(("upload_video",))

    def upload_video(self) -> None:
        try:
            video_file = self.obs_recorder.find_latest_video()
            if not video_file:
                return
            video_url = self.youtube_uploader.upload_video(video_file)
            print("Video URL:", video_url)
            self.discord_notifier.send_discord_message(video_url)
        except googleapiclient.errors.ResumableUploadError as e:
            print("Google API quota exceeded. Unable to upload video.")
            # Handle gracefully, display message, cleanup, etc.
            self.update_status("Google quota exceeded", "ERROR", "red")
            time.sleep(5)
            self.obs_recorder.disconnect()
            exit()
        except Exception as e:
            print("An unexpected error occurred:", e)
            # Handle gracefully, display message, cleanup, etc.
            self.update_status("An unexpected error occurred", "ERROR", "red")
            time.sleep(5)
            self.obs_recorder.disconnect()
            exit()

    def on_press(self, event: KeyboardEvent) -> None:
        if event.name == '1':
            print("Record key pressed: starting recording")
            self.start_recording()
        elif event.name == '2':
            print("Stop key pressed: stopping recording")
            self.stop_recording()


    def run(self) -> None:
        keyboard_thread = threading.Thread(target=lambda: keyboard.on_press(self.on_press))
        keyboard_thread.daemon = True
        keyboard_thread.start()
        self.root.after(100, self.process_gui_queue)
        self.root.mainloop()


if __name__ == "__main__":
    app = RecordingApp()
    app.run()
