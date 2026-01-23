import json
import base64
from groq import Groq
from src.config import settings

class AIService:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    # --- 1. PARA TEXTO (Listas pegadas de WhatsApp) ---
    def match_products_smart(self, user_text, valid_products_list):
        products_str = "\n".join(valid_products_list)
        prompt = f"""
        Sos un experto en stock. Interpretá esta lista cruda y matcheala con la oficial.
        LISTA OFICIAL: {products_str}
        INPUT USUARIO: {user_text}
        
        INSTRUCCIONES:
        1. Ignora precios y códigos. Solo Cantidad y Producto.
        2. Matchea semánticamente (Ej: "Mila" -> "MILANESA").
        
        OUTPUT JSON: {{ "movimientos": [ {{ "input_original": "texto", "cantidad": numero, "producto_oficial": "NOMBRE EXACTO" }} ] }}
        """
        return self._call_groq(prompt, model="llama3-70b-8192")

    # --- 2. PARA FOTOS (Facturas) ---
    def analyze_image_smart(self, image_bytes, valid_products_list):
        # Convertimos la imagen a texto codificado (Base64)
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        products_str = "\n".join(valid_products_list)

        prompt = f"""
        Sos un experto logístico leyendo una FACTURA.
        Tu misión: Extraer items (Producto y Cantidad) y matchearlos con la BASE DE DATOS.

        BASE DE DATOS OFICIAL:
        {products_str}

        INSTRUCCIONES:
        1. Ignora precios ($), códigos de barra, fechas y direcciones.
        2. Concentrate en las columnas de DESCRIPCIÓN y CANTIDAD.
        3. Si ves "30 PEPSI", busca en la base "PEPSI 500".
        4. Si la imagen no se lee, devolvé lista vacía.

        OUTPUT JSON: {{ "movimientos": [ {{ "input_original": "texto leido", "cantidad": numero, "producto_oficial": "NOMBRE EXACTO" }} ] }}
        """
        
        # Llamada especial con imagen
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                        ],
                    }
                ],
                model="llama-3.2-11b-vision-preview", # Modelo con Ojos 👀
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
            print(f"Error Vision: {e}")
            return None

    # Helper privado para texto
    def _call_groq(self, prompt, model):
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "JSON puro."},
                    {"role": "user", "content": prompt}
                ],
                model=model,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return json.loads(chat_completion.choices[0].message.content)
        except: return None