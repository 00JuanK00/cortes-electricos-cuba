import os
import requests
from telethon.sync import TelegramClient
from datetime import datetime, timedelta
import json
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de Telegram (variables de entorno)
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
channel_username = 'une_cuba'

# Configuración de rutas
JSON_PATH = 'data/cortes.json'
MAX_ENTRIES = 100  # Límite de entradas en el historial

def load_current_data():
    """Carga los datos existentes desde GitHub o archivo local"""
    try:
        url_json = 'https://raw.githubusercontent.com/00JuanK00/cortes-electricos-cuba/main/data/cortes.json'
        response = requests.get(url_json, timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        logger.warning(f"No se pudo cargar JSON remoto: {e}. Usando archivo local.")
        try:
            with open(JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

def process_messages(messages, existing_data):
    """Procesa TODOS los mensajes sin filtrar"""
    existing_ids = {entry['id'] for entry in existing_data}
    new_entries = []
    
    for message in messages:
        if not message.text:
            continue
            
        entry = {
            "id": message.id,
            "fecha": message.date.strftime("%Y-%m-%d %H:%M"),
            "mensaje": message.text,
            "timestamp": int(message.date.timestamp())
        }
        
        if message.id not in existing_ids:
            new_entries.append(entry)
            logger.info(f"Mensaje añadido: {message.date} - {message.text[:50]}...")
    
    return new_entries

def save_data(data):
    """Guarda los datos ordenados y limitados"""
    data_sorted = sorted(data, key=lambda x: x['timestamp'], reverse=True)
    
    if len(data_sorted) > MAX_ENTRIES:
        data_sorted = data_sorted[:MAX_ENTRIES]
    
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data_sorted, f, ensure_ascii=False, indent=2)
    logger.info(f"Datos guardados. Total de entradas: {len(data_sorted)}")

def main():
    try:
        current_data = load_current_data()
        
        with TelegramClient('session_name', api_id, api_hash) as client:
            messages = client.get_messages(
                channel_username,
                limit=20  # Últimos 20 mensajes (sin filtro temporal)
            )
            
            new_entries = process_messages(messages, current_data)
            updated_data = new_entries + current_data
            save_data(updated_data)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

if __name__ == '__main__':
    main()
