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
import time
import subprocess

nest_asyncio.apply()

# Load environment variables from .env file
load_dotenv()

class Logger:
    def __init__(self, name: str, log_file: str = 'lightboard.txt'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger

class OBSRecorder:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.host: str = os.getenv("OBS_HOST", "localhost")
        self.port: int = int(os.getenv("OBS_PORT", 4455))
        self.video_path: str = os.getenv("OBS_VIDEO_PATH", r'/home/user/Videos')
        self.client = obsws(self.host, self.port)
        self.recording_state = 0
        self.pause_resume_counter = 0

        self.connect_with_retry()
        
    def connect_with_retry(self, retries: int = 30, delay: int = 1) -> None:
        connected = False
        for _ in range(retries):
            try:
                self.client.connect()
                connected = True
                break
            except Exception as e:
                self.logger.warning(f"Failed to connect to OBS at {self.host}:{self.port}. Retrying in {delay} seconds...")
                time.sleep(delay)
        
        if not connected:
            raise ConnectionError(f"Unable to connect to OBS at {self.host}:{self.port} after {retries * delay} seconds.")
        
        self.logger.info(f"Connected to OBS at {self.host}:{self.port}")

    def start_recording(self) -> None:
        if self.recording_state == 0:
            try:
                self.client.call(obs_requests.StartRecord())
                self.recording_state = 1
                self.logger.info("Enregistrement démarré")
            except Exception as e:
                self.logger.error(f"Erreur lors du démarrage de l'enregistrement : {e}")
        else:
            self.toggle_pause_resume_recording()

    def stop_recording(self) -> None:
        try:
            self.client.call(obs_requests.StopRecord())
            self.recording_state = 0
            self.pause_resume_counter = 0
            self.logger.info("Enregistrement arrêté")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'arrêt de l'enregistrement : {e}")

    def toggle_pause_resume_recording(self) -> None:
        self.pause_resume_counter += 1
        try:
            if self.pause_resume_counter % 2 == 1:
                response = self.client.call(obs_requests.PauseRecord())
                self.logger.info("Enregistrement mis en pause")
                self.capture_screenshot()
            else:
                response = self.client.call(obs_requests.ResumeRecord())
                self.logger.info("Enregistrement repris")
        except Exception as e:
            self.logger.error(f"Erreur lors de la bascule pause/reprise de l'enregistrement : {e}")

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

    def find_latest_image(self) -> Optional[str]:
        image_files = glob.glob(os.path.join(self.video_path, '*.png'))
        if not image_files:
            return None
        latest_image = max(image_files, key=os.path.getmtime)
        self.logger.info(f"Latest image found: {latest_image}")
        return latest_image

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
        #response = self.youtube.videos().insert(part='snippet,status', body=body, media_body=media).execute()
        #video_id = response['id']
        video_id = toto
        self.logger.info(f"Video uploaded to YouTube: {video_id}")
        return f'https://www.youtube.com/watch?v={video_id}'

class DiscordNotifier:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.channel_id: int = int(os.getenv("DISCORD_CHANNEL_ID", "1242449552850681958"))
        self.bot_token: str = os.getenv("DISCORD_BOT_TOKEN", "")
        self.logger.info("Discord notifier initialized")

    async def send_message(self, message: str, image: str) -> None:
        intents = discord.Intents.default()
        intents.messages = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready() -> None:
            channel = client.get_channel(self.channel_id)
            if channel:
                if not image:
                    await channel.send(message)
                    self.logger.info(f"Message sent to Discord channel {self.channel_id}")
                else:
                    await channel.send(message,file=discord.File(image))
                    self.logger.info(f"Message sent to Discord channel {self.channel_id}")
            else:
                self.logger.error("The channel ID is incorrect, right-click the channel to get the ID")
            await client.close()

        await client.start(self.bot_token)

    def send_discord_message(self, url: str) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        message = f"Votre vidéo est accessible grâce à l'URL suivant : \n{url}"
        loop.run_until_complete(self.send_message(message))

    def send_discord_image(self, path: str) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        message = f"Capture d'ecran de la vidéo en cours"
        loop.run_until_complete(self.send_message(message, path))

class RecordingApp:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.obs_recorder = OBSRecorder(logger)
        self.youtube_uploader = YouTubeUploader(logger)
        self.discord_notifier = DiscordNotifier(logger)
        self.gui_queue: queue.Queue = queue.Queue()
        self.root, self.label = self.create_status_window()
        self.last_status_message = "EN ATTENTE"  # Variable to keep track of the last status message
        self.last_status_color = "white"  # Variable to keep track of the last status color

    def create_status_window(self) -> Tuple[Tk, Label]:
        root = Tk()
        root.geometry("400x100")
        root.overrideredirect(True)
        root.configure(background='white')
        root.geometry(f"{400}x{100}+{root.winfo_screenwidth() - 400}+{root.winfo_screenheight() - 100}")
        label = Label(root, text="EN ATTENTE", font=("Multicolore", 45), bg='white')
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
        if self.obs_recorder.pause_resume_counter % 2 == 1:
            self.gui_queue.put(("update_status", "PAUSE", "PAUSE", "blue"))
        else:
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

            time.sleep(5)
            
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

    def on_press(self, event: keyboard.KeyboardEvent) -> None:
        if event.name == '"':
            self.logger.info("Record key pressed: starting recording")
            self.start_recording()
        elif event.name == 'é':
            self.logger.info("Stop key pressed: stopping recording")
            self.stop_recording()
        elif event.name == '&':
            self.capture_screenshot()

    def capture_screenshot(self) -> None:
        screenshot_path = os.path.join(self.obs_recorder.video_path, f"screenshot_{int(time.time())}.png")
        subprocess.run(["gnome-screenshot", "-f", screenshot_path])
        self.gui_queue.put(("update_status","SCREENSHOT", "SCREENSHOT", "green"))
        self.root.after(3000, lambda: self.gui_queue.put(("update_status", self.last_status_message, self.last_status_message, self.last_status_color)))
        image_file = self.obs_recorder.find_latest_image()
        if not image_file:
            self.logger.error("No image file found for upload")
            return
        self.discord_notifier.send_discord_image(image_file)

    def run(self) -> None:
        keyboard_thread = threading.Thread(target=lambda: keyboard.on_press(self.on_press))
        keyboard_thread.daemon = True
        keyboard_thread.start()
        self.root.after(100, self.process_gui_queue)
        self.root.mainloop()

if __name__ == "__main__":
    app_logger = Logger(__name__).get_logger()
    app_logger.info(f"Starting Lightboard app...")
    app = RecordingApp(app_logger)
    app.run()