import json
import base64
from groq import Groq
from src.config import settings

class AIService:
    def __init__(self):
        # Usamos la API Key de config
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def match_products_smart(self, user_text, valid_products_list):
        # Convertimos la lista a texto para que la IA la lea
        products_str = "\n".join(valid_products_list)
        
        prompt = f"""
        Sos un asistente de logística experto. Tu misión es interpretar una lista de pedidos sucia y matchearla con el stock oficial.

        CATÁLOGO OFICIAL (Solo podés usar estos nombres exactos):
        {products_str}

        INPUT DEL USUARIO (Lista sucia):
        {user_text}

        INSTRUCCIONES OBLIGATORIAS:
        1. Analiza línea por línea. Extrae CANTIDAD (número) y PRODUCTO.
        2. Limpia palabras basura como "unidades", "botellas", "kg", "bolsa de".
           Ejemplo: "3 unidades Panceta" -> Cantidad: 3, Producto: "Panceta".
        3. Busca el nombre MÁS PARECIDO en el Catálogo Oficial.
        4. Si dice "muzza barra", busca "MOZZARELLA" o similar en la lista.
        
        DEVOLVÉ SOLO JSON (Sin texto extra):
        {{
            "movimientos": [
                {{
                    "input_original": "la linea original del usuario",
                    "cantidad": numero_entero,
                    "producto_oficial": "NOMBRE EXACTO DEL CATALOGO" (o null si no existe)
                }}
            ]
        }}
        """
        
        # Usamos el modelo más potente y nuevo para texto
        return self._call_groq(prompt, model="llama-3.3-70b-versatile")

    def analyze_image_smart(self, image_bytes, valid_products_list):
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        products_str = "\n".join(valid_products_list)

        prompt = f"""
        Actúa como un sistema OCR de facturas. Extrae items (Producto y Cantidad) de la imagen.

        CATÁLOGO OFICIAL:
        {products_str}

        INSTRUCCIONES:
        1. Ignora precios, códigos, fechas y direcciones. Solo importa QUE LLEGÓ y CUANTO.
        2. Matchea con el nombre exacto del catálogo oficial.
        3. Devuelve JSON puro.

        OUTPUT JSON: {{ "movimientos": [ {{ "input_original": "texto leido", "cantidad": numero, "producto_oficial": "NOMBRE EXACTO" }} ] }}
        """

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
                model="llama-3.2-11b-vision-preview",
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
            print(f"❌ Error Visión IA: {e}")
            return None

    def _call_groq(self, prompt, model):
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Sos una API que solo responde JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                model=model,
                temperature=0.1, # Creatividad baja para ser preciso
                response_format={"type": "json_object"},
            )
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
            print(f"❌ Error Texto IA: {e}")
            return None