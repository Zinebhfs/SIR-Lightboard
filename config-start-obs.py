import subprocess
import time
import configparser
import os

def modify_obs_config():
    config_path = os.path.expanduser('~/.config/obs-studio/basic/profiles/Untitled/basic.ini')
    config = configparser.ConfigParser()
    config.read(config_path)

    # Activer la WebSocket et désactiver l'authentif
    if 'WebsocketAPI' not in config:
        config['WebsocketAPI'] = {}
    config['WebsocketAPI']['ServerEnabled'] = 'true'
    config['WebsocketAPI']['ServerAuthRequired'] = 'false'
    
    # Changer le chemin de sauvegarde des vidéos
    if 'AdvOut' not in config:
        config['AdvOut'] = {}
    config['AdvOut']['RecFilePath'] = '/home/user/Videos'

    # Sauvegarder les changements
    with open(config_path, 'w') as configfile:
        config.write(configfile)

modify_obs_config()

def start_obs():
    try:
        # Démarrer OBS Studio
        print("Démarrage d'OBS Studio")
        subprocess.Popen(['obs'])
        
        # Attendre que OBS soit complètement lancé avant de continuer
        print("Attente que OBS se lance...")
        time.sleep(10) 

        print("OBS en cours d'exécution")
    except Exception as e:
        print(f"Erreur lors du démarrage d'OBS: {e}")


start_obs()

# on met ici la suite du script
print("Exécution de la suite du script...")
