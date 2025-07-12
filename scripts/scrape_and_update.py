import os
import requests
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import json
import logging
from datetime import datetime, timedelta

# Configuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Credenciales
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('TELEGRAM_SESSION')
CHANNEL = 'une_cuba'

def load_client():
    """Inicia el cliente de Telegram con sesión persistente"""
    return TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def fetch_messages(client):
    """Obtiene los últimos mensajes del canal"""
    try:
        messages = client.get_messages(CHANNEL, limit=20)
        return [
            {
                "id": msg.id,
                "date": msg.date.strftime("%Y-%m-%d %H:%M"),
                "text": msg.text,
                "timestamp": int(msg.date.timestamp())
            }
            for msg in messages if msg.text
        ]
    except Exception as e:
        logger.error(f"Error al obtener mensajes: {e}")
        return []

def save_data(data):
    """Guarda los datos en formato JSON"""
    try:
        with open('data/cortes.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Datos guardados ({len(data)} registros)")
    except Exception as e:
        logger.error(f"Error al guardar datos: {e}")

def main():
    client = load_client()
    with client:
        messages = fetch_messages(client)
        if messages:
            save_data(messages)

if __name__ == '__main__':
    main()
