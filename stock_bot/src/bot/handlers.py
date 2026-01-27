from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from src.bot.states import BotStates
from src.bot.keyboards import KeyboardBuilder
from src.services.google_sheets import GoogleSheetService
from src.config import settings
from datetime import datetime
from src.services.drive_service import GoogleDriveService

class StockFlowController:
    def __init__(self):
        self.sheet_service = GoogleSheetService()
        self.drive_service = GoogleDriveService()   

    # --- INICIO Y MENÚ PRINCIPAL ---
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # --- LIMPIEZA DE MEMORIA ---
        # Si escribe /start, asumimos que es un usuario nuevo o una sesión nueva
        context.user_data.clear() 
        
        context.user_data['modo'] = 'RETIRO'
        user = update.effective_user.first_name
        
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                f"👋 Hola {user}.\nSeleccioná tu puesto:", 
                reply_markup=KeyboardBuilder.main_sector_menu()
            )
        else:
            await update.message.reply_text(
                f"👋 Hola {user}.\nSeleccioná tu puesto:", 
                reply_markup=KeyboardBuilder.main_sector_menu()
            )
        return BotStates.SELECT_SECTOR

    async def sector_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        sector = query.data
        context.user_data['sector'] = sector
        
        # Opción Deshacer
        if sector == 'UNDO_ACTION':
            user = update.effective_user.first_name
            await query.edit_message_text("⏳ Buscando tus últimos movimientos...")
            
            moves = self.sheet_service.get_last_user_movements(user)
            
            if not moves:
                 await query.edit_message_text("🤷‍♂️ No encontré movimientos recientes tuyos para deshacer.", reply_markup=KeyboardBuilder.main_sector_menu())
                 return BotStates.SELECT_SECTOR
            
            await query.edit_message_text(
                "🗑️ **DESHACER MOVIMIENTO**\nTocá el que quieras borrar:", 
                reply_markup=KeyboardBuilder.undo_list_menu(moves),
                parse_mode='Markdown'
            )
            return BotStates.SELECT_UNDO

        # Opción Jefes
        if sector in ['Encargado', 'Administracion']:
            await query.edit_message_text(f"🔑 {sector}: ¿Qué tarea vas a realizar?", reply_markup=KeyboardBuilder.admin_action_menu())
            return BotStates.SELECT_ACTION
            
        # Opción Ingreso Stock
        if context.user_data.get('modo') == 'INGRESO':
            await query.edit_message_text(f"✅ Sector: {sector}\n🏢 Decime: ¿De qué **PROVEEDOR** es la mercadería?")
            return BotStates.ASK_SUPPLIER 
        
        # --- MODO RÁFAGA (EMPLEADOS) ---
        # Si ya tenemos nombre y local en memoria, saltamos pasos
        if 'nombre_usuario' in context.user_data and 'local' in context.user_data:
            nombre = context.user_data['nombre_usuario']
            local = context.user_data['local']
            
            # Buscamos categorías directamente
            cats = self.sheet_service.get_unique_categories(sector)
            if not cats:
                 await query.edit_message_text("⚠️ No encontré categorías para este sector.", reply_markup=KeyboardBuilder.main_sector_menu())
                 return BotStates.SELECT_SECTOR

            await query.edit_message_text(f"👤 **{nombre}** ({local})\n📂 Entrando a {sector}.\nSeleccioná categoría:", reply_markup=KeyboardBuilder.category_menu(cats))
            return BotStates.SELECT_CATEGORY
            
        # Si NO tenemos datos, flujo normal (pedir nombre)
        await query.edit_message_text(f"✅ Sector: {sector}\n👤 Por favor, escribí tu **NOMBRE**:")
        return BotStates.INPUT_NAME

    async def name_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['nombre_usuario'] = update.message.text
        await update.message.reply_text("🏢 ¿En qué local estás trabajando?", reply_markup=KeyboardBuilder.local_menu())
        return BotStates.SELECT_LOCAL

    async def local_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        context.user_data['local'] = query.data
        
        # Buscamos categorías
        cats = self.sheet_service.get_unique_categories(context.user_data['sector'])
        if not cats:
             await query.edit_message_text("⚠️ No encontré categorías para este sector.", reply_markup=KeyboardBuilder.main_sector_menu())
             return BotStates.SELECT_SECTOR
             
        await query.edit_message_text(f"📍 {query.data}\nSeleccioná una categoría:", reply_markup=KeyboardBuilder.category_menu(cats))
        return BotStates.SELECT_CATEGORY

    async def category_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        try:
            await query.answer() # MATAR EL RELOJITO
            
            # --- PROTECCIÓN: SI SE REINICIÓ EL BOT ---
            if 'sector' not in context.user_data:
                await query.edit_message_text("⚠️ **Sesión expirada.**\nEl bot se actualizó. Por favor tocá /start.")
                return ConversationHandler.END
            # -----------------------------------------

            data = query.data
            if data == "CMD_COMENTARIO":
                await query.edit_message_text("📝 Escribí tu comentario:")
                return BotStates.INPUT_COMMENT
            if data == "BACK_START": return await self.start(update, context)

            cat = data.replace("CAT_", "")
            context.user_data['categoria'] = cat
            
            # Buscamos productos con control de errores
            prods = self.sheet_service.get_products_by_category(context.user_data['sector'], cat)
            
            if not prods:
                await query.edit_message_text(f"⚠️ No hay productos cargados en '{cat}'.", reply_markup=KeyboardBuilder.main_sector_menu())
                return BotStates.SELECT_SECTOR
            
            verbo = "ingresar" if context.user_data.get('modo') == 'INGRESO' else "retirar"
            await query.edit_message_text(f"📂 {cat}\n¿Qué vas a {verbo}?", reply_markup=KeyboardBuilder.product_list_menu(prods))
            return BotStates.SELECT_PRODUCT

        except Exception as e:
            print(f"🔥 Error critico en categoria: {e}")
            try:
                await query.edit_message_text(f"❌ Error inesperado: {str(e)}\nTocá /start")
            except: pass
            return ConversationHandler.END

    async def product_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == 'BACK_MAIN': return await self.start(update, context)
            
        context.user_data['producto'] = query.data
        await query.edit_message_text(f"📦 {query.data}\n🔢 Escribí la cantidad:")
        return BotStates.INPUT_QUANTITY

    async def quantity_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.text.isdigit():
            await update.message.reply_text("⛔ Solo números.")
            return BotStates.INPUT_QUANTITY
            
        cantidad = int(update.message.text)
        modo = context.user_data.get('modo')
        
        # --- CASO A: PRODUCCIÓN PROPIA (NUEVO) ---
        if modo == 'PRODUCCION':
            prod = context.user_data['producto']
            user = update.effective_user.first_name
            
            # Guardamos como INGRESO especial
            self.sheet_service.register_movement(user, "Cocina", prod, cantidad, "Producción Propia")
            exito, _, stock, _, _ = self.sheet_service.update_stock(prod, cantidad, mode='INGRESO')
            
            await update.message.reply_text(f"✅ Producción: **{prod}** (+{cantidad})\nStock Nuevo: {stock}", parse_mode='Markdown')
            await update.message.reply_text("¿Cargaste algo más de Producción?", reply_markup=KeyboardBuilder.yes_no_menu())
            return BotStates.CONFIRM_MORE_PRODUCCION

        # --- CASO B: INGRESO DE PROVEEDOR ---
        if modo == 'INGRESO':
            context.user_data['temp_cantidad'] = cantidad
            await update.message.reply_text("📅 ¿Fecha de VENCIMIENTO? (o escribí 'NO'):")
            return BotStates.ASK_EXPIRATION
        
        # --- CASO C: RETIRO NORMAL (EMPLEADOS) ---
        else:
            user = context.user_data.get('nombre_usuario', 'Anónimo') 
            prod = context.user_data['producto']
            local = context.user_data.get('local', 'Desconocido')
            sector_elegido = context.user_data['sector']
            
            # MAGIA: Si eligió "TODOS", buscamos el sector real del producto
            real_sector = sector_elegido
            if sector_elegido == 'TODOS':
                real_sector = self.sheet_service.get_product_sector(prod)

            # 1. Historial (Usamos real_sector)
            self.sheet_service.register_movement(user, real_sector, prod, -cantidad, local)
            
            # 2. Stock
            exito, alerta, stock, minimo, _ = self.sheet_service.update_stock(prod, cantidad, mode='RETIRO')
            
            msg = f"✅ Retiro: {prod}\nSector: {real_sector}\nQuedan: {stock}" if exito else "⚠️ Error técnico."

            # Alertas
            if alerta and settings.ID_GRUPO_ALERTAS:
                try:
                    await context.bot.send_message(chat_id=settings.ID_GRUPO_ALERTAS, text=f"🚨 **ALERTA**\n{prod} bajo mínimo ({stock})")
                except: pass

            await update.message.reply_text(msg)

            context.user_data['modo'] = 'RETIRO' 
            await update.message.reply_text("🔄 ¿Querés retirar algo más?", reply_markup=KeyboardBuilder.yes_no_menu())
            return BotStates.PREGUNTA_CONTINUAR
            
            # Bucle rápido
            context.user_data['modo'] = 'RETIRO' 
            await update.message.reply_text("🔄 ¿Querés retirar algo más?", reply_markup=KeyboardBuilder.yes_no_menu())
            return BotStates.PREGUNTA_CONTINUAR

    # --- FLUJO DE INGRESO: VENCIMIENTO Y PRECIO (NUEVO) ---
    async def expiration_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['temp_vencimiento'] = update.message.text
        
        # AHORA PEDIMOS EL PRECIO (Esto faltaba en tu archivo anterior)
        await update.message.reply_text(
            "💰 **PRECIO UNITARIO NUEVO**\n"
            "Escribí el costo por unidad/kilo (Ej: 1500). Si no sabés, poné 0:"
        )
        return BotStates.ASK_UNIT_PRICE

    async def price_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if not text.isdigit():
             await update.message.reply_text("⛔ Solo números. Si no sabés poné 0.")
             return BotStates.ASK_UNIT_PRICE
             
        precio = int(text)
        prod_nombre = context.user_data.get('producto')

        # INTELIGENCIA: Buscamos el sector REAL del producto (porque ahora estamos en modo TODOS)
        sector_real = self.sheet_service.get_product_sector(prod_nombre)
        
        # GUARDAMOS TODO EL INGRESO
        data = {
            'fecha': datetime.now().strftime("%Y-%m-%d"),
            'usuario': update.effective_user.first_name,
            'sector': sector_real, 
            'local': context.user_data.get('local', 'General'),
            'producto': prod_nombre,
            'cantidad': context.user_data.get('temp_cantidad'),
            'vencimiento': context.user_data.get('temp_vencimiento'),
            'proveedor': context.user_data.get('ingreso_proveedor'),
            'monto': context.user_data.get('ingreso_monto'),
            'tipo_fact': context.user_data.get('ingreso_tipo_fact'),
            'precio_unitario': precio 
        }
        
        exito, alerta_precio = self.sheet_service.register_full_entry(data)
        
        if exito:
            msg = f"✅ **Ingreso Guardado**\n(Sector detectado: {sector_real})"
            if alerta_precio: msg += f"\n\n{alerta_precio}" 
            
            await update.message.reply_text(msg)
            await update.message.reply_text("¿Tenés **MÁS PRODUCTOS** de la misma factura?", reply_markup=KeyboardBuilder.yes_no_menu())
            return BotStates.CONFIRM_MORE_PRODUCTS
        else:
            await update.message.reply_text("❌ Error al guardar en Sheets.")
            return BotStates.SELECT_ACTION

    # --- CONFIRMACIÓN Y BUCLES ---
    async def more_products_decision(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == 'NO':
            await query.edit_message_text("👌 Ingreso finalizado.")
            return await self.start(update, context)
            
        # Si sigue, preguntamos si es misma factura
        await query.edit_message_text("¿Son de la **MISMA FACTURA**?", reply_markup=KeyboardBuilder.yes_no_menu())
        return BotStates.CHECK_SAME_INVOICE

    # --- ESTA ES LA FUNCIÓN QUE FALTABA ---
    async def check_same_invoice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == 'SI':
            cats = self.sheet_service.get_unique_categories(context.user_data['sector'])
            await query.edit_message_text("📦 Elegí la Categoría:", reply_markup=KeyboardBuilder.category_menu(cats))
            return BotStates.SELECT_CATEGORY
        else:
            # Limpiamos datos anteriores
            context.user_data.pop('ingreso_proveedor', None)
            context.user_data.pop('ingreso_monto', None)
            context.user_data.pop('ingreso_tipo_fact', None)
            
            await query.edit_message_text("🔄 Nuevo Proveedor. Escribí el nombre:")
            return BotStates.ASK_SUPPLIER

    # --- FLUJO DE PEDIDOS ---
    async def order_name_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['pedido_usuario'] = update.message.text
        await update.message.reply_text(f"Hola {update.message.text}. 📝 ¿Qué producto hace falta pedir?")
        return BotStates.ORDER_PRODUCT

    async def order_product_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['pedido_producto'] = update.message.text
        await update.message.reply_text("🔢 ¿Qué cantidad anoto?")
        return BotStates.ORDER_QUANTITY

    async def order_quantity_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['pedido_cantidad'] = update.message.text
        await update.message.reply_text("🚚 ¿Para qué **Proveedor** es?")
        return BotStates.ORDER_SUPPLIER

    async def order_supplier_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            self.sheet_service.save_order(
                datetime.now().strftime("%Y-%m-%d"), 
                context.user_data['pedido_producto'], 
                context.user_data['pedido_cantidad'], 
                update.message.text, 
                context.user_data.get('pedido_usuario', 'Anónimo')
            )
            await update.message.reply_text("✅ Pedido Guardado.", reply_markup=KeyboardBuilder.admin_action_menu())
            return BotStates.SELECT_ACTION
        except:
            await update.message.reply_text("❌ Error guardando pedido.")
            return BotStates.SELECT_ACTION

    # --- INICIO DEL INGRESO (ADMIN/PIN) ---
    async def supplier_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        search = update.message.text.lower()
        all_p = self.sheet_service.get_suppliers_list()
        found = [p for p in all_p if search in str(p).lower()]
        
        if not found:
            context.user_data['ingreso_proveedor'] = update.message.text
            await update.message.reply_text(f"🆕 Nuevo: {update.message.text}\n💰 Monto Total de Factura:")
            return BotStates.ASK_TOTAL_AMOUNT
            
        kb = [[InlineKeyboardButton(p, callback_data=p[:60])] for p in found]
        await update.message.reply_text("🔎 Encontrados:", reply_markup=InlineKeyboardMarkup(kb))
        return BotStates.SELECT_SUPPLIER

    async def supplier_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        context.user_data['ingreso_proveedor'] = query.data
        await query.edit_message_text(f"✅ {query.data}\n💰 Monto Total de Factura:")
        return BotStates.ASK_TOTAL_AMOUNT
    
    async def amount_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.text.isdigit(): 
            await update.message.reply_text("Solo números.")
            return BotStates.ASK_TOTAL_AMOUNT
        context.user_data['ingreso_monto'] = update.message.text
        await update.message.reply_text("📝 Tipo Comprobante:", reply_markup=KeyboardBuilder.invoice_type_menu())
        return BotStates.ASK_INVOICE_TYPE

    async def invoice_type_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        context.user_data['ingreso_tipo_fact'] = query.data
        context.user_data['modo'] = 'INGRESO'
        cats = self.sheet_service.get_unique_categories(context.user_data['sector'])
        await query.edit_message_text("📦 Categoría:", reply_markup=KeyboardBuilder.category_menu(cats))
        return BotStates.SELECT_CATEGORY
    
    async def invoice_type_fallback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("⚠️ Tocá los botones de arriba.")
        return BotStates.ASK_INVOICE_TYPE

    async def handle_admin_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        action = query.data
        
        # --- 1. PRODUCCIÓN PROPIA (NUEVO) ---
        if action == 'START_PRODUCCION':
            context.user_data['modo'] = 'PRODUCCION'
            context.user_data['sector'] = 'Cocina'
            cats = self.sheet_service.get_unique_categories('Cocina')
            await query.edit_message_text("🍳 **PRODUCCIÓN PROPIA**\nSeleccioná la Categoría:", reply_markup=KeyboardBuilder.category_menu(cats))
            return BotStates.SELECT_CATEGORY

        # --- 2. RETIRO MASIVO (NUEVO) ---
        if action == 'START_MASIVO':
            msg = "⚡ **INGRESAR VARIOS (Retiro Masivo)**\nPegá tu lista de productos abajo.\nEj:\n3 pan hambur\n40 mila carne"
            await query.edit_message_text(msg, parse_mode='Markdown')
            return BotStates.INPUT_BATCH_LIST

        # --- 3. INGRESAR STOCK ---
        if action == 'INGRESAR_STOCK':
            context.user_data['next_action'] = 'INGRESAR'
            await query.edit_message_text("🔐 PIN Encargado:")
            return BotStates.CHECK_PIN
            
        # --- 4. HACER PEDIDO ---
        if action == 'HACER_PEDIDO':
            context.user_data['next_action'] = 'PEDIDO'
            await query.edit_message_text("🔐 PIN Pedidos:")
            return BotStates.CHECK_PIN 
        
        # --- 5. REGISTRAR PAGO ---
        if action == 'REGISTRAR_PAGO':
            provs = self.sheet_service.get_suppliers_list()
            if not provs: 
                await query.edit_message_text("⚠️ No hay proveedores.") 
                return BotStates.SELECT_ACTION
            await query.edit_message_text("💸 ¿A quién pagamos?", reply_markup=KeyboardBuilder.provider_menu(provs))
            return BotStates.SELECT_PROVIDER_PAY

        # --- 6. VISOR Y REPORTES ---
        if action == 'BUSCAR_PRODUCTO':
            await query.edit_message_text("🔍 Escribí el nombre del producto:")
            return BotStates.SEARCH_PRODUCT
            
        if action == 'VER_REPORTES':
            await query.edit_message_text("📅 **REPORTES**\nSeleccioná el período:", reply_markup=KeyboardBuilder.report_range_menu())
            return BotStates.SELECT_REPORT_RANGE

        if action == 'VER_INGRESOS':
            reporte = self.sheet_service.get_recent_incomes()
            await query.edit_message_text(reporte, parse_mode='Markdown', reply_markup=KeyboardBuilder.admin_action_menu())
            return BotStates.SELECT_ACTION

        if action == 'BACK_MAIN': 
            return await self.start(update, context)
            
        return BotStates.SELECT_ACTION
    async def verify_pin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text in [settings.PIN_ENCARGADO, settings.PIN_ADMIN]:
            # Opción Pedido
            if context.user_data.get('next_action') == 'PEDIDO':
                await update.message.reply_text("🔓 Acceso OK. ¿Quién hace el pedido?")
                return BotStates.ORDER_INPUT_NAME 
            
            # Opción Ingreso Stock (MODIFICADO PARA UNIFICAR)
            context.user_data['modo'] = 'INGRESO'
            
            # TRUCO: Seteamos 'TODOS' automáticamente para que traiga todas las categorías juntas
            context.user_data['sector'] = 'TODOS' 
            
            # Saltamos directo a pedir Proveedor (sin preguntar sector)
            await update.message.reply_text("🔓 Acceso OK. (Categorías Unificadas)\n🏢 Decime: ¿De qué **PROVEEDOR** es la mercadería?")
            return BotStates.ASK_SUPPLIER
            
        await update.message.reply_text("⛔ PIN Incorrecto.")
        return BotStates.CHECK_PIN

    # --- PAGOS ---
    async def provider_selected_for_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == "BACK_MAIN": return await self.start(update, context)
        
        prov = query.data.replace("PROV_", "")
        context.user_data['pago_proveedor'] = prov
        det = self.sheet_service.get_provider_details(prov)
        saldo = det['SALDO']
        estado = f"🔴 DEUDA: ${saldo:,.0f}" if saldo > 0 else (f"🟢 A FAVOR: ${abs(saldo):,.0f}" if saldo < 0 else "✅ AL DÍA")

        await query.edit_message_text(f"🏦 **{prov}**\n{estado}\nCBU: `{det['CBU_ALIAS']}`\n\n💰 ¿Cuánto pagaste?", parse_mode='Markdown')
        return BotStates.INPUT_PAYMENT_AMOUNT

    async def payment_amount_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.text.isdigit(): return BotStates.INPUT_PAYMENT_AMOUNT
        self.sheet_service.save_expense(datetime.now().strftime("%Y-%m-%d"), context.user_data['pago_proveedor'], int(update.message.text), "PAGADO", update.effective_user.first_name)
        await update.message.reply_text("✅ Pago Registrado.", reply_markup=KeyboardBuilder.admin_action_menu())
        return BotStates.SELECT_ACTION
    
    # --- COMENTARIOS ---
    async def comment_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.sheet_service.save_comment(datetime.now().strftime("%Y-%m-%d"), context.user_data.get('nombre_usuario'), context.user_data.get('local'), update.message.text)
        await update.message.reply_text("✅ Comentario enviado.", reply_markup=KeyboardBuilder.main_sector_menu())
        return BotStates.SELECT_SECTOR

    async def decision_continuar_retiro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == 'SI':
            # INTELIGENCIA: Si ya estaba en un sector, ¿para qué preguntarlo de nuevo?
            # Podemos enviarlo directo a elegir Categoría del mismo sector.
            
            sector = context.user_data.get('sector')
            cats = self.sheet_service.get_unique_categories(sector)
            
            await query.edit_message_text(
                f"🚀 **Modo Rápido**: Seguimos en **{sector}**.\nElegí Categoría:", 
                reply_markup=KeyboardBuilder.category_menu(cats)
            )
            # Saltamos directo al paso 3 (Categoría) en vez del 1 (Sector)
            return BotStates.SELECT_CATEGORY 
            
        else:
            context.user_data.clear()
            await query.edit_message_text("👋 Sesión finalizada.")
            return ConversationHandler.END

    async def search_product_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query_text = update.message.text
        found, msg = self.sheet_service.get_product_details(query_text)
        
        # Le mostramos la info y le dejamos el menú de admin para seguir
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=KeyboardBuilder.admin_action_menu())
        return BotStates.SELECT_ACTION

    async def report_range_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data == "BACK_ADMIN": # Volver al menú principal de admin
            await query.edit_message_text("🔑 Admin: ¿Qué tarea vas a realizar?", reply_markup=KeyboardBuilder.admin_action_menu())
            return BotStates.SELECT_ACTION
            
        # Guardamos si eligió DIARIO o SEMANAL
        rango = "DIARIO" if data == "RANGO_DIARIO" else "SEMANAL"
        context.user_data['report_range'] = rango
        
        await query.edit_message_text(
            f"📅 Período: **{rango}**\nAhora, ¿qué querés ver?", 
            reply_markup=KeyboardBuilder.report_type_menu(), # <--- Menú nuevo 2
            parse_mode="Markdown"
        )
        return BotStates.SELECT_REPORT_TYPE

    async def report_type_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data == "BACK_RANGE": # Volver a elegir fecha
            await query.edit_message_text("📅 Seleccioná el período:", reply_markup=KeyboardBuilder.report_range_menu())
            return BotStates.SELECT_REPORT_RANGE

        rango = context.user_data.get('report_range', 'DIARIO')
        tipo = data.replace("TYPE_", "") # Queda "FALTANTES", "INGRESOS", etc.
        
        await query.edit_message_text(f"⏳ Generando reporte **{tipo}** ({rango})...")
        
        # Llamamos al servicio con los dos datos
        reporte = self.sheet_service.get_filtered_report(tipo, rango)
        
        # Mostramos resultado y volvemos a dejar el menú de tipos por si quiere ver otro
        await query.edit_message_text(
            reporte, 
            parse_mode="Markdown", 
            reply_markup=KeyboardBuilder.report_type_menu() # <--- Se queda aquí para ver otro reporte rápido
        )
        return BotStates.SELECT_REPORT_TYPE

    async def confirm_more_production(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == 'SI':
            # Vuelve a pedir Categoría (Loop)
            cats = self.sheet_service.get_unique_categories('Cocina')
            await query.edit_message_text("🍳 Sigamos. ¿Qué Categoría?", reply_markup=KeyboardBuilder.category_menu(cats))
            return BotStates.SELECT_CATEGORY
        else:
            context.user_data.clear()
            await query.edit_message_text("👋 Ingreso de Elaboración Propia TERMINADO.")
            return ConversationHandler.END

    # --- 4. PROCESAR LISTA MASIVA ---
    async def process_batch_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user.first_name
        
        # CASO A: ES UNA FOTO 📸
        if update.message.photo:
            await update.message.reply_text("👀 Analizando imagen... Dame unos segundos.")
            # Bajamos la foto en memoria (la última es la de mejor calidad)
            photo_file = await update.message.photo[-1].get_file()
            byte_array = await photo_file.download_as_bytearray()
            
            # Mandamos a procesar
            reporte = self.sheet_service.process_photo_entry(byte_array, user)

        # CASO B: ES TEXTO PEGADO 📝
        elif update.message.text:
            await update.message.reply_text("📥 Leyendo texto...")
            reporte = self.sheet_service.process_batch_entry(update.message.text, user)
            
        else:
            await update.message.reply_text("⛔ Formato no válido. Mandá foto o texto.")
            return BotStates.INPUT_BATCH_ENTRY

        if len(reporte) > 4000: reporte = reporte[:4000]
        await update.message.reply_text(reporte, reply_markup=KeyboardBuilder.admin_action_menu())
        return BotStates.SELECT_ACTION

    # --- PARA RETIRO MASIVO (LISTA DE TEXTO) ---
    async def process_batch_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        user = update.effective_user.first_name
        
        await update.message.reply_text("⚡ Procesando retiro masivo... dame unos segundos.")
        
        # Llamamos al servicio de Google Sheets para procesar la lista como RETIRO
        reporte = self.sheet_service.process_batch_list(text, user)
        
        if len(reporte) > 4000: reporte = reporte[:4000]
        
        # Al terminar, volvemos al menú principal
        await update.message.reply_text(reporte, reply_markup=KeyboardBuilder.main_sector_menu())
        return BotStates.SELECT_SECTOR

    # --- FUNCIÓN QUE TE FALTA (Agregala al final de la clase) ---
    async def undo_item_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        # Si se arrepiente y quiere volver
        if data == "BACK_MAIN":
            return await self.start(update, context)
            
        # Si eligió borrar una fila específica (Ej: UNDO_ROW_125)
        if "UNDO_ROW_" in data:
            row_id = data.replace("UNDO_ROW_", "")
            
            await query.edit_message_text("⏳ Borrando y recalculando stock...")
            
            # Llamamos al servicio para borrar esa fila exacta
            exito, msg = self.sheet_service.undo_specific_row(row_id)
            
            await query.edit_message_text(
                f"{'✅' if exito else '⛔'} {msg}", 
                reply_markup=KeyboardBuilder.main_sector_menu()
            )
            return BotStates.SELECT_SECTOR
        
        return BotStates.SELECT_UNDO

    # --- HANDLER DEL BOTÓN ---
    async def btn_cargar_factura_pressed(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("📸 **CARGAR FACTURA**\nPor favor, enviame ahora la FOTO de la factura.")
        return BotStates.WAITING_FOR_FACTURA_PHOTO

    # --- HANDLER QUE RECIBE LA FOTO ---
    async def foto_factura_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text("⏳ Subiendo a Drive...")

        try:
            # 1. Bajar foto de Telegram
            photo_file = await update.message.photo[-1].get_file()
            image_bytes = await photo_file.download_as_bytearray()

            # 2. Nombre del archivo
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"factura_{user.first_name}_{timestamp}.jpg"

            # 3. Subir a Drive
            drive_link = self.drive_service.upload_image_from_bytes(image_bytes, filename)

            if drive_link:
                await update.message.reply_text(f"✅ **Guardada en Drive**\n📂 Link: {drive_link}", reply_markup=KeyboardBuilder.admin_action_menu())
            else:
                 await update.message.reply_text("❌ Error subiendo a Drive. Verificá el ID de la carpeta en .env")

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

        return BotStates.SELECT_ACTION

    