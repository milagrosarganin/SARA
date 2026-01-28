import os
from dotenv import load_dotenv

# Carga las claves
load_dotenv()

class Settings:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
    GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "SISTEMA_STOCK_MASTER")
    GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS", "credenciales.json")
    
    try:
        ID_GRUPO_ALERTAS = int(os.getenv("ID_GRUPO_ALERTAS", "0"))
    except:
        ID_GRUPO_ALERTAS = 0

    PIN_ENCARGADO = os.getenv("PIN_ENCARGADO", "1234")
    PIN_ADMIN = os.getenv("PIN_ADMIN", "5678")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    ID_CANAL_FACTURAS = os.getenv("ID_CANAL_FACTURAS")

    DRIVE_FOLDER_ID_FACTURAS = os.getenv("DRIVE_FOLDER_ID_FACTURAS")

    # --- ESTO ERA LO QUE FALTABA ---
    @property
    def is_valid(self):
        return bool(self.TELEGRAM_TOKEN)

settings = Settings()