import json
from groq import Groq
from src.config import settings

class AIService:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def match_products_smart(self, user_text, valid_products_list):
        """
        Usa Inteligencia Artificial para entender la lista del usuario
        y mapearla a los productos exactos del Excel.
        """
        # Convertimos la lista de productos validos a un string para que la IA la lea
        products_str = "\n".join(valid_products_list)
        
        prompt = f"""
        Sos un asistente experto en stock de un restaurante.
        Tu trabajo es interpretar una lista de items escrita por un humano (con abreviaturas o errores) y conectarla con la lista OFICIAL de productos.

        LISTA OFICIAL DE PRODUCTOS VÁLIDOS:
        {products_str}

        LISTA DEL USUARIO (Input):
        {user_text}

        INSTRUCCIONES:
        1. Para cada linea del usuario, extraé la CANTIDAD (numero) y el NOMBRE.
        2. Busca en la LISTA OFICIAL el producto que mejor coincida SEMÁNTICAMENTE. 
           Ejemplo: "Mila pollo" -> "MILANESA DE POLLO (PAQUETE X 10)".
           Ejemplo: "Tubo calamar" -> "TUBO DE CALAMAR (KG)".
           Ejemplo: "Pan rayado" NO ES "Almendrado".
        3. Si no encontras coincidencia segura, poné "null" en producto_oficial.
        4. Si el usuario pone "Ingresa" o "Egresa", detectalo como tipo de movimiento.

        OUTPUT JSON OBLIGATORIO:
        Devolve SOLO un objeto JSON con este formato exacto, sin texto extra:
        {{
            "movimientos": [
                {{
                    "input_original": "texto del usuario",
                    "cantidad": numero,
                    "producto_oficial": "NOMBRE EXACTO DE LA LISTA OFICIAL" o null
                }}
            ]
        }}
        """

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "Sos un parser JSON estricto. Solo devolvés JSON válido."
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama3-70b-8192", # Modelo muy inteligente y rápido
                temperature=0.1, # Creatividad baja para ser precisos
                response_format={"type": "json_object"},
            )

            # Convertimos la respuesta de texto a un objeto Python real
            response_content = chat_completion.choices[0].message.content
            return json.loads(response_content)

        except Exception as e:
            print(f"Error en IA: {e}")
            return None