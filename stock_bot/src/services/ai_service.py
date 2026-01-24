import json
import base64
from groq import Groq
from src.config import settings

class AIService:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def match_products_smart(self, user_text, valid_products_list):
        products_str = "\n".join(valid_products_list)
        
        prompt = f"""
        Sos un experto logístico. Tu trabajo es limpiar una lista de pedidos y cruzarla con el stock oficial.

        CATÁLOGO OFICIAL:
        {products_str}

        LISTA SUCIA DEL USUARIO:
        {user_text}

        INSTRUCCIONES:
        1. Lee línea por línea. Extrae CANTIDAD y PRODUCTO.
        2. IGNORA palabras basura como: "unidades", "botellas", "kg", "bolsa de", "pack".
           Ejemplo: "3 unidades Panceta" -> 3 "Panceta".
           Ejemplo: "1 bolsa papa" -> 1 "Papa".
        3. Busca el nombre MÁS PARECIDO en el Catálogo Oficial.
        4. Si no encontrás coincidencia, dejalo como null.

        RESPONDÉ SOLO ESTE JSON:
        {{
            "movimientos": [
                {{
                    "input_original": "texto original",
                    "cantidad": numero_entero,
                    "producto_oficial": "NOMBRE EXACTO CATALOGO" (o null)
                }}
            ]
        }}
        """
        return self._call_groq(prompt, model="llama-3.3-70b-versatile")

    def analyze_image_smart(self, image_bytes, valid_products_list):
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        products_str = "\n".join(valid_products_list)
        prompt = f"""
        Sistema OCR de facturas. Extrae items (Producto y Cantidad).
        CATÁLOGO: {products_str}
        OUTPUT JSON: {{ "movimientos": [ {{ "input_original": "texto", "cantidad": num, "producto_oficial": "NOMBRE" }} ] }}
        """
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                    ]}
                ],
                model="llama-3.2-11b-vision-preview",
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
            print(f"Error Vision: {e}")
            return None

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