Variables
```python
TXT_FTP_SERVER_PATH = os.getenv("FTP_SERVER_PATH")
TXT_FTP_SERVER_USER = os.getenv("FTP_SERVER_USER")
TXT_FTP_SERVER_PASS_PHRASE = os.getenv("FTP_SERVER_PASS_PHRASE")
```


Code
```python
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
```