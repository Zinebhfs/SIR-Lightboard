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
import queue
import time
import subprocess
import platform
import pyautogui

# Load environment variables from .env file
load_dotenv()

TXT_LOG_FILE = "lightboard.txt"
TXT_CONSOLE_HANDLER_LEVEL = logging.DEBUG
TXT_FILE_HANDLER_LEVEL = logging.DEBUG
TXT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
TXT_LOGGER_STARTING_APP = "Starting Lightboard app..."
TXT_LOGGER_PAUSE_RECORD = "Recording paused"
TXT_LOGGER_RESUME_RECORD = "Recording resumed"
TXT_OBS_HOST = os.getenv("OBS_HOST", "localhost")
TXT_OBS_PORT = int(os.getenv("OBS_PORT", 4455))
TXT_OBS_VIDEO_PATH = os.getenv("OBS_VIDEO_PATH", r"/home/user/Videos")
TXT_OBS_CONNECTED = "Connected to OBS at {host}:{port}"
TXT_OBS_FAILED_CONNECT = (
    "Failed to connect to OBS at {host}:{port}. Retrying in {delay} seconds..."
)
TXT_OBS_CONNECT_ERROR = (
    "Unable to connect to OBS at {host}:{port} after {retries * delay} seconds."
)
TXT_OBS_START_RECORD = "Started recording"
TXT_OBS_STOP_RECORD = "Stopped recording"
TXT_OBS_DISCONNECTED = "Disconnected from OBS"
TXT_OBS_LATEST_VIDEO = "Latest video found: {video}"
TXT_YT_CLIENT_SECRETS_FILE = os.getenv("CLIENT_SECRETS_FILE", "client_secret.json")
TXT_YT_TOKEN_FILE = os.getenv("TOKEN_FILE", "token.pkl")
TXT_YT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TXT_YT_CLIENT_INIT = "YouTube client initialized"
TXT_YT_CREDENTIALS_LOADED = "Loaded credentials from token file"
TXT_YT_TOKEN_NOT_FOUND = "Token file not found, creating new credentials"
TXT_YT_CREDENTIALS_SAVED = "New credentials saved to token file"
TXT_DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "1242449552850681958"))
TXT_DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
TXT_DISCORD_INIT = "Discord notifier initialized"
TXT_DISCORD_MSG_SENT = "Message sent to Discord channel {channel_id}"
TXT_DISCORD_CHANNEL_ERROR = (
    "The channel ID is incorrect, right-click the channel to get the ID"
)
TXT_DISCORD_MSG_TEMPLATE = "Votre vidéo est accessible grâce à l'URL suivant : \n{url}"
TXT_GUI_WAITING = "EN ATTENTE"
TXT_GUI_IN_PROGRESS = "EN COURS"
TXT_GUI_COMPLETED = "TERMINÉ"
TXT_GUI_FINISH_RECORDING = "ENREGISTREMENT"
TXT_GUI_ERROR = "ERROR"
TXT_GUI_PAUSE = "PAUSE"
TXT_GUI_TIMER = "00:00"
TXT_GUI_GOOGLE_QUOTA_ERROR = "Google quota exceeded"
TXT_GUI_UNEXPECTED_ERROR = "An unexpected error occurred"

nest_asyncio.apply()


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
        # self.recording_state = 0
        self.pause_resume_counter = 0

        self.connect_with_retry()

    def get_video_status(self) -> str:
        response = self.client.call(obs_requests.GetRecordStatus())
        print(response)
        return response

    def connect_with_retry(self, retries: int = 30, delay: int = 1) -> None:
        connected = False
        for _ in range(retries):
            try:
                self.client.connect()
                connected = True
                break
            except Exception as e:
                self.logger.warning(
                    TXT_OBS_FAILED_CONNECT.format(
                        host=self.host, port=self.port, delay=delay
                    )
                )
                time.sleep(delay)

        if not connected:
            raise ConnectionError(
                TXT_OBS_CONNECT_ERROR.format(
                    host=self.host, port=self.port, retries=retries, delay=delay
                )
            )

        self.logger.info(TXT_OBS_CONNECTED.format(host=self.host, port=self.port))

    def start_recording(self) -> None:
        try:
            self.client.call(obs_requests.StartRecord())
            self.logger.info(TXT_OBS_START_RECORD)
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage de l'enregistrement : {e}")

    def stop_recording(self) -> None:
        try:
            self.client.call(obs_requests.StopRecord())
            # self.recording_state = 0
            self.pause_resume_counter = 0
            self.logger.info(TXT_OBS_STOP_RECORD)
        except Exception as e:
            self.logger.error(f"Erreur lors de l'arrêt de l'enregistrement : {e}")

    def pause_recording(self) -> None:
        try:
            self.client.call(obs_requests.PauseRecord())
            self.logger.info(TXT_LOGGER_PAUSE_RECORD)
        except Exception as e:
            self.logger.error(f"Erreur lors de la pause de l'enregistrement : {e}")

    def resume_recording(self) -> None:
        try:
            self.client.call(obs_requests.ResumeRecord())
            self.logger.info(TXT_LOGGER_RESUME_RECORD)
        except Exception as e:
            self.logger.error(f"Erreur lors de la reprise de l'enregistrement : {e}")

    # def toggle_pause_resume_recording(self) -> None:
    #     self.pause_resume_counter += 1
    #     try:
    #         if self.pause_resume_counter % 2 == 1:
    #             response = self.client.call(obs_requests.PauseRecord())
    #             self.logger.info(TXT_LOGGER_PAUSE_RECORD)
    #             self.capture_screenshot()  # Todo: Fix this
    #         else:
    #             response = self.client.call(obs_requests.ResumeRecord())
    #             self.logger.info(TXT_LOGGER_RESUME_RECORD)
    #     except Exception as e:
    #         self.logger.error(
    #             f"Erreur lors de la bascule pause/reprise de l'enregistrement : {e}"
    #         )

    def disconnect(self) -> None:
        self.client.disconnect()
        self.logger.info(TXT_OBS_DISCONNECTED)

    def find_latest_video(self) -> Optional[str]:
        video_files = glob.glob(os.path.join(self.video_path, "*.mkv"))
        if not video_files:
            return None
        latest_video = max(video_files, key=os.path.getmtime)
        self.logger.info(TXT_OBS_LATEST_VIDEO.format(video=latest_video))
        return latest_video

    def find_latest_image(self) -> Optional[str]:
        image_files = glob.glob(os.path.join(self.video_path, "*.png"))
        if not image_files:
            return None
        latest_image = max(image_files, key=os.path.getmtime)
        self.logger.info(f"Latest image found: {latest_image}")
        return latest_image


class YouTubeUploader:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.client_secrets_file: str = TXT_YT_CLIENT_SECRETS_FILE
        self.token_file: str = TXT_YT_TOKEN_FILE
        self.credentials = self.get_credentials()
        self.youtube: Resource = build("youtube", "v3", credentials=self.credentials)
        self.logger.info(TXT_YT_CLIENT_INIT)

    def get_credentials(self):
        try:
            with open(self.token_file, "rb") as token:
                self.logger.info(TXT_YT_CREDENTIALS_LOADED)
                return pickle.load(token)
        except FileNotFoundError:
            self.logger.warning(TXT_YT_TOKEN_NOT_FOUND)
            flow = InstalledAppFlow.from_client_secrets_file(
                self.client_secrets_file, TXT_YT_SCOPES
            )
            credentials = flow.run_local_server(port=0)
            with open(self.token_file, "wb") as token:
                pickle.dump(credentials, token)
            self.logger.info(TXT_YT_CREDENTIALS_SAVED)
            return credentials

    def upload_video(self, video_file: str) -> str:
        body = {
            "snippet": {
                "title": "Video TC INSA Lyon",
                "description": "",
                "tags": ["tag1", "tag2"],
            },
            "status": {"privacyStatus": "unlisted"},
        }
        media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
        response = (
            self.youtube.videos()
            .insert(part="snippet,status", body=body, media_body=media)
            .execute()
        )
        video_id = response["id"]
        self.logger.info(f"Video uploaded to YouTube: {video_id}")
        return f"https://www.youtube.com/watch?v={video_id}"


class DiscordNotifier:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.channel_id: int = int(TXT_DISCORD_CHANNEL_ID)
        self.bot_token: str = TXT_DISCORD_BOT_TOKEN
        self.logger.info(TXT_DISCORD_INIT)

    async def send_message(self, message: str, image: str = "") -> None:
        intents = discord.Intents.default()
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready() -> None:
            channel = client.get_channel(self.channel_id)
            if channel:
                if not image:
                    await channel.send(message)
                    self.logger.info(
                        TXT_DISCORD_MSG_SENT.format(channel_id=self.channel_id)
                    )
                else:
                    await channel.send(message, file=discord.File(image))
                    self.logger.info(
                        TXT_DISCORD_MSG_SENT.format(channel_id=self.channel_id)
                    )
            else:
                self.logger.error(TXT_DISCORD_CHANNEL_ERROR)
            await client.close()

        await client.start(self.bot_token)

    def send_discord_message(self, url: str) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            self.send_message(TXT_DISCORD_MSG_TEMPLATE.format(url=url))
        )

    def send_discord_image(self, path: str, message: str) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.send_message(message, path))


class RecordingApp:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.obs_recorder = OBSRecorder(logger)
        self.youtube_uploader = YouTubeUploader(logger)
        self.discord_notifier = DiscordNotifier(logger)
        self.gui_queue: queue.Queue = queue.Queue()
        self.root, self.label = self.create_status_window()
        self.last_status_message = TXT_GUI_WAITING
        self.last_status_color = "black"
        self.keyboard_hook = keyboard.hook(self.on_key_event)
        self.previous_status_message = self.last_status_message
        self.previous_status_color = self.last_status_color
        self.previous_state = "EN_ATTENTE"
        self.state = "EN_ATTENTE"  # Initialize the state

        self.elapsed_time: int = 0
        self.start_time = None
        self.start_paused_time = None
        self.end_paused_time = None
        self.paused_time: int = 0
        time.sleep(1)
        self.update_gui_message(self.last_status_message, self.last_status_color)
        self.capture_screenshot(message="Etat du tableau au démarrage", show_gui=False)

    def update_state(self, new_state: str):
        self.logger.info(f"{self.state} -> {new_state}")
        self.logger.info(f"{self.previous_state} -> {self.state}")
        self.previous_state = self.state
        self.state = new_state
        self.logger.info(f"State updated to: {self.state}")
        self.logger.info(f"Previous state: {self.previous_state}")

    def create_status_window(self) -> Tuple[Tk, Label]:
        root = Tk()
        root.geometry("400x100")
        root.overrideredirect(True)
        root.configure(background="white")
        root.geometry(
            f"{400}x{100}+{root.winfo_screenwidth() - 400}+{root.winfo_screenheight() - 100}"
        )
        label = Label(root, text=TXT_GUI_WAITING, font=("Multicolore", 45), bg="white")
        label.pack()
        return root, label

    def update_gui_message(self, message: str, color: str) -> None:
        self.previous_status_message = self.last_status_message
        self.previous_status_color = self.last_status_color
        self.last_status_message = message
        self.last_status_color = color
        self.label.config(text=message, fg=color)
        self.root.update()
        self.logger.info(f"Status updated: {message}")

    def restore_previous_status(self) -> None:
        self.update_gui_message(
            self.previous_status_message, self.previous_status_color
        )
        self.update_state(self.previous_state)

    def process_gui_queue(self) -> None:
        while not self.gui_queue.empty():
            task = self.gui_queue.get()
            if task[0] == "update_gui_message":
                self.update_gui_message(task[1], task[2])
            elif task[0] == "upload_video":
                self.upload_video()
            elif task[0] == "launch_timer":
                self.launch_timer()
        self.root.after(100, self.process_gui_queue)

    def upload_video(self) -> None:
        try:
            video_file = self.obs_recorder.find_latest_video()
            if not video_file:
                self.logger.error("No video file found for upload")
                return

            time.sleep(5)  # Wait for the video to be fully written to disk

            video_url = self.youtube_uploader.upload_video(video_file)
            self.logger.info(f"Video URL: {video_url}")
            self.discord_notifier.send_discord_message(video_url)
        except googleapiclient.errors.ResumableUploadError as e:
            self.logger.error("Google API quota exceeded. Unable to upload video.")
            self.update_gui_message("Google quota exceeded", "red")
            time.sleep(5)
            self.obs_recorder.disconnect()
            exit()
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            self.update_gui_message("An unexpected error occurred", "red")
            time.sleep(5)
            self.obs_recorder.disconnect()
            exit()

    def on_key_event(self, event: keyboard.KeyboardEvent):
        if event.event_type == keyboard.KEY_DOWN:
            # Action : ⏯️
            if event.name == '"' or event.name == "3":

                if self.state == "EN_ATTENTE":
                    self.update_state("EN_COURS")
                    self.start_time = time.time()
                    self.gui_queue.put(("launch_timer",))

                    self.obs_recorder.start_recording()
                    self.obs_recorder.get_video_status()

                elif self.state == "EN_COURS":
                    self.update_state("PAUSE")
                    self.start_paused_time = time.time()
                    self.gui_queue.put(("launch_timer",))
                    self.obs_recorder.pause_recording()
                    self.obs_recorder.get_video_status()

                elif self.state == "PAUSE":
                    self.update_state("EN_COURS")
                    self.end_paused_time = time.time()
                    self.paused_time += int(
                        self.end_paused_time - self.start_paused_time
                    )
                    self.start_paused_time = None
                    self.end_paused_time = None
                    self.gui_queue.put(("launch_timer",))
                    self.obs_recorder.resume_recording()
                    self.obs_recorder.get_video_status()

            # Action : 🟥
            elif event.name == "é" or event.name == "2":
                if self.state == "PAUSE" or self.state == "EN_COURS":
                    self.update_state("ENREGISTREMENT")
                    self.obs_recorder.stop_recording()
                    self.gui_queue.put(("upload_video",))
                    self.gui_queue.put(
                        (
                            "update_gui_message",
                            TXT_GUI_FINISH_RECORDING,
                            "red",
                        )
                    )
                    time.sleep(3)
                    self.capture_screenshot(
                        message="Etat du tableau à la fin du recording", show_gui=False
                    )
                    self.elapsed_time: int = 0
                    self.start_time = None
                    self.start_paused_time = None
                    self.end_paused_time = None
                    self.paused_time: int = 0
                    self.update_state("EN_ATTENTE")
                    self.gui_queue.put(("update_gui_message", TXT_GUI_WAITING, "black"))

            # Action : 📷
            elif event.name == "&" or event.name == "1":
                self.update_state("SCREENSHOT")
                self.capture_screenshot(
                    message="Capture d'ecran de la vidéo en cours", show_gui=True
                )
                self.restore_previous_status()
                if self.state in ["EN_COURS", "PAUSE"]:
                    self.gui_queue.put(("launch_timer",))

    def capture_screenshot(self, message: str = "", show_gui: bool = True) -> None:

        if show_gui:
            for count in reversed(range(1, 4)):
                self.label.config(text=f"{count}", fg="red")
                self.root.update()
                time.sleep(1)
            self.gui_queue.put(("update_gui_message", "SCREENSHOT", "green"))

        time.sleep(0.5)
        screenshot_path = os.path.join(
            self.obs_recorder.video_path, f"screenshot_{int(time.time())}.png"
        )

        # Capture screenshot based on the operating system
        if platform.system() == "Linux":
            subprocess.run(["gnome-screenshot", "-f", screenshot_path])
        elif platform.system() == "Windows":
            screenshot = pyautogui.screenshot()
            screenshot.save(screenshot_path)
        else:
            raise NotImplementedError("Unsupported OS")

        # Find the latest image and upload it
        image_file = self.obs_recorder.find_latest_image()
        if not image_file:
            self.logger.error("No image file found for upload")
            return

        self.discord_notifier.send_discord_image(image_file, message)

    def run(self) -> None:
        self.root.after(100, self.process_gui_queue)
        self.root.mainloop()

    def launch_timer(self) -> None:
        while self.state == "EN_COURS":
            self.elapsed_time = int(time.time() - self.start_time) - self.paused_time
            hours, remainder = divmod(self.elapsed_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.update_gui_message(f"{minutes:02d}:{seconds:02d}", "green")
            self.root.update_idletasks()
            time.sleep(1)


if __name__ == "__main__":
    app_logger = Logger(__name__).get_logger()
    app_logger.info(TXT_LOGGER_STARTING_APP)
    app = RecordingApp(app_logger)
    app.run()
