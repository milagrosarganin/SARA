import gspread
from src.config import settings
from datetime import datetime  # <--- ¡ESTO FALTABA! Sin esto no guarda la fecha.

class GoogleSheetService:
    def __init__(self):
        # --- CHIVATO DE DEBUG ---
        print(f"👀 OJO: Intentando abrir la hoja llamada: '{settings.GOOGLE_SHEET_NAME}'")
        # ------------------------

        self.gc = gspread.service_account(filename='credenciales.json')
        self.sh = self.gc.open(settings.GOOGLE_SHEET_NAME)
        
        # Intentamos buscar la pestaña "STOCK"
        try:
            self.worksheet_stock = self.sh.worksheet("STOCK")
        except:
            # Si no existe una pestaña llamada "STOCK", agarramos la primera que encuentre
            print("⚠️ No encontré pestaña 'STOCK', usando la primera hoja.")
            self.worksheet_stock = self.sh.get_worksheet(0)        
        
        # Cacheamos las hojas
        self.worksheet_historial = self.sh.worksheet("HISTORIAL")
        self.worksheet_pedidos = self.sh.worksheet("PEDIDOS")
        self.worksheet_comentarios = self.sh.worksheet("COMENTARIOS")
        self.worksheet_proveedores = self.sh.worksheet("PROVEEDORES")
        self.worksheet_gastos = self.sh.worksheet("GASTOS")
        self.worksheet_ingresos = self.sh.worksheet("INGRESOS")

    # --- LIMPIEZA DE NÚMEROS INTELIGENTE ---
    def _clean_number(self, value):
        """Convierte texto sucio (10 kg, $30.000, 10,5) en número float seguro"""
        
        # 1. Si Excel ya nos da un número (ej: 38000 sin comillas), lo usamos directo
        if isinstance(value, (int, float)):
            return float(value)
            
        try:
            # 2. Si es texto, limpiamos
            text = str(value).lower()
            text = text.replace('kg','').replace('un','').replace('$','').replace(' ','').strip()
            
            # 3. Lógica Argentina:
            # Quitamos los puntos de mil (38.000 -> 38000)
            text = text.replace('.', '')
            # Cambiamos la coma por punto para decimales (10,5 -> 10.5)
            text = text.replace(',', '.')
            
            if not text: return 0.0
            return float(text)
        except:
            return 0.0

    # --- LECTURA ---
    def get_unique_categories(self, sector):
        try:
            records = self.worksheet_stock.get_all_records()
            cats = set()
            for p in records:
                if sector.upper() in str(p.get('SECTOR', '')).strip().upper():
                    if p.get('CATEGORIA'): cats.add(str(p['CATEGORIA']))
            return list(cats)
        except: return []

    def get_products_by_category(self, sector, category):
        try:
            records = self.worksheet_stock.get_all_records()
            return [p for p in records if sector.upper() in str(p.get('SECTOR','')).upper() and str(p.get('CATEGORIA','')).upper() == category.upper()]
        except: return []

    # --- MOVIMIENTOS ---
    def register_movement(self, user_name, sector, product_name, quantity, local):
        try:
            # AQUI FALLABA ANTES PORQUE FALTABA EL IMPORT DE DATETIME
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            row = [timestamp, user_name, sector, product_name, "INGRESO 🟢" if int(quantity)>0 else "RETIRO 🔴", int(quantity), local]
            self.worksheet_historial.append_row(row)
            return True
        except Exception as e: 
            print(f"❌ Error guardando historial: {e}")
            return False

    def update_stock(self, product_name, quantity, mode='RETIRO', new_price=None):
        print(f"🕵️ DEBUG: Procesando {product_name}...")
        try:
            cell = self.worksheet_stock.find(product_name)
            if not cell: return False, False, 0, 0, None
            
            # Usamos row_values para leer TODA la fila de una (más seguro)
            row_values = self.worksheet_stock.row_values(cell.row)
            
            # Rellenamos la lista por si la fila está corta en el Excel
            while len(row_values) < 10:
                row_values.append("")
            
            # ÍNDICES (Restamos 1 porque Python empieza en 0)
            # Col E (5) -> índice 4 (Stock Min)
            # Col F (6) -> índice 5 (Stock Actual)
            # Col G (7) -> índice 6 (Precio)
            
            curr_val = row_values[5]      # Stock Actual (Col F)
            min_val  = row_values[4]      # Stock Mínimo (Col E)
            old_price_val = row_values[6] # Precio (Col G)
            
            print(f"🕵️ DEBUG LECTURA EXCEL -> Stock: {curr_val} | Precio Viejo: {old_price_val}")

            current_stock = self._clean_number(curr_val)
            stock_minimo  = self._clean_number(min_val)
            old_price     = self._clean_number(old_price_val)
            
            print(f"🕵️ DEBUG LIMPIO -> Precio Viejo detectado: {old_price}")

            # 1. Update Cantidad
            if mode == 'INGRESO':
                new_stock = current_stock + quantity
            else:
                new_stock = current_stock - quantity
            
            # Guardamos Stock (Columna 6 = F)
            self.worksheet_stock.update_cell(cell.row, 6, new_stock)
            
            # 2. Update Precio y Generar Mensaje
            price_msg = None
            if mode == 'INGRESO' and new_price is not None:
                # Si el precio ingresado es mayor a 0, lo guardamos
                if new_price > 0:
                    # Guardamos Precio (Columna 7 = G)
                    self.worksheet_stock.update_cell(cell.row, 7, new_price)
                
                    # Lógica de comparación
                    if old_price == 0:
                        price_msg = f"🆕 **Precio Inicial**: ${new_price:,.0f}"
                    elif new_price > old_price:
                        diff = new_price - old_price
                        porc = (diff / old_price) * 100
                        price_msg = f"📈 **¡AUMENTO!**\nAntes: ${old_price:,.0f} ➡️ Ahora: ${new_price:,.0f}\n(Subió {porc:.1f}%)"
                    elif new_price < old_price:
                        price_msg = f"📉 **BAJÓ DE PRECIO**\nAntes: ${old_price:,.0f} ➡️ Ahora: ${new_price:,.0f}"
                    else:
                        price_msg = f"✅ **Mismo Precio** (${new_price:,.0f})"

            # 3. Alerta Stock
            stock_alert = (mode == 'RETIRO' and new_stock <= stock_minimo)
            
            return True, stock_alert, new_stock, stock_minimo, price_msg

        except Exception as e:
            print(f"🔥 Error Update: {e}")
            return False, False, 0, 0, None

    def register_full_entry(self, data):
        try:
            # 1. Ingresos
            self.worksheet_ingresos.append_row([
                data['fecha'], data['monto'], data['usuario'], data['sector'],
                data['local'], data['proveedor'], data['producto'], 
                data['cantidad'], data['vencimiento'], data['tipo_fact']
            ])
            # 2. Historial
            self.worksheet_historial.append_row([
                data['fecha'], data['usuario'], data['sector'], data['producto'],
                "INGRESO 🟢", int(data['cantidad']), data['local']
            ])
            # 3. Stock + Precio
            precio_unitario = float(data.get('precio_unitario', 0))
            exito, st_alert, st_new, st_min, pr_msg = self.update_stock(
                data['producto'], int(data['cantidad']), mode='INGRESO', new_price=precio_unitario
            )
            return True, pr_msg
        except Exception as e:
            print(f"Error ingreso full: {e}")
            return False, None

    # --- RESTO DE FUNCIONES ---
    def get_suppliers_list(self):
        try: return [r[0] for r in self.worksheet_proveedores.get_all_values()[1:] if r and r[0]]
        except: return []

    def get_provider_details(self, provider_name):
        try:
            cell = self.worksheet_proveedores.find(provider_name)
            if cell:
                row = self.worksheet_proveedores.row_values(cell.row)
                while len(row) < 10: row.append("")
                return {'CBU_ALIAS': row[1] or "No cargado", 'PREFERENCIA': row[2] or "-", 'SALDO': self._clean_number(row[6])}
            return {'CBU_ALIAS': 'No encontrado', 'PREFERENCIA': '-', 'SALDO': 0}
        except: return {'CBU_ALIAS': 'Error', 'PREFERENCIA': '-', 'SALDO': 0}

    def save_expense(self, fecha, proveedor, monto, estado, usuario):
        self.worksheet_gastos.append_row([fecha, proveedor, monto, estado, usuario])
    
    def save_order(self, fecha, prod, cant, prov, user):
        self.worksheet_pedidos.append_row([fecha, prod, cant, prov, "PENDIENTE", user])

    def save_comment(self, fecha, persona, local, comentario):
        self.worksheet_comentarios.append_row([fecha, persona, local, comentario])

    def get_stock_report(self):
        try:
            data = self.worksheet_stock.get_all_records()
            low = []
            for p in data:
                curr = self._clean_number(p.get('STOCK ACTUAL', 0))
                min = self._clean_number(p.get('STOCK MINIMO', 0))
                if curr <= min: low.append(f"⚠️ {p.get('PRODUCTO')}: {curr} (Min: {min})")
            return "📉 **FALTANTES**\n" + "\n".join(low) if low else "✅ Stock OK."
        except: return "Error reporte."

    def get_daily_movements_report(self):
        # Tu reporte diario...
        return "Reporte diario..."

    def undo_last_movement(self, user_name):
        # Tu función undo...
        return False, "Función undo."