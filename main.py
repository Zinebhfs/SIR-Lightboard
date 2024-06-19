import os
import glob
import keyboard
import logging
from typing import Optional, Tuple
import logging
import paramiko
from obswebsocket import obsws, requests as obs_requests
from dotenv import load_dotenv
from tkinter import Tk, Label
import nest_asyncio
import queue
import time
import subprocess
import platform
import pyautogui
import requests

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
TXT_DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
TXT_DISCORD_INIT = "Discord notifier initialized"
TXT_DISCORD_MSG_SENT = "Message sent to Discord channel via webhook"
TXT_DISCORD_MSG_TEMPLATE = "Votre vidéo est accessible sur https://videos.insa-lyon.fr/record/claim_record/"
TXT_GUI_WAITING = "EN ATTENTE"
TXT_GUI_IN_PROGRESS = "EN COURS"
TXT_GUI_COMPLETED = "TERMINÉ"
TXT_GUI_FINISH_RECORDING = "UPLOAD"
TXT_GUI_ERROR = "ERROR"
TXT_GUI_PAUSE = "PAUSE"
TXT_GUI_TIMER = "00:00"
TXT_GUI_UNEXPECTED_ERROR = "An unexpected error occurred"

TXT_FTP_SERVER_PATH = os.getenv("FTP_SERVER_PATH")
TXT_FTP_SERVER_USER = os.getenv("FTP_SERVER_USER")
TXT_FTP_SERVER_PASS_PHRASE = os.getenv("FTP_SERVER_PASS_PHRASE")

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


class FTPUploader:
    def __init__(
        self,
        server: str,
        username: str,
        key_path: str,
        passphrase: str,
        logger: logging.Logger,
    ):
        self.server = server
        self.username = username
        self.key_path = key_path
        self.passphrase = passphrase
        self.logger = logger
        self.sftp = None
        self.connect()

    def connect(self):
        try:
            key = paramiko.RSAKey.from_private_key_file(
                self.key_path, password=self.passphrase
            )
            transport = paramiko.Transport((self.server, 22))
            transport.connect(username=self.username, pkey=key)
            self.sftp = paramiko.SFTPClient.from_transport(transport)
            self.logger.info("Connected to SFTP server")
        except Exception as e:
            self.logger.error(f"Failed to connect to SFTP server: {e}")

    def upload_file(self, local_path: str, remote_path: str):
        if not self.sftp:
            self.logger.error("SFTP connection not established")
            return
        try:
            self.sftp.put(local_path, remote_path)
            self.logger.info(f"Uploaded {local_path} to {remote_path}")
        except Exception as e:
            self.logger.error(f"Failed to upload file: {e}")

    def disconnect(self):
        if self.sftp:
            self.sftp.close()
            self.logger.info("Disconnected from SFTP server")
        else:
            self.logger.warning("SFTP connection was not established")


class DiscordNotifier:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.webhook_url: str = TXT_DISCORD_WEBHOOK_URL
        self.logger.info(TXT_DISCORD_INIT)

    def send_discord_message(self, message) -> None:
        message = {"content": message}
        response = requests.post(self.webhook_url, json=message)
        if response.status_code == 204:
            self.logger.info(TXT_DISCORD_MSG_SENT)
        else:
            self.logger.error(f"Failed to send message: {response.status_code}")

    def send_discord_image(self, path: str, message: str) -> None:
        with open(path, "rb") as file:
            response = requests.post(
                self.webhook_url, files={"file": file}, data={"content": message}
            )
            if response.status_code == 204:
                self.logger.info(TXT_DISCORD_MSG_SENT)
            else:
                self.logger.error(f"Failed to send image: {response.status_code}")


class RecordingApp:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.obs_recorder = OBSRecorder(logger)
        self.ftp_uploader = FTPUploader(
            server=TXT_FTP_SERVER_PATH,
            username=TXT_FTP_SERVER_USER,
            passphrase=TXT_FTP_SERVER_PASS_PHRASE,
            logger=logger,
            key_path="/home/user/.ssh/id_rsa.dat",
        )
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

            file_name = os.path.basename(video_file).replace(" ", "_")
            self.ftp_uploader.upload_file(video_file, f"/TC/{file_name}")
            video_url = f"ftp://{self.ftp_uploader.server}/TC/{file_name}"
            self.logger.info(f"Video URL: {video_url}")
            self.discord_notifier.send_discord_message(TXT_DISCORD_MSG_TEMPLATE)
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

                elif self.state == "ENREGISTREMENT":
                    self.logger.info(
                        "Upload in progress, please wait for the video to be uploaded before taking another action"
                    )
                elif self.state == "SCREENSHOT":
                    self.logger.info(
                        "Screenshot in progress, pls wait before taking another action"
                    )
                else:
                    self.logger.info(f"Unexpected action ⏯️ with state {self.state}")

            # Action : 🟥
            elif event.name == "é" or event.name == "2":
                if self.state == "PAUSE" or self.state == "EN_COURS":
                    self.update_state("ENREGISTREMENT")
                    self.gui_queue.put(
                        (
                            "update_gui_message",
                            TXT_GUI_FINISH_RECORDING,
                            "red",
                        )
                    )
                    self.obs_recorder.stop_recording()
                    self.gui_queue.put(("upload_video",))

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

                elif self.state == "ENREGISTREMENT":
                    self.logger.info(
                        "Recording already stopped, please wait for upload"
                    )

                elif self.state == "SCREENSHOT":
                    self.logger.info(
                        "Screenshot in progress, pls wait before taking another action"
                    )

                else:
                    self.logger.info(f"Unexpected action 🟥 with state {self.state}")

            # Action : 📷
            elif event.name == "&" or event.name == "1":
                if self.state != "SCREENSHOT":
                    self.update_state("SCREENSHOT")
                    self.capture_screenshot(
                        message="Capture d'ecran de la vidéo en cours", show_gui=True
                    )
                    self.restore_previous_status()

                    if self.state == "EN_COURS" or self.state == "PAUSE":
                        self.gui_queue.put(("launch_timer",))

                elif self.state == "SCREENSHOT":
                    self.logger.info(
                        "Screenshot already in progress, pls wait before taking another one"
                    )
                else:
                    self.logger.info(f"Unexpected action 📷 with state {self.state}")

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
