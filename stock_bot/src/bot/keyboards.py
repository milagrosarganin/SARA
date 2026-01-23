from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class KeyboardBuilder:
    
    @staticmethod
    def main_sector_menu():
        keyboard = [
            [InlineKeyboardButton("🌎 Catálogo Completo (General)", callback_data="TODOS")],
            [InlineKeyboardButton("🤵 Mozo", callback_data='Mozo'),
             InlineKeyboardButton("🍺 Barra", callback_data='Barra')],
            [InlineKeyboardButton("🍳 Cocina", callback_data='Cocina'),
             InlineKeyboardButton("🍰 Pastelería", callback_data='Pasteleria')],
            [InlineKeyboardButton("🏭 Producción", callback_data='Producción')],
            [InlineKeyboardButton("🔑 Encargado", callback_data='Encargado'),
             InlineKeyboardButton("🏢 Admin", callback_data='Administracion')],
            [InlineKeyboardButton("↩️ Deshacer mi último movimiento", callback_data='UNDO_ACTION')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def admin_action_menu():
        keyboard = [
            # Botón 1: Producción (Paso a paso)
            [InlineKeyboardButton("🍳 Ingresar Producción Propia", callback_data="START_PRODUCCION")],
            # Botón 2: Retiro Masivo (Lista)
            [InlineKeyboardButton("⚡ Ingresar Varios (Lista)", callback_data="START_MASIVO")],
            
            [InlineKeyboardButton("📥 Ingresar Stock (Proveedor)", callback_data="INGRESAR_STOCK")],
            [InlineKeyboardButton("🔍 Buscar Producto (Visor)", callback_data="BUSCAR_PRODUCTO")],
            [InlineKeyboardButton("📊 Reportes", callback_data="VER_REPORTES")],
            [InlineKeyboardButton("🔙 Volver", callback_data="BACK_MAIN")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def yes_no_menu():
        keyboard = [
            [InlineKeyboardButton("✅ SI", callback_data='SI'),
             InlineKeyboardButton("⛔ NO", callback_data='NO')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def invoice_type_menu():
        keyboard = [
            [InlineKeyboardButton("Factura A", callback_data='Factura A'),
             InlineKeyboardButton("Factura B", callback_data='Factura B')],
            [InlineKeyboardButton("Factura C", callback_data='Factura C'),
             InlineKeyboardButton("Remito / X", callback_data='Remito X')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def local_menu():
        keyboard = [
            [InlineKeyboardButton("General", callback_data='General')],
            [InlineKeyboardButton("Via Appia", callback_data='Via Appia')],
            [InlineKeyboardButton("Revoque", callback_data='Revoque')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def category_menu(categories):
        keyboard = []
        for cat in categories:
            keyboard.append([InlineKeyboardButton(f"📂 {cat}", callback_data=f"CAT_{cat}")])
        keyboard.append([InlineKeyboardButton("📝 Dejar Comentario", callback_data='CMD_COMENTARIO')])
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data='BACK_START')])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def product_list_menu(products):
        keyboard = []
        for p in products:
            nombre = p.get('PRODUCTO', 'Sin Nombre')
            keyboard.append([InlineKeyboardButton(nombre, callback_data=nombre[:60])])
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data='BACK_MAIN')])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def provider_menu(providers):
        keyboard = []
        for p in providers:
            keyboard.append([InlineKeyboardButton(p, callback_data=f"PROV_{p[:50]}")])
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data='BACK_MAIN')])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def report_range_menu():
        keyboard = [
            [InlineKeyboardButton("📅 Hoy", callback_data="RANGO_DIARIO")],
            [InlineKeyboardButton("🗓️ Esta Semana (7 días)", callback_data="RANGO_SEMANAL")],
            [InlineKeyboardButton("🔙 Volver", callback_data="BACK_ADMIN")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def report_type_menu():
        keyboard = [
            [InlineKeyboardButton("📉 Faltantes (Stock Bajo)", callback_data="TYPE_FALTANTES")],
            [InlineKeyboardButton("🚚 Ingresos", callback_data="TYPE_INGRESOS")],
            [InlineKeyboardButton("🔄 Movimientos (Historial)", callback_data="TYPE_MOVIMIENTOS")],
            [InlineKeyboardButton("🔙 Volver", callback_data="BACK_RANGE")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def undo_list_menu(movements):
        keyboard = []
        
        if not movements:
            keyboard.append([InlineKeyboardButton("🤷‍♂️ No tenés movimientos recientes", callback_data="BACK_MAIN")])
        else:
            for mov in movements:
                # El botón dirá: "10:30 | Coca Cola (-2)"
                # El dato oculto (callback) será: "UNDO_ROW_154" (el número de fila)
                texto = f"{mov['fecha']} | {mov['producto']} ({mov['cantidad']})"
                callback = f"UNDO_ROW_{mov['row_id']}"
                keyboard.append([InlineKeyboardButton(texto, callback_data=callback)])
        
        keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="BACK_MAIN")])
        return InlineKeyboardMarkup(keyboard)