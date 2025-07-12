import os
import json
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from datetime import datetime
import logging
from pytz import timezone

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('TELEGRAM_SESSION')
CONFIG_FILE = 'config/channels.json'
DATA_DIR = 'data/provincias'

# Zona horaria de Cuba (UTC-5)
CUBA_TZ = timezone('America/Havana')

os.makedirs(DATA_DIR, exist_ok=True)

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)['channels']

def convert_to_cuba_time(utc_time):
    """Convierte UTC a hora local de Cuba"""
    return utc_time.astimezone(CUBA_TZ)

def scrape_channel(client, channel):
    try:
        messages = client.get_messages(channel['username'], limit=20)
        processed_messages = []
        
        for msg in messages:
            if msg.text:
                cuba_time = convert_to_cuba_time(msg.date)
                processed_messages.append({
                    "id": msg.id,
                    "fecha": cuba_time.strftime("%Y-%m-%d %H:%M"),
                    "hora_utc": msg.date.strftime("%Y-%m-%d %H:%M"),  # Opcional: guardar UTC también
                    "mensaje": msg.text,
                    "timestamp": int(msg.date.timestamp()),
                    "timestamp_local": int(cuba_time.timestamp())  # Opcional
                })
        
        return processed_messages
        
    except Exception as e:
        logger.error(f"Error en {channel['name']}: {str(e)}", exc_info=True)
        return []

def save_data(channel_name, data):
    filename = f"{DATA_DIR}/{channel_name}.json"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)  # CORRECCIÓN: ensure_ascii solo una vez
    except Exception as e:
        logger.error(f"Error al guardar {filename}: {str(e)}")

def main():
    channels = load_config()
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    try:
        with client:
            for channel in channels:
                logger.info(f"Escaneando {channel['name']}...")
                messages = scrape_channel(client, channel)
                if messages:
                    save_data(channel['name'], messages)
                    logger.info(f"✅ {len(messages)} mensajes guardados para {channel['name']}")
                    
    except Exception as e:
        logger.error(f"Error fatal: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
