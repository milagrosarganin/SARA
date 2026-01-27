import os
import sys

# Aseguramos que el directorio de trabajo sea el correcto
carpeta_del_bot = os.path.dirname(os.path.abspath(__file__))
os.chdir(carpeta_del_bot)

import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    CallbackQueryHandler, 
    ConversationHandler, 
    CommandHandler, 
    MessageHandler, 
    filters
)
from src.bot.handlers import StockFlowController
from src.bot.states import BotStates
from src.config import settings

# Configuración básica de logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Verificación de entorno
if not settings.is_valid:
    print("❌ Error: Faltan variables en el archivo .env")
    exit(1)

class StockBotApp:
    def __init__(self):
        # Construimos la aplicación con el Token
        self.application = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()
        
        # Iniciamos el controlador de flujo
        self.flow_controller = StockFlowController()

        # --- DEFINICIÓN DEL CEREBRO (ConversationHandler) ---
        self.conversation_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.flow_controller.start)],
            states={
                # 1. FLUJO INICIAL: Elige Sector -> Pide Nombre -> Elige Local
                BotStates.SELECT_SECTOR: [
                    CallbackQueryHandler(self.flow_controller.sector_selected)
                ],
                BotStates.INPUT_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.name_received)
                ],
                BotStates.SELECT_LOCAL: [
                    CallbackQueryHandler(self.flow_controller.local_selected)
                ],

                # 2. FLUJO MANUAL (Categoría -> Producto -> Cantidad)
                BotStates.SELECT_CATEGORY: [
                    CallbackQueryHandler(self.flow_controller.category_selected)
                ],
                BotStates.SELECT_PRODUCT: [
                    CallbackQueryHandler(self.flow_controller.product_selected)
                ],
                BotStates.INPUT_QUANTITY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.quantity_received)
                ],
                BotStates.PREGUNTA_CONTINUAR: [
                    CallbackQueryHandler(self.flow_controller.decision_continuar_retiro)
                ],

                # 3. --- NUEVOS ESTADOS INTELIGENTES (LO QUE FALTABA) ---
                
                # A) RETIRO MASIVO (Listas pegadas)
                BotStates.INPUT_BATCH_LIST: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.process_batch_list)
                ],

                # B) INGRESO MASIVO (Fotos de Facturas o Texto)
                BotStates.INPUT_BATCH_ENTRY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.process_batch_entry),
                    MessageHandler(filters.PHOTO, self.flow_controller.process_batch_entry)
                ],

                # C) DESHACER (Undo)
                BotStates.SELECT_UNDO: [
                    CallbackQueryHandler(self.flow_controller.undo_item_selected)
                ],

                # D) PRODUCCIÓN PROPIA (Loop)
                BotStates.CONFIRM_MORE_PRODUCCION: [
                    CallbackQueryHandler(self.flow_controller.confirm_more_production)
                ],

                # 4. FLUJO DE ADMIN / ENCARGADO / MENÚS
                BotStates.CHECK_PIN: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.verify_pin)
                ],
                BotStates.SELECT_ACTION: [
                    CallbackQueryHandler(self.flow_controller.handle_admin_action)
                ],
                
                # 5. FLUJO DE INGRESO MANUAL DETALLADO
                BotStates.ASK_SUPPLIER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.supplier_received)
                ],
                BotStates.SELECT_SUPPLIER: [
                    CallbackQueryHandler(self.flow_controller.supplier_selected)
                ],
                BotStates.ASK_TOTAL_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.amount_received)
                ],
                BotStates.ASK_INVOICE_TYPE: [
                    CallbackQueryHandler(self.flow_controller.invoice_type_selected),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.invoice_type_fallback)
                ],
                BotStates.ASK_EXPIRATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.expiration_received)
                ],
                BotStates.ASK_UNIT_PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.price_received)
                ],
                BotStates.CONFIRM_MORE_PRODUCTS: [
                    CallbackQueryHandler(self.flow_controller.more_products_decision)
                ],
                BotStates.CHECK_SAME_INVOICE: [
                    CallbackQueryHandler(self.flow_controller.check_same_invoice)
                ],

                # 6. REPORTES, COMENTARIOS Y PEDIDOS
                BotStates.INPUT_COMMENT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.comment_received)
                ],
                BotStates.SEARCH_PRODUCT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.search_product_received)
                ],
                BotStates.SELECT_REPORT_RANGE: [
                    CallbackQueryHandler(self.flow_controller.report_range_selected)
                ],
                BotStates.SELECT_REPORT_TYPE: [
                    CallbackQueryHandler(self.flow_controller.report_type_selected)
                ],
                BotStates.ORDER_INPUT_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.order_name_received)
                ],
                BotStates.ORDER_PRODUCT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.order_product_received)
                ],
                BotStates.ORDER_QUANTITY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.order_quantity_received)
                ],
                BotStates.ORDER_SUPPLIER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.order_supplier_received)
                ],
                BotStates.SELECT_PROVIDER_PAY: [
                    CallbackQueryHandler(self.flow_controller.provider_selected_for_pay)
                ],
                BotStates.INPUT_PAYMENT_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.payment_amount_received)
                ],
                BotStates.SELECT_ACTION: [
                    # AGREGAR ESTA LÍNEA PARA QUE EL BOTÓN FUNCIONE:
                    CallbackQueryHandler(self.flow_controller.btn_cargar_factura_pressed, pattern='^BTN_CARGAR_FACTURA$'),
                    CallbackQueryHandler(self.flow_controller.handle_admin_action)
                ],
                BotStates.WAITING_FOR_FACTURA_PHOTO: [
                    MessageHandler(filters.PHOTO, self.flow_controller.foto_factura_received)
                ],
            },
            fallbacks=[
                CommandHandler('start', self.flow_controller.start),
                CallbackQueryHandler(self.flow_controller.start, pattern='^BACK_MAIN$')
            ],
            per_user=True  # Importante: mantiene la memoria separada por usuario
        )

        self.application.add_handler(self.conversation_handler)

    def run(self):
        print("🚀 Bot de Stock Iniciado (Sistema Completo)...")
        self.application.run_polling()

if __name__ == '__main__':
    bot = StockBotApp()
    bot.run()