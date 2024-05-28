# Live CD Creation with live-build

This directory provides a simple setup to create a Debian-based live CD using `live-build`.

## Requirements

First, you need to install the `live-build` package. Open a terminal and run:

```bash
sudo apt install live-build
```	

## Setup

To create a live CD, follow these steps:

1. As the root directory of this repo, create and navigate to the working directory:

    ```bash
    cd live-cd
    mkdir live
    cd live
    ```
    
1. Copy the `lbconfig.sh` file to the working directory and execute it:

    ```bash
    cp ../lbconfig.sh .
    ./lbconfig.sh
    ```

1. Build the live CD:

    ```bash
    sudo lb build
    ```
