
# Build ISO

In this section, we will see how to build a custom live CD that can be used to run the OBS recording script on any machine without installing any dependencies. It automatically starts the OBS and run the script that handler all the feature when the system boots up.

## File needed
To build the ISO, you need to have the following files in the root directory of the project:

Place the `client_secret.json` and `token.pkl` files in the root directory of the project.

For the `.env` file, you can create it with the following content:
You only need to change `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID` with your own values.

```bash
OBS_HOST="localhost"
OBS_PORT=4455
OBS_VIDEO_PATH="/home/user"

CLIENT_SECRETS_FILE="../client_secret.json"
TOKEN_FILE="../token.pkl"

DISCORD_BOT_TOKEN="your_discord_bot_token_here"
DISCORD_CHANNEL_ID="your_discord_channel_id_here"
```


```bash
├── client_secret.json              # here
├── .env                                   # here
├── .gitignore
├── live-cd
│   ├── isolinux.cfg
│   ├── lbconfig.sh
│   ├── README.md
│   └── start.xsession
├── main.py
├── monscript.sh
├── obs
│   ├── obs-global-config.ini
│   ├── obs-profile-config.ini
│   └── obs-scene-config.json
├── README.md
├── requirements.txt
└── token.pkl                            # and here

```

## Prepare the live directory
Then run the following commands to prepare the live directory :
```bash
mkdir live-cd/live
cp live-cd/live
cp ../lbconfig.sh .
chmod +x lbconfig.sh
./lbconfig.sh
```

After that, you can build the ISO using the following command:
```bash
sudo lb build
```

After quite some time, you will have the ISO file in the `live-cd` directory.

## conclusion
Great, now you have a custom live CD that can be used to run the OBS recording script on any machine without installing any dependencies. It automatically starts the OBS and run the script that handler all the feature when the system boots up.
