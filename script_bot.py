# -*- coding: utf-8 -*-
"""
Created on Tue May 21 13:56:52 2024

@author: CAMBRAY-LAGASSY E
"""
import discord
import asyncio
import nest_asyncio

nest_asyncio.apply()

async def my_coroutine():
    print("Hello, World!")

async def main():
    await my_coroutine()

intents = discord.Intents.default()
client = discord.Client(intents=intents)

#Token du bot discord
BOT_TOKEN = "TOKEN"

#Définir le channel concerné pour l'envoi de l'URL
CHANNEL_ID = 1242449552850681958

#Fonction pour envoyer un message au canal spécifié
async def send_message_to_channel(channel_id, message):
    channel = client.get_channel(channel_id)
    if channel:
        await channel.send(message)
    else:
        print("L'identifiant du channel saisi est incorrect")

#Obtention de l'URL de la dernière vidéo uploadée
URL = "test"
@client.event
async def on_ready():    
    await send_message_to_channel(CHANNEL_ID, "Voici l'URL de la dernière vidéo qui a été uploadée : " + URL)
    
    
async def run_bot():
    bot_task = asyncio.create_task(client.start(BOT_TOKEN))
    await asyncio.sleep(10)
    await client.close()
    
def main():
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()