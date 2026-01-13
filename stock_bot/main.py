import os
import sys

carpeta_del_bot = os.path.dirname(os.path.abspath(__file__))
os.chdir(carpeta_del_bot)

import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ConversationHandler, CommandHandler, MessageHandler, filters
from src.bot.handlers import StockFlowController
from src.bot.states import BotStates
from src.config import settings

# Configuración básica de logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

if not settings.is_valid:
    print("❌ Error: Faltan variables en el archivo .env")
    exit(1)

class StockBotApp:
    def __init__(self):
        self.application = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()
        self.flow_controller = StockFlowController()

        # Definimos el manejador de la conversación con TODOS los pasos nuevos
        self.conversation_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.flow_controller.start)],
            states={
                # 1. Elige Sector -> Pide Nombre
                BotStates.SELECT_SECTOR: [
                    CallbackQueryHandler(self.flow_controller.sector_selected)
                ],
                # 2. Recibe Nombre -> Pide Local (ESTO ES LO QUE TE FALTABA)
                BotStates.INPUT_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.name_received)
                ],
                # 3. Elige Local -> Muestra Categorías
                BotStates.SELECT_LOCAL: [
                    CallbackQueryHandler(self.flow_controller.local_selected)
                ],
                # 4. Elige Categoría -> Muestra Productos
                BotStates.SELECT_CATEGORY: [
                    CallbackQueryHandler(self.flow_controller.category_selected)
                ],
                # 5. Selección de Producto -> Pide Cantidad
                BotStates.SELECT_PRODUCT: [
                    CallbackQueryHandler(self.flow_controller.product_selected)
                ],
                # 6. Recibe Cantidad -> Procesa y vuelve al inicio
                BotStates.INPUT_QUANTITY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.quantity_received)
                ],
                # --- Estados Extras ---
                # Menú de Jefes
                BotStates.SELECT_ACTION: [
                    CallbackQueryHandler(self.flow_controller.handle_admin_action)
                ],
                # Ingreso de PIN
                BotStates.CHECK_PIN: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.verify_pin)
                ],
                BotStates.INPUT_COMMENT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.comment_received)
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
                BotStates.ASK_SUPPLIER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.supplier_received)
                ],
                BotStates.ASK_TOTAL_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.amount_received)
                ],
                BotStates.ASK_INVOICE_TYPE: [
                    CallbackQueryHandler(self.flow_controller.invoice_type_selected)
                ],
                BotStates.ASK_EXPIRATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.expiration_received)
                ],
                BotStates.CONFIRM_MORE_PRODUCTS: [
                    CallbackQueryHandler(self.flow_controller.more_products_decision)
                ],
                BotStates.CHECK_SAME_INVOICE: [
                    CallbackQueryHandler(self.flow_controller.check_same_invoice)
                ],
                # --- FLUJO DE INGRESO ACTUALIZADO ---
                BotStates.ASK_SUPPLIER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.supplier_received)
                ],
                # NUEVO: Estado para el clic del proveedor
                BotStates.SELECT_SUPPLIER: [
                    CallbackQueryHandler(self.flow_controller.supplier_selected)
                ],

                BotStates.ASK_TOTAL_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.amount_received)
                ],

                BotStates.ASK_INVOICE_TYPE: [
                    CallbackQueryHandler(self.flow_controller.invoice_type_selected),
                    # Agregamos esto para atrapar si escriben en vez de tocar botón:
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.invoice_type_fallback)
                ],
                BotStates.ASK_UNIT_PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.flow_controller.price_received)
                    ],
            },
            fallbacks=[CommandHandler('start', self.flow_controller.start)]
        )

        self.application.add_handler(self.conversation_handler)

    def run(self):
        print("🚀 Bot de Stock Iniciado (Sistema Completo)...")
        self.application.run_polling()

if __name__ == '__main__':
    bot = StockBotApp()
    bot.run()