import os
import glob
import pickle
import keyboard
import discord
import asyncio
import logging
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

class Logger:
    def __init__(self, name: str, log_file: str = 'lightboard.txt'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Create handlers
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Create formatters and add them to handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add handlers to the logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger


class OBSRecorder:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        #self.host: str = os.getenv("OBS_HOST", "localhost")
        self.host: str = "134.214.202.160"

        self.port: int = int(os.getenv("OBS_PORT", 4455))
        self.video_path: str = os.getenv("OBS_VIDEO_PATH", r'/home/user/Videos')
        self.client = obsws(self.host, self.port)
        self.client.connect()
        self.logger.info(f"Connected to OBS at {self.host}:{self.port}")

    def start_recording(self) -> None:
        self.client.call(obs_requests.StartRecord())
        self.logger.info("Started recording")

    def stop_recording(self) -> None:
        self.client.call(obs_requests.StopRecord())
        self.logger.info("Stopped recording")

    def disconnect(self) -> None:
        self.client.disconnect()
        self.logger.info("Disconnected from OBS")

    def find_latest_video(self) -> Optional[str]:
        video_files = glob.glob(os.path.join(self.video_path, '*.mkv'))
        if not video_files:
            return None
        latest_video = max(video_files, key=os.path.getmtime)
        self.logger.info(f"Latest video found: {latest_video}")
        return latest_video


class YouTubeUploader:
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.client_secrets_file: str = os.getenv("CLIENT_SECRETS_FILE", 'client_secret.json')
        self.token_file: str = os.getenv("TOKEN_FILE", 'token.pkl')
        self.credentials = self.get_credentials()
        self.youtube: Resource = build('youtube', 'v3', credentials=self.credentials)
        self.logger.info("YouTube client initialized")

    def get_credentials(self):
        try:
            with open(self.token_file, 'rb') as token:
                self.logger.info("Loaded credentials from token file")
                return pickle.load(token)
        except FileNotFoundError:
            self.logger.warning("Token file not found, creating new credentials")
            flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, self.SCOPES)
            credentials = flow.run_local_server(port=0)
            with open(self.token_file, 'wb') as token:
                pickle.dump(credentials, token)
            self.logger.info("New credentials saved to token file")
            return credentials

    def upload_video(self, video_file: str) -> str:
        body = {
            'snippet': {'title': 'Video TC INSA Lyon', 'description': '', 'tags': ['tag1', 'tag2']},
            'status': {'privacyStatus': 'unlisted'}
        }
        media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
        response = self.youtube.videos().insert(part='snippet,status', body=body, media_body=media).execute()
        video_id = response['id']
        self.logger.info(f"Video uploaded to YouTube: {video_id}")
        return f'https://www.youtube.com/watch?v={video_id}'


class DiscordNotifier:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.channel_id: int = int(os.getenv("DISCORD_CHANNEL_ID", "1242449552850681958"))
        self.bot_token: str = os.getenv("DISCORD_BOT_TOKEN", "")
        self.logger.info("Discord notifier initialized")

    async def send_message(self, message: str) -> None:
        intents = discord.Intents.default()
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready() -> None:
            channel = client.get_channel(self.channel_id)
            if channel:
                await channel.send(message)
                self.logger.info(f"Message sent to Discord channel {self.channel_id}")
            else:
                self.logger.error("The channel ID is incorrect, right-click the channel to get the ID")
            await client.close()

        await client.start(self.bot_token)

    def send_discord_message(self, url: str) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        message = f"Here is the URL of the latest video that has been published: \n{url}"
        loop.run_until_complete(self.send_message(message))


class RecordingApp:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.obs_recorder = OBSRecorder(logger)
        self.youtube_uploader = YouTubeUploader(logger)
        self.discord_notifier = DiscordNotifier(logger)
        self.gui_queue: queue.Queue = queue.Queue()
        self.root, self.label = self.create_status_window()

    def create_status_window(self) -> Tuple[Tk, Label]:
        root = Tk()
        root.geometry("400x100")
        root.overrideredirect(True)
        root.configure(background='white')  # Set the background color to white
        root.geometry(f"{400}x{100}+{root.winfo_screenwidth() - 400}+{root.winfo_screenheight() - 100}")
        label = Label(root, text="", font=("Cambria", 50), bg='white')  # Set widget background color to white
        label.pack()
        return root, label

    def update_status(self, message: str, status: str, color: str) -> None:
        self.label.config(text=message, fg=color)
        self.root.update()
        self.logger.info(f"Status updated: {message}")

    def process_gui_queue(self) -> None:
        while not self.gui_queue.empty():
            task = self.gui_queue.get()
            if task[0] == "update_status":
                self.update_status(task[1], task[2], task[3])
            elif task[0] == "upload_video":
                self.upload_video()
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
                self.logger.error("No video file found for upload")
                return
            video_url = self.youtube_uploader.upload_video(video_file)
            self.logger.info(f"Video URL: {video_url}")
            self.discord_notifier.send_discord_message(video_url)
        except googleapiclient.errors.ResumableUploadError as e:
            self.logger.error("Google API quota exceeded. Unable to upload video.")
            self.update_status("Google quota exceeded", "ERROR", "red")
            time.sleep(5)
            self.obs_recorder.disconnect()
            exit()
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            self.update_status("An unexpected error occurred", "ERROR", "red")
            time.sleep(5)
            self.obs_recorder.disconnect()
            exit()

    def on_press(self, event: KeyboardEvent) -> None:
        if event.name == '1':
            self.logger.info("Record key pressed: starting recording")
            self.start_recording()
        elif event.name == '2':
            self.logger.info("Stop key pressed: stopping recording")
            self.stop_recording()
        elif event.name == '3':
            print("Quit key pressed")
            keyboard.unhook_all()
            self.obs_recorder.disconnect()
            self.gui_queue.put(("quit",))
            exit()

    def run(self) -> None:
        keyboard_thread = threading.Thread(target=lambda: keyboard.on_press(self.on_press))
        keyboard_thread.daemon = True
        keyboard_thread.start()
        self.root.after(100, self.process_gui_queue)
        self.root.mainloop()


if __name__ == "__main__":
    app_logger = Logger(__name__).get_logger()
    app_logger.info(f"Status avant lancer mon object RecordingApp")
    app = RecordingApp(app_logger)
    app.run()
