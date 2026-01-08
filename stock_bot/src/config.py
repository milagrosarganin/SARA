import os
from dotenv import load_dotenv

# Carga las claves del archivo .env (si existe en tu PC)
load_dotenv()

class Settings:
    # 1. Token del Bot (Telegram)
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
    
    # 2. Nombre de tu Google Sheet
    # (Si no encuentra el nombre en el .env, usa "STOCK_MH" por defecto)
    GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "SISTEMA_STOCK_MASTER")
    
    # 3. ID del Grupo de Alertas
    # Intenta convertirlo a número. Si falla, pone 0.
    try:
        ID_GRUPO_ALERTAS = int(os.getenv("ID_GRUPO_ALERTAS", "0"))
    except:
        ID_GRUPO_ALERTAS = 0

    # 4. PINs de Seguridad
    PIN_ENCARGADO = os.getenv("PIN_ENCARGADO", "1234")
    PIN_ADMIN = os.getenv("PIN_ADMIN", "9999")

# Creamos la variable 'settings' que usan los otros archivos
settings = Settings()