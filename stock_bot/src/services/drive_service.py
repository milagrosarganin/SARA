import io
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from src.config import settings

class GoogleDriveService:
    def __init__(self):
        # Si no hay ID de carpeta configurado, avisamos pero no fallamos todavía
        if not settings.DRIVE_FOLDER_ID_FACTURAS:
            print("⚠️ ADVERTENCIA: No tienes configurado DRIVE_FOLDER_ID_FACTURAS en el .env")
            self.service = None
            return

        self.SCOPES = ['https://www.googleapis.com/auth/drive.file']
        self.folder_id = settings.DRIVE_FOLDER_ID_FACTURAS
        
        try:
            # Usamos las mismas credenciales que para Sheets
            self.creds = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_CREDENTIALS, scopes=self.SCOPES)
            self.service = build('drive', 'v3', credentials=self.creds)
        except Exception as e:
            print(f"❌ Error conectando con Drive: {e}")
            self.service = None

    def upload_image_from_bytes(self, image_bytes, filename):
        """Recibe la foto y la sube a Drive. Devuelve el LINK."""
        if not self.service:
            return None

        try:
            # Metadatos (Nombre y Carpeta donde se guarda)
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            
            # Preparamos el archivo
            media = MediaIoBaseUpload(io.BytesIO(image_bytes),
                                      mimetype='image/jpeg',
                                      resumable=True)
            
            # Subimos
            print(f"📤 Subiendo {filename} a Drive...")
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            webview_link = file.get('webViewLink')

            # Hacemos que sea visible para quien tenga el link
            self.make_file_publicly_readable(file_id)

            print(f"✅ Subido exitoso. ID: {file_id}")
            return webview_link

        except Exception as e:
            print(f"❌ Error subiendo a Drive: {e}")
            return None

    def make_file_publicly_readable(self, file_id):
        """Permiso para que se pueda ver la foto con el link"""
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader',
                'allowFileDiscovery': False
            }
            self.service.permissions().create(
                fileId=file_id,
                body=permission,
                fields='id',
            ).execute()
        except Exception as e:
             print(f"⚠️ No pude dar permisos públicos: {e}")