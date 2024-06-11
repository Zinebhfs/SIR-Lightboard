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

# Load environment variables from .env file
load_dotenv()

import logging

class Logger:
    """
    A custom logger class that sets up logging to both console and file.
    
    Attributes:
        logger (logging.Logger): The logger instance.
    """
    def __init__(self, name: str, log_file: str = 'lightboard.txt'):
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
        console_handler.setLevel(logging.DEBUG)

        # Create file handler for logging
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
        self.host: str = os.getenv("OBS_HOST", "localhost")
        self.port: int = int(os.getenv("OBS_PORT", 4455))
        self.video_path: str = os.getenv("OBS_VIDEO_PATH", r'/home/user/Videos')
        self.client = obsws(self.host, self.port)

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
                self.logger.warning(f"Failed to connect to OBS at {self.host}:{self.port}. Retrying in {delay} seconds...")
                time.sleep(delay)
        
        if not connected:
            raise ConnectionError(f"Unable to connect to OBS at {self.host}:{self.port} after {retries * delay} seconds.")
        
        self.logger.info(f"Connected to OBS at {self.host}:{self.port}")

    def start_recording(self) -> None:
        """
        Starts the OBS recording.
        """
        self.client.call(obs_requests.StartRecord())
        self.logger.info("Started recording")

    def stop_recording(self) -> None:
        """
        Stops the OBS recording.
        """
        self.client.call(obs_requests.StopRecord())
        self.logger.info("Stopped recording")

    def disconnect(self) -> None:
        """
        Disconnects the OBS WebSocket client.
        """
        self.client.disconnect()
        self.logger.info("Disconnected from OBS")

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
        self.logger.info(f"Latest video found: {latest_video}")
        return latest_video


class YouTubeUploader:
    """
    A class to manage video uploads to YouTube.

    Attributes:
        SCOPES (list): The scopes required for the YouTube API.
        logger (logging.Logger): The logger instance.
        client_secrets_file (str): The path to the client secrets file.
        token_file (str): The path to the token file.
        credentials: The credentials for the YouTube API.
        youtube (Resource): The YouTube API client.
    """
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

    def __init__(self, logger: logging.Logger):
        """
        Initializes the YouTubeUploader with a logger instance.
        
        Args:
            logger (logging.Logger): The logger instance.
        """
        self.logger = logger
        self.client_secrets_file: str = os.getenv("CLIENT_SECRETS_FILE", 'client_secret.json')
        self.token_file: str = os.getenv("TOKEN_FILE", 'token.pkl')
        self.credentials = self.get_credentials()
        self.youtube: Resource = build('youtube', 'v3', credentials=self.credentials)
        self.logger.info("YouTube client initialized")

    def get_credentials(self):
        """
        Retrieves the credentials for the YouTube API, loading them from a file or creating new ones if not found.
        
        Returns:
            Credentials: The credentials for the YouTube API.
        """
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
        self.channel_id: int = int(os.getenv("DISCORD_CHANNEL_ID", "1242449552850681958"))
        self.bot_token: str = os.getenv("DISCORD_BOT_TOKEN", "")
        self.logger.info("Discord notifier initialized")

    async def send_message(self, message: str) -> None:
        """
        Sends a message to the Discord channel.
        
        Args:
            message (str): The message to send.
        """
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
        """
        Initiates the sending of a message to the Discord channel with the video URL.
        
        Args:
            url (str): The URL of the uploaded video.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        message = f"Votre vidéo est accessible grâce à l'URL suivant : \n{url}"
        loop.run_until_complete(self.send_message(message))


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
        label = Label(root, text="EN ATTENTE", font=("Multicolore", 45), bg='white')  # Set widget background color to white
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
        self.gui_queue.put(("update_status", "EN COURS", "IN PROGRESS", "green"))

    def stop_recording(self) -> None:
        """
        Stops the OBS recording, updates the status, and initiates video upload.
        """
        self.obs_recorder.stop_recording()
        self.gui_queue.put(("update_status", "TERMINÉ", "COMPLETED", "red"))
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
        if event.name == '"':
            self.logger.info("Record key pressed: starting recording")
            self.start_recording()
        elif event.name == 'é':
            self.logger.info("Stop key pressed: stopping recording")
            self.stop_recording()
        # elif event.name == '1':
        #     print("Quit key pressed")
        #     keyboard.unhook_all()
        #     self.obs_recorder.disconnect()
        #     self.gui_queue.put(("quit",))
        #     exit()

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
    app_logger.info(f"Starting Lightboard app...")
    app = RecordingApp(app_logger)
    app.run()
