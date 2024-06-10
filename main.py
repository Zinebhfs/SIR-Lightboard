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

load_dotenv()

# Text variables
TXT_LOG_FILE = 'lightboard.txt'
TXT_CONSOLE_HANDLER_LEVEL = logging.DEBUG
TXT_FILE_HANDLER_LEVEL = logging.DEBUG
TXT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
TXT_LOGGER_STARTING_APP = 'Starting Lightboard app...'
TXT_OBS_HOST = os.getenv("OBS_HOST", "localhost")
TXT_OBS_PORT = int(os.getenv("OBS_PORT", 4455))
TXT_OBS_VIDEO_PATH = os.getenv("OBS_VIDEO_PATH", r'/home/user/Videos')
TXT_OBS_CONNECTED = 'Connected to OBS at {host}:{port}'
TXT_OBS_FAILED_CONNECT = 'Failed to connect to OBS at {host}:{port}. Retrying in {delay} seconds...'
TXT_OBS_CONNECT_ERROR = 'Unable to connect to OBS at {host}:{port} after {retries * delay} seconds.'
TXT_OBS_START_RECORD = 'Started recording'
TXT_OBS_STOP_RECORD = 'Stopped recording'
TXT_OBS_DISCONNECTED = 'Disconnected from OBS'
TXT_OBS_LATEST_VIDEO = 'Latest video found: {video}'
TXT_YT_CLIENT_SECRETS_FILE = os.getenv("CLIENT_SECRETS_FILE", 'client_secret.json')
TXT_YT_TOKEN_FILE = os.getenv("TOKEN_FILE", 'token.pkl')
TXT_YT_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
TXT_YT_CLIENT_INIT = 'YouTube client initialized'
TXT_YT_CREDENTIALS_LOADED = 'Loaded credentials from token file'
TXT_YT_TOKEN_NOT_FOUND = 'Token file not found, creating new credentials'
TXT_YT_CREDENTIALS_SAVED = 'New credentials saved to token file'
TXT_YT_UPLOAD_TITLE = 'Video TC INSA Lyon'
TXT_YT_UPLOAD_DESCRIPTION = ''
TXT_YT_UPLOAD_TAGS = ['tag1', 'tag2']
TXT_YT_VIDEO_URL = 'https://www.youtube.com/watch?v={video_id}'
TXT_YT_VIDEO_UPLOADED = 'Video uploaded to YouTube: {video_id}'
TXT_DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "1242449552850681958"))
TXT_DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
TXT_DISCORD_INIT = 'Discord notifier initialized'
TXT_DISCORD_MSG_SENT = 'Message sent to Discord channel {channel_id}'
TXT_DISCORD_CHANNEL_ERROR = 'The channel ID is incorrect, right-click the channel to get the ID'
TXT_DISCORD_MSG_TEMPLATE = "Votre vidéo est accessible grâce à l'URL suivant : \n{url}"
TXT_GUI_WAITING = 'EN ATTENTE'
TXT_GUI_IN_PROGRESS = 'EN COURS'
TXT_GUI_COMPLETED = 'TERMINÉ'
TXT_GUI_PAUSE = 'PAUSE'
TXT_GUI_ERROR = 'ERROR'
TXT_GUI_GOOGLE_QUOTA_ERROR = 'Google quota exceeded'
TXT_GUI_UNEXPECTED_ERROR = 'An unexpected error occurred'

class Logger:
    def __init__(self, name: str, log_file: str = TXT_LOG_FILE):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(TXT_CONSOLE_HANDLER_LEVEL)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(TXT_FILE_HANDLER_LEVEL)

        formatter = logging.Formatter(TXT_LOG_FORMAT)
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger

class OBSRecorder:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.host: str = TXT_OBS_HOST
        self.port: int = TXT_OBS_PORT
        self.video_path: str = TXT_OBS_VIDEO_PATH
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
                self.logger.warning(TXT_OBS_FAILED_CONNECT.format(host=self.host, port=self.port, delay=delay))
                time.sleep(delay)
        
        if not connected:
            raise ConnectionError(TXT_OBS_CONNECT_ERROR.format(host=self.host, port=self.port, retries=retries, delay=delay))
        
        self.logger.info(TXT_OBS_CONNECTED.format(host=self.host, port=self.port))

    def start_recording(self) -> None:
        if self.recording_state == 0:
            try:
                self.client.call(obs_requests.StartRecord())
                self.recording_state = 1
                self.logger.info(TXT_OBS_START_RECORD)
            except Exception as e:
                self.logger.error(f"Erreur lors du démarrage de l'enregistrement : {e}")
        else:
            self.toggle_pause_resume_recording()

    def stop_recording(self) -> None:
        try:
            self.client.call(obs_requests.StopRecord())
            self.recording_state = 0
            self.pause_resume_counter = 0
            self.logger.info(TXT_OBS_STOP_RECORD)
        except Exception as e:
            self.logger.error(f"Erreur lors de l'arrêt de l'enregistrement : {e}")

    def toggle_pause_resume_recording(self) -> None:
        self.pause_resume_counter += 1
        try:
            if self.pause_resume_counter % 2 == 1:
                self.client.call(obs_requests.PauseRecord())
                self.logger.info("Enregistrement mis en pause")
            else:
                self.client.call(obs_requests.ResumeRecord())
                self.logger.info("Enregistrement repris")
        except Exception as e:
            self.logger.error(f"Erreur lors de la bascule pause/reprise de l'enregistrement : {e}")

    def disconnect(self) -> None:
        self.client.disconnect()
        self.logger.info(TXT_OBS_DISCONNECTED)

    def find_latest_video(self) -> Optional[str]:
        video_files = glob.glob(os.path.join(self.video_path, '*.mkv'))
        if not video_files:
            return None
        latest_video = max(video_files, key=os.path.getmtime)
        self.logger.info(TXT_OBS_LATEST_VIDEO.format(video=latest_video))
        return latest_video

class YouTubeUploader:
    SCOPES = TXT_YT_SCOPES

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.client_secrets_file: str = TXT_YT_CLIENT_SECRETS_FILE
        self.token_file: str = TXT_YT_TOKEN_FILE
        self.credentials = self.get_credentials()
        self.youtube: Resource = build('youtube', 'v3', credentials=self.credentials)
        self.logger.info(TXT_YT_CLIENT_INIT)

    def get_credentials(self):
        try:
            with open(self.token_file, 'rb') as token:
                self.logger.info(TXT_YT_CREDENTIALS_LOADED)
                return pickle.load(token)
        except FileNotFoundError:
            self.logger.warning(TXT_YT_TOKEN_NOT_FOUND)
            flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, self.SCOPES)
            credentials = flow.run_local_server(port=0)
            with open(self.token_file, 'wb') as token:
                pickle.dump(credentials, token)
            self.logger.info(TXT_YT_CREDENTIALS_SAVED)
            return credentials

    def upload_video(self, video_file: str) -> str:
        body = {
            'snippet': {
                'title': TXT_YT_UPLOAD_TITLE,
                'description': TXT_YT_UPLOAD_DESCRIPTION,
                'tags': TXT_YT_UPLOAD_TAGS
            },
            'status': {
                'privacyStatus': 'unlisted'
            }
        }
        media_body = MediaFileUpload(video_file, chunksize=-1, resumable=True)
        request = self.youtube.videos().insert(part='snippet,status', body=body, media_body=media_body)
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                self.logger.debug(f"Uploaded {int(status.progress() * 100)}%")
        self.logger.info(TXT_YT_VIDEO_UPLOADED.format(video_id=response['id']))
        return response['id']

class DiscordNotifier:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.token: str = TXT_DISCORD_BOT_TOKEN
        self.channel_id: int = TXT_DISCORD_CHANNEL_ID
        self.client = discord.Client(intents=discord.Intents.default())
        self.logger.info(TXT_DISCORD_INIT)

    async def send_message(self, message: str) -> None:
        @self.client.event
        async def on_ready():
            try:
                channel = self.client.get_channel(self.channel_id)
                await channel.send(message)
                self.logger.info(TXT_DISCORD_MSG_SENT.format(channel_id=self.channel_id))
            except Exception as e:
                self.logger.error(TXT_DISCORD_CHANNEL_ERROR)
            await self.client.close()

        await self.client.start(self.token)

    def notify(self, video_id: str) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.send_message(TXT_DISCORD_MSG_TEMPLATE.format(url=TXT_YT_VIDEO_URL.format(video_id=video_id))))

class GuiApp:
    def __init__(self):
        self.window = Tk()
        self.window.geometry("400x100")
        self.window.overrideredirect(True)
        self.window.configure(background='white')
        self.window.geometry(f"{400}x{100}+{self.window.winfo_screenwidth() - 400}+{self.window.winfo_screenheight() - 100}")
        self.window.title("Lightboard Status")
        self.label = Label(self.window, text=TXT_GUI_WAITING, font=("Multicolore", 45), bg='white')
        self.label.pack()

    def update_label(self, text: str, color: str) -> None:
        self.label.config(text=text, fg=color)
        self.window.update_idletasks()

    def run(self):
        self.window.mainloop()

class LightboardApp:
    def __init__(self):
        logger = Logger('LightboardApp').get_logger()
        logger.info(TXT_LOGGER_STARTING_APP)

        self.logger = logger
        self.gui = GuiApp()
        self.obs_recorder = OBSRecorder(logger)
        self.youtube_uploader = YouTubeUploader(logger)
        self.discord_notifier = DiscordNotifier(logger)

        self.event_queue = queue.Queue()

    def on_key_press(self, event: KeyboardEvent) -> None:
        if event.event_type == keyboard.KEY_DOWN:
            if event.name == '"':
                self.logger.debug('Start recording key pressed')
                self.event_queue.put('start')
            elif event.name == 'é':
                self.logger.debug('Stop recording key pressed')
                self.event_queue.put('stop')

    def process_events(self) -> None:
        while True:
            event = self.event_queue.get()
            if event == 'start':
                self.obs_recorder.start_recording()
                if self.obs_recorder.pause_resume_counter % 2 == 1:
                    self.gui.update_label(TXT_GUI_PAUSE, "yellow")
                else:
                    self.gui.update_label(TXT_GUI_IN_PROGRESS, "green")
            elif event == 'stop':
                self.obs_recorder.stop_recording()
                self.gui.update_label(TXT_GUI_COMPLETED, "red")
                latest_video = self.obs_recorder.find_latest_video()
                if latest_video:
                    try:
                        video_id = self.youtube_uploader.upload_video(latest_video)
                        self.discord_notifier.notify(video_id)
                    except googleapiclient.errors.HttpError as e:
                        if e.resp.status == 403:
                            self.gui.update_label(TXT_GUI_GOOGLE_QUOTA_ERROR, "red")
                        else:
                            self.gui.update_label(TXT_GUI_UNEXPECTED_ERROR, "red")
                        self.logger.error(f"Error uploading video: {e}")
                else:
                    self.logger.error("No video found to upload")

    def run(self) -> None:
        threading.Thread(target=self.process_events, daemon=True).start()
        keyboard.on_press(self.on_key_press)
        self.gui.run()

if __name__ == "__main__":
    app = LightboardApp()
    app.run()
