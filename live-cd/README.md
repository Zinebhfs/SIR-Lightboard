# Live CD Creation with live-build

This directory provides a simple setup to create a Debian-based live CD using `live-build`.

## Requirements

First, you need to install the `live-build` package. Open a terminal and run:

```bash
sudo apt install live-build
```	

## Setup

To create a live CD, follow these steps:

1. Make sure you have the `.env` `client_secret.json` `token.pkl` files in the root directory (SIR-Lightboard).
    
1. Execute the `lbconfig.sh` file:

    ```bash
    sh ./lbconfig.sh
    ```

1. Build the live CD:

    ```bash
    cd live/
    sudo lb build
    ```
