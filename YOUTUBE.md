Variables d'environnement:
```python
TXT_YT_CLIENT_SECRETS_FILE = os.getenv("CLIENT_SECRETS_FILE", "client_secret.json")
TXT_YT_TOKEN_FILE = os.getenv("TOKEN_FILE", "token.pkl")
TXT_YT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TXT_YT_CLIENT_INIT = "YouTube client initialized"
TXT_YT_CREDENTIALS_LOADED = "Loaded credentials from token file"
TXT_YT_TOKEN_NOT_FOUND = "Token file not found, creating new credentials"
TXT_YT_CREDENTIALS_SAVED = "New credentials saved to token file"
```


Code
```python
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
```