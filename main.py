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
from keyboard import KeyboardEvent
import subprocess

# Load environment variables from .env file
load_dotenv()

TXT_LOG_FILE = 'lightboard.txt'
TXT_CONSOLE_HANDLER_LEVEL = logging.DEBUG
TXT_FILE_HANDLER_LEVEL = logging.DEBUG
TXT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
TXT_LOGGER_STARTING_APP = 'Starting Lightboard app...'
TXT_LOGGER_PAUSE_RECORD= 'Recording paused'
TXT_LOGGER_RESUME_RECORD = 'Recording resumed'
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
TXT_DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "1242449552850681958"))
TXT_DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
TXT_DISCORD_INIT = 'Discord notifier initialized'
TXT_DISCORD_MSG_SENT = 'Message sent to Discord channel {channel_id}'
TXT_DISCORD_CHANNEL_ERROR = 'The channel ID is incorrect, right-click the channel to get the ID'
TXT_DISCORD_MSG_TEMPLATE = "Votre vidéo est accessible grâce à l'URL suivant : \n{url}"
TXT_GUI_WAITING = 'EN ATTENTE'
TXT_GUI_IN_PROGRESS = 'EN COURS'
TXT_GUI_COMPLETED = 'TERMINÉ'
TXT_GUI_ERROR = 'ERROR'
TXT_GUI_PAUSE= 'PAUSE'
TXT_GUI_GOOGLE_QUOTA_ERROR = 'Google quota exceeded'
TXT_GUI_UNEXPECTED_ERROR = 'An unexpected error occurred'


nest_asyncio.apply()


class Logger:
    """
    A custom logger class that sets up logging to both console and file.
    
    Attributes:
        logger (logging.Logger): The logger instance.
    """
    def __init__(self, name: str, log_file: str = TXT_LOG_FILE):
        """
        Initializes the Logger with a specific name and optional log file.
        
        Args:
            name (str): The name of the logger.
            log_file (str): The file to log messages to.
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Create console handler for logging
        console_handler = logging.StreamHandler()
        console_handler.setLevel(TXT_CONSOLE_HANDLER_LEVEL)

        # Create file handler for logging
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(TXT_FILE_HANDLER_LEVEL)

        # Create formatters and add them to handlers
        formatter = logging.Formatter(TXT_LOG_FORMAT)
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add handlers to the logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def get_logger(self):
        """
        Returns the logger instance.
        
        Returns:
            logging.Logger: The logger instance.
        """
        return self.logger

class OBSRecorder:
    """
    A class to manage OBS recording operations.

    Attributes:
        logger (logging.Logger): The logger instance.
        host (str): The OBS host.
        port (int): The OBS port.
        video_path (str): The path to save the recorded videos.
        client (obsws): The OBS WebSocket client.
    """
    def __init__(self, logger: logging.Logger):
        """
        Initializes the OBSRecorder with a logger instance.
        
        Args:
            logger (logging.Logger): The logger instance.
        """
        self.logger = logger
        self.host: str = TXT_OBS_HOST
        self.port: int = TXT_OBS_PORT
        self.video_path: str = TXT_OBS_VIDEO_PATH
        self.client = obsws(self.host, self.port)
        self.recording_state = 0  # 0: not recording, 1: recording
        self.pause_resume_counter = 0  # Compteur pour suivre les basculements pause/reprise

        self.connect_with_retry()
        
    def connect_with_retry(self, retries: int = 30, delay: int = 1) -> None:
        """
        Attempts to connect to the OBS WebSocket server with retries.
        
        Args:
            retries (int): Number of retries before giving up.
            delay (int): Delay between retries in seconds.
        """
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
        """
        Starts the OBS recording.
        """
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
        """
        Stops the OBS recording.
        """
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
                response = self.client.call(obs_requests.PauseRecord())
                if response.status == "ok":
                    self.logger.info(TXT_LOGGER_PAUSE_RECORD)
                else:
                    self.logger.error(f"Erreur lors de la mise en pause de l'enregistrement : {response.status} - {response.datain}")
            else:
                response = self.client.call(obs_requests.ResumeRecord())
                if response.status == "ok":
                    self.logger.info(TXT_LOGGER_RESUME_RECORD)
                else:
                    self.logger.error(f"Erreur lors de la reprise de l'enregistrement : {response.status} - {response.datain}")
        except Exception as e:
            self.logger.error(f"Erreur lors de la bascule pause/reprise de l'enregistrement : {e}")

    def disconnect(self) -> None:
        """
        Disconnects the OBS WebSocket client.
        """
        self.client.disconnect()
        self.logger.info(TXT_OBS_DISCONNECTED)

    def find_latest_video(self) -> Optional[str]:
        """
        Finds the latest recorded video file.
        
        Returns:
            Optional[str]: The path to the latest video file, or None if no files are found.
        """
        video_files = glob.glob(os.path.join(self.video_path, '*.mkv'))
        if not video_files:
            return None
        latest_video = max(video_files, key=os.path.getmtime)
        self.logger.info(TXT_OBS_LATEST_VIDEO.format(video=latest_video))
        return latest_video

    def find_latest_image(self) -> Optional[str]:
        image_files = glob.glob(os.path.join(self.video_path, '*.png'))
        if not image_files:
            return None
        latest_image = max(image_files, key=os.path.getmtime)
        self.logger.info(f"Latest image found: {latest_image}")
        return latest_image

class YouTubeUploader:
    """
    A class to manage video uploads to YouTube.

    Attributes:
        logger (logging.Logger): The logger instance.
        client_secrets_file (str): The path to the client secrets file.
        token_file (str): The path to the token file.
        credentials: The credentials for the YouTube API.
        youtube (Resource): The YouTube API client.
    """

    def __init__(self, logger: logging.Logger):
        """
        Initializes the YouTubeUploader with a logger instance.
        
        Args:
            logger (logging.Logger): The logger instance.
        """
        self.logger = logger
        self.client_secrets_file: str = TXT_YT_CLIENT_SECRETS_FILE
        self.token_file: str = TXT_YT_TOKEN_FILE
        self.credentials = self.get_credentials()
        self.youtube: Resource = build('youtube', 'v3', credentials=self.credentials)
        self.logger.info(TXT_YT_CLIENT_INIT)

    def get_credentials(self):
        """
        Retrieves the credentials for the YouTube API, loading them from a file or creating new ones if not found.
        
        Returns:
            Credentials: The credentials for the YouTube API.
        """
        try:
            with open(self.token_file, 'rb') as token:
                self.logger.info(TXT_YT_CREDENTIALS_LOADED)
                return pickle.load(token)
        except FileNotFoundError:
            self.logger.warning(TXT_YT_TOKEN_NOT_FOUND)
            flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, TXT_YT_SCOPES)
            credentials = flow.run_local_server(port=0)
            with open(self.token_file, 'wb') as token:
                pickle.dump(credentials, token)
            self.logger.info(TXT_YT_CREDENTIALS_SAVED)
            return credentials

    def upload_video(self, video_file: str) -> str:
        """
        Uploads a video to YouTube.
        
        Args:
            video_file (str): The path to the video file to upload.
        
        Returns:
            str: The URL of the uploaded video.
        """
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
    """
    A class to manage sending notifications to a Discord channel.

    Attributes:
        logger (logging.Logger): The logger instance.
        channel_id (int): The Discord channel ID.
        bot_token (str): The Discord bot token.
    """
    def __init__(self, logger: logging.Logger):
        """
        Initializes the DiscordNotifier with a logger instance.
        
        Args:
            logger (logging.Logger): The logger instance.
        """
        self.logger = logger
        self.channel_id: int = int(TXT_DISCORD_CHANNEL_ID)
        self.bot_token: str = TXT_DISCORD_BOT_TOKEN
        self.logger.info(TXT_DISCORD_INIT)

    async def send_message(self, message: str, image: str) -> None:
        """
        Sends a message to the Discord channel.
        
        Args:
            message (str): The message to send.
        """
        intents = discord.Intents.default()
        intents.messages = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready() -> None:
            channel = client.get_channel(self.channel_id)
            if channel:
                if not image:
                    await channel.send(message)
                    self.logger.info(TXT_DISCORD_MSG_SENT.format(channel_id=self.channel_id))
                else:
                    await channel.send(message,file=discord.File(image))
                    self.logger.info(TXT_DISCORD_MSG_SENT.format(channel_id=self.channel_id))
                await channel.send(message)
                self.logger.info(TXT_DISCORD_MSG_SENT.format(channel_id=self.channel_id))
            else:
                self.logger.error(TXT_DISCORD_CHANNEL_ERROR)
            await client.close()

        await client.start(self.bot_token)

    def send_discord_message(self, url: str) -> None:
        """
        Initiates the sending of a message to the Discord channel with the video URL.
        
        Args:
            url (str): The URL of the uploaded video.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.send_message(TXT_DISCORD_MSG_TEMPLATE.format(url=url)))

    def send_discord_image(self, path: str) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        message = f"Capture d'ecran de la vidéo en cours"
        loop.run_until_complete(self.send_message(message, path))

class RecordingApp:
    """
    A class to manage the recording, uploading, and notification process.

    Attributes:
        logger (logging.Logger): The logger instance.
        obs_recorder (OBSRecorder): The OBS recorder instance.
        youtube_uploader (YouTubeUploader): The YouTube uploader instance.
        discord_notifier (DiscordNotifier): The Discord notifier instance.
        gui_queue (queue.Queue): The GUI queue for status updates.
        root (Tk): The Tkinter root window.
        label (Label): The Tkinter label for status updates.
    """
    def __init__(self, logger: logging.Logger):
        """
        Initializes the RecordingApp with a logger instance.
        
        Args:
            logger (logging.Logger): The logger instance.
        """
        self.logger = logger
        self.obs_recorder = OBSRecorder(logger)
        self.youtube_uploader = YouTubeUploader(logger)
        self.discord_notifier = DiscordNotifier(logger)
        self.gui_queue: queue.Queue = queue.Queue()
        self.root, self.label = self.create_status_window()
        self.last_status_message = "Le dernier m"
        self.last_status_color = "blue"

    def create_status_window(self) -> Tuple[Tk, Label]:
        """
        Creates the status window for the GUI.
        
        Returns:
            Tuple[Tk, Label]: The Tkinter root window and label for status updates.
        """
        root = Tk()
        root.geometry("400x100")
        root.overrideredirect(True)
        root.configure(background='white')  # Set the background color to white
        root.geometry(f"{400}x{100}+{root.winfo_screenwidth() - 400}+{root.winfo_screenheight() - 100}")
        label = Label(root, text=TXT_GUI_WAITING, font=("Multicolore", 45), bg='white')  # Set widget background color to white
        label.pack()
        return root, label
    
    def update_status(self, message: str, status: str, color: str) -> None:
        """
        Updates the status message in the GUI.
        
        Args:
            message (str): The status message.
            status (str): The status indicator.
            color (str): The color of the status message.
        """
        self.label.config(text=message, fg=color)
        self.root.update()
        self.logger.info(f"Status updated: {message}")

    def process_gui_queue(self) -> None:
        """
        Processes the GUI queue for status updates.
        """
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
        """
        Starts the OBS recording and updates the status.
        """
        self.obs_recorder.start_recording()
        if self.obs_recorder.pause_resume_counter % 2 == 1:
            self.gui_queue.put(("update_status", TXT_GUI_PAUSE, "PAUSE", "blue"))
        else:
            self.gui_queue.put(("update_status", TXT_GUI_IN_PROGRESS, "IN PROGRESS", "green"))

    def stop_recording(self) -> None:
        """
        Stops the OBS recording, updates the status, and initiates video upload.
        """
        self.obs_recorder.stop_recording()
        self.gui_queue.put(("update_status", TXT_GUI_COMPLETED, "COMPLETED", "red"))
        self.gui_queue.put(("upload_video",))

    def upload_video(self) -> None:
        """
        Uploads the latest recorded video to YouTube and sends a notification to Discord.
        """
        try:
            video_file = self.obs_recorder.find_latest_video()
            if not video_file:
                self.logger.error("No video file found for upload")
                return

            # Wait for obs to render all the video before uploading
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

    def on_press(self, event: KeyboardEvent) -> None:
        """
        Handles keyboard events to start and stop recording.
        
        Args:
            event (KeyboardEvent): The keyboard event.
        """
        if event.name == '"' or event.name == '3':
            self.logger.info("Record key pressed: starting recording")
            self.start_recording()
        elif event.name == 'é' or event.name == '2':
            self.logger.info("Stop key pressed: stopping recording")
            self.stop_recording()
        elif event.name == '&' or event.name == '1':
            self.capture_screenshot()
        time.sleep(0.5)

    def capture_screenshot(self) -> None:
        screenshot_path = os.path.join(self.obs_recorder.video_path, f"screenshot_{int(time.time())}.png")
        self.gui_queue.put(("update_status","SCREENSHOT", "SCREENSHOT", "green"))
        subprocess.run(["gnome-screenshot", "-f", screenshot_path])
        self.root.after(3000, lambda: self.gui_queue.put(("update_status", self.last_status_message, self.last_status_message, self.last_status_color)))
        image_file = self.obs_recorder.find_latest_image()
        if not image_file:
            self.logger.error("No image file found for upload")
            return
        self.discord_notifier.send_discord_image(image_file)

    def run(self) -> None:
        """
        Runs the recording application, setting up keyboard event handling and the GUI loop.
        """
        keyboard_thread = threading.Thread(target=lambda: keyboard.on_press(self.on_press))
        keyboard_thread.daemon = True
        keyboard_thread.start()
        self.root.after(100, self.process_gui_queue)
        self.root.mainloop()

if __name__ == "__main__":
    app_logger = Logger(__name__).get_logger()
    app_logger.info(TXT_LOGGER_STARTING_APP)
    app = RecordingApp(app_logger)
    app.run()