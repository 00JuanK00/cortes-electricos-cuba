import os
import json
import requests
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from datetime import datetime
import logging
from pytz import timezone
from collections import Counter  # Importación movida aquí

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('TELEGRAM_SESSION')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CONFIG_FILE = 'config/channels.json'
DATA_DIR = 'data/provincias'
CUBA_TZ = timezone('America/Havana')

os.makedirs(DATA_DIR, exist_ok=True)

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)['channels']

def convert_to_cuba_time(utc_time):
    """Convierte UTC a hora local de Cuba"""
    return utc_time.astimezone(CUBA_TZ)

def get_bot_file_url(file_id):
    """Intenta obtener URL permanente mediante la API de bots"""
    try:
        if not BOT_TOKEN:
            return None
            
        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}",
            timeout=10
        ).json()
        
        if response.get('ok'):
            file_path = response['result']['file_path']
            return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        else:
            logger.warning(f"Bot API error: {response.get('description')}")
            return None
            
    except Exception as e:
        logger.error(f"Error en Bot API: {str(e)}")
        return None

def get_public_media_url(msg, channel_username):
    """Genera URLs compatibles con Glide"""
    try:
        if hasattr(msg.media, 'photo'):
            # Para fotos en canales públicos
            return f"https://cdn4.telegram-cdn.org/file/{msg.media.photo.id}.jpg"
            
        elif hasattr(msg.media, 'document') and 'image' in msg.document.mime_type:
            # Para documentos/imágenes
            return f"https://cdn4.telegram-cdn.org/file/{msg.document.id}.jpg"
            
    except Exception as e:
        logger.error(f"Error generando URL: {str(e)}")
    return None

def get_media_url(msg, channel_username):
    """Obtiene URL de medios con múltiples métodos de respaldo"""
    if not msg.media:
        return None
        
    try:
        file_id = None
        
        if hasattr(msg.media, 'photo'):
            file_id = msg.media.photo.id
        elif hasattr(msg.media, 'document') and 'image' in msg.document.mime_type:
            file_id = msg.document.id
        elif hasattr(msg.media, 'sticker'):
            file_id = msg.media.sticker.id
            
        if file_id:
            bot_url = get_bot_file_url(file_id)
            if bot_url:
                return bot_url
                
        public_url = get_public_media_url(msg, channel_username)
        if public_url:
            logger.info(f"Usando enlace público para {channel_username}/{msg.id}")
            return public_url
            
    except Exception as e:
        logger.error(f"Error procesando medios: {str(e)}", exc_info=True)
        
    return None

def get_media_type(msg):
    """Identifica el tipo de medio adjunto"""
    if not msg.media:
        return None
        
    if hasattr(msg.media, 'photo'):
        return "foto"
    elif hasattr(msg.media, 'document'):
        return "documento"
    elif hasattr(msg.media, 'sticker'):
        return "sticker"
    return "otro"

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
                    "mensaje": msg.text if msg.text else "[Contenido multimedia]",
                    "timestamp": int(msg.date.timestamp()),
                    "media_url": get_media_url(msg, channel['username']),
                    "tipo_medio": get_media_type(msg)
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
                logger.info(f"Escaneando {channel['name']} ({channel['username']})...")
                messages = scrape_channel(client, channel)
                if messages:
                    save_data(channel['name'], messages)
                    media_count = sum(1 for m in messages if m.get('media_url'))
                    # LÍNEA CORREGIDA:
                    tipos_medio = Counter(m['tipo_medio'] for m in messages if m.get('tipo_medio'))
                    logger.info(f"✅ {len(messages)} mensajes | {media_count} con medios | Tipos: {tipos_medio}")
                    
    except Exception as e:
        logger.error(f"Error fatal: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main()
