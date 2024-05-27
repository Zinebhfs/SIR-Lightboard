# -*- coding: utf-8 -*-

import discord
import os
import asyncio
from dotenv import load_dotenv
import nest_asyncio

nest_asyncio.apply()

# Charger les variables d'environnement depuis un fichier .env
load_dotenv()

# Token du bot discord (à mettre dans un fichier .env)
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

def sendURL(URL):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    # Fonction pour envoyer un message au canal spécifié
    async def send_message_to_channel(channel_id, message):
        channel = client.get_channel(channel_id)
        if channel:
            await channel.send(message)
        else:
            print("L'identifiant du canal est incorrect, faites un clique droit sur le canal concerné pour récupérer l'identifiant")

    # Envoi de l'URL lors du lancement du serveur
    @client.event
    async def on_ready():
        messages = f"Voici l'URL de la dernière vidéo qui a été publiée : \n{URL}"
        await send_message_to_channel(CHANNEL_ID, messages)
        await client.close()

    # Démarrage du bot
    client.run(BOT_TOKEN)


# Envoi des URLs
sendURL("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
sendURL("https://www.youtube.com/")
sendURL("https://google.com")

