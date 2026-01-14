from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from src.bot.states import BotStates
from src.bot.keyboards import KeyboardBuilder
from src.services.google_sheets import GoogleSheetService
from src.config import settings
from datetime import datetime

class StockFlowController:
    def __init__(self):
        self.sheet_service = GoogleSheetService()

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
            await query.edit_message_text("⏳ Deshaciendo último movimiento...", reply_markup=KeyboardBuilder.main_sector_menu())
            exito, msg = self.sheet_service.undo_last_movement(update.effective_user.first_name)
            await query.edit_message_text(f"{'✅' if exito else '⛔'} {msg}", reply_markup=KeyboardBuilder.main_sector_menu())
            return BotStates.SELECT_SECTOR

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
        await query.answer()
        data = query.data
        
        if data == "CMD_COMENTARIO":
            await query.edit_message_text("📝 Escribí tu comentario:")
            return BotStates.INPUT_COMMENT
        if data == "BACK_START": return await self.start(update, context)

        cat = data.replace("CAT_", "")
        context.user_data['categoria'] = cat
        
        # Buscamos productos
        prods = self.sheet_service.get_products_by_category(context.user_data['sector'], cat)
        if not prods:
             await query.edit_message_text("⚠️ No hay productos acá.", reply_markup=KeyboardBuilder.main_sector_menu())
             return BotStates.SELECT_SECTOR
        
        verbo = "ingresar" if context.user_data.get('modo') == 'INGRESO' else "retirar"
        await query.edit_message_text(f"📂 {cat}\n¿Qué vas a {verbo}?", reply_markup=KeyboardBuilder.product_list_menu(prods))
        return BotStates.SELECT_PRODUCT

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
        
        # --- CAMINO A: INGRESO DE MERCADERÍA ---
        if context.user_data.get('modo') == 'INGRESO':
            context.user_data['temp_cantidad'] = cantidad
            await update.message.reply_text("📅 ¿Cuál es la **FECHA DE VENCIMIENTO**? (o escribí 'NO'):")
            return BotStates.ASK_EXPIRATION
        
        # --- CAMINO B: RETIRO DE MERCADERÍA ---
        else:
            user = context.user_data.get('nombre_usuario', 'Anónimo') 
            prod = context.user_data['producto']
            local = context.user_data.get('local', 'Desconocido')
            sector = context.user_data['sector']
            
            # 1. Registrar Historial
            self.sheet_service.register_movement(user, sector, prod, -cantidad, local)
            
            # 2. Actualizar Stock
            exito, alerta, stock, minimo, _ = self.sheet_service.update_stock(prod, cantidad, mode='RETIRO')
            
            msg = f"✅ Retiro Registrado.\nQuedan: {stock}" if exito else "⚠️ Error técnico, pero se guardó en historial."
            
            # 3. Alerta de Stock Bajo
            if alerta:
                # ... (tu código de alerta igual que antes) ...
                if settings.ID_GRUPO_ALERTAS:
                    try:
                        alert_msg = f"🚨 **ALERTA**\n{prod} bajo mínimo ({stock})"
                        await context.bot.send_message(chat_id=settings.ID_GRUPO_ALERTAS, text=alert_msg)
                    except: pass

            await update.message.reply_text(msg)
            
            # --- AQUÍ CAMBIA: PREGUNTA BUCLE ---
            context.user_data['modo'] = 'RETIRO' 
            
            # Usamos el menú SI/NO para preguntar si sigue
            await update.message.reply_text(
                "🔄 **¿Necesitás retirar algo más?**", 
                reply_markup=KeyboardBuilder.yes_no_menu()
            )
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
        
        # GUARDAMOS TODO EL INGRESO
        data = {
            'fecha': datetime.now().strftime("%Y-%m-%d"),
            'usuario': update.effective_user.first_name,
            'sector': context.user_data.get('sector'),
            'local': context.user_data.get('local', 'General'),
            'producto': context.user_data.get('producto'),
            'cantidad': context.user_data.get('temp_cantidad'),
            'vencimiento': context.user_data.get('temp_vencimiento'),
            'proveedor': context.user_data.get('ingreso_proveedor'),
            'monto': context.user_data.get('ingreso_monto'),
            'tipo_fact': context.user_data.get('ingreso_tipo_fact'),
            'precio_unitario': precio # <--- Esto activa la alerta de inflación
        }
        
        exito, alerta_precio = self.sheet_service.register_full_entry(data)
        
        if exito:
            msg = "✅ **Ingreso Guardado**"
            if alerta_precio: msg += f"\n\n{alerta_precio}" # Muestra si subió o bajó el precio
            
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

    # --- ADMIN / PAGOS ---
    async def handle_admin_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        action = query.data
        if action == 'BACK_MAIN': return await self.start(update, context)
        
        if action == 'VER_REPORTES':
            rep = self.sheet_service.get_daily_movements_report()
            fal = self.sheet_service.get_stock_report()
            full = f"{rep}\n\n{fal}"
            if len(full) > 4000: full = full[:4000]
            await query.edit_message_text(full, parse_mode='Markdown', reply_markup=KeyboardBuilder.admin_action_menu())
            return BotStates.SELECT_ACTION
            
        if action == 'INGRESAR_STOCK':
            context.user_data['next_action'] = 'INGRESAR'
            await query.edit_message_text("🔐 PIN Encargado:")
            return BotStates.CHECK_PIN
            
        if action == 'HACER_PEDIDO':
            context.user_data['next_action'] = 'PEDIDO'
            await query.edit_message_text("🔐 PIN Pedidos:")
            return BotStates.CHECK_PIN 
        
        if action == 'REGISTRAR_PAGO':
            provs = self.sheet_service.get_suppliers_list()
            if not provs: 
                await query.edit_message_text("⚠️ No hay proveedores.") 
                return BotStates.SELECT_ACTION
            await query.edit_message_text("💸 ¿A quién pagamos?", reply_markup=KeyboardBuilder.provider_menu(provs))
            return BotStates.SELECT_PROVIDER_PAY

        if action == 'VER_INGRESOS':
            reporte = self.sheet_service.get_recent_incomes()
            await query.edit_message_text(reporte, parse_mode='Markdown', reply_markup=KeyboardBuilder.admin_action_menu())
            return BotStates.SELECT_ACTION

        if action == 'BUSCAR_PRODUCTO':
            await query.edit_message_text("🔍 Escribí el nombre del producto a buscar (ej: Coca):")
            return BotStates.SEARCH_PRODUCT
            
        return BotStates.SELECT_ACTION

    async def verify_pin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text in [settings.PIN_ENCARGADO, settings.PIN_ADMIN]:
            # Opción Pedido
            if context.user_data.get('next_action') == 'PEDIDO':
                await update.message.reply_text("🔓 Acceso OK. ¿Quién hace el pedido?")
                return BotStates.ORDER_INPUT_NAME # <--- Esto llamará a order_name_received
            
            # Opción Ingreso Stock
            context.user_data['modo'] = 'INGRESO'
            kb = [[InlineKeyboardButton(s, callback_data=s) for s in ["Cocina", "Barra"]],
                  [InlineKeyboardButton(s, callback_data=s) for s in ["Salon", "Deposito"]]]
            await update.message.reply_text("🔓 Acceso OK. ¿Qué SECTOR?", reply_markup=InlineKeyboardMarkup(kb))
            return BotStates.SELECT_SECTOR
            
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