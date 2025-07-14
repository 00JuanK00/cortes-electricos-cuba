import os
import json
import requests
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
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Nuevo: Token de tu bot
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

def get_telegram_file_url(file_id):
    """Obtiene URL permanente usando la API de bots de Telegram"""
    if not BOT_TOKEN:
        logger.warning("No se configuró BOT_TOKEN para URLs permanentes")
        return None
        
    try:
        # Paso 1: Obtener file_path
        api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
        response = requests.get(api_url, timeout=10).json()
        
        if not response.get('ok'):
            logger.error(f"API Error: {response.get('description')}")
            return None
            
        file_path = response['result']['file_path']
        
        # Paso 2: Construir URL permanente
        return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
    except Exception as e:
        logger.error(f"Error al obtener URL permanente: {str(e)}")
        return None

def get_media_url(msg):
    """Obtiene URL para cualquier tipo de medio adjunto"""
    if not msg.media:
        return None
        
    try:
        # Para fotos normales
        if hasattr(msg.media, 'photo'):
            return get_telegram_file_url(msg.media.photo.id)
            
        # Para documentos/imágenes
        elif hasattr(msg.media, 'document') and 'image' in msg.document.mime_type:
            return get_telegram_file_url(msg.document.id)
            
        # Para stickers (convertidos a imagen)
        elif hasattr(msg.media, 'sticker'):
            return get_telegram_file_url(msg.media.sticker.id)
            
    except Exception as e:
        logger.error(f"Error al procesar medio: {str(e)}")
        
    return None

def scrape_channel(client, channel):
    try:
        messages = client.get_messages(channel['username'], limit=20)
        processed_messages = []
        
        for msg in messages:
            if msg.text or msg.media:
                cuba_time = convert_to_cuba_time(msg.date)
                message_data = {
                    "id": msg.id,
                    "fecha": cuba_time.strftime("%d de %b del %Y a las %I:%M %p"),
                    "hora_utc": msg.date.strftime("%Y-%m-%d %H:%M"),
                    "mensaje": msg.text if msg.text else "[Contenido multimedia]",
                    "timestamp": int(msg.date.timestamp()),
                    "timestamp_local": int(cuba_time.timestamp()),
                    "media_url": get_media_url(msg)  # URL permanente o None
                }
                processed_messages.append(message_data)
        
        return processed_messages
        
    except Exception as e:
        logger.error(f"Error en {channel['name']}: {str(e)}", exc_info=True)
        return []

def save_data(channel_name, data):
    filename = f"{DATA_DIR}/{channel_name}.json"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
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
                    updated_messages = len([m for m in messages if m.get('media_url')])
                    logger.info(f"✅ {len(messages)} mensajes ({updated_messages} con medios) para {channel['name']}")
                    
    except Exception as e:
        logger.error(f"Error fatal: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
