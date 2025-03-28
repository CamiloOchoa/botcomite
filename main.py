import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler

# Configuración del logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Validación de variables de entorno
def validar_variables():
    try:
        global TOKEN, GRUPO_ID, BOT_USERNAME, GROUP_LINK
        TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
        if not TOKEN or ":" not in TOKEN:
            raise ValueError("Formato de token inválido")
        
        grupo_id_raw = os.environ["GROUP_ID"].strip()
        grupo_id_limpio = re.sub(r"[^-\d]", "", grupo_id_raw)
        GRUPO_ID = int(grupo_id_limpio.split("=")[-1]) if "=" in grupo_id_limpio else int(grupo_id_limpio)
        if not (-1009999999999 < GRUPO_ID < -1000000000000):
            raise ValueError("ID de grupo inválido")
        
        BOT_USERNAME = os.environ["BOT_USERNAME"].strip().lstrip('@')
        if not BOT_USERNAME:
            raise ValueError("BOT_USERNAME vacío")
        
        GROUP_LINK = os.environ["GROUP_LINK"].strip()
        if not GROUP_LINK.startswith("https://t.me/"):
            raise ValueError("Enlace de grupo inválido")
        
        logger.info("✅ Variables validadas correctamente")
        return True
    except Exception as e:
        logger.critical(f"❌ Error de configuración: {str(e)}")
        return False

if not validar_variables():
    exit(1)

# IDs de los temas
TEMA_CONSULTAS_SUGERENCIAS = 272  # Tema dentro del grupo del comité
TEMA_CONSULTAS_EXTERNO = 69  # Tema de consultas en el grupo externo
TEMA_SUGERENCIAS_EXTERNO = 71  # Tema de sugerencias en el grupo externo
GRUPO_EXTERNO_ID = -1002433074372  # ID del grupo externo

# Comando /start
def start(update: Update, context: CallbackContext) -> None:
    mensaje = "Bienvenido. ¿Quieres hacer una consulta o una sugerencia?"
    keyboard = [[InlineKeyboardButton("Consulta", callback_data='consulta')],
                [InlineKeyboardButton("Sugerencia", callback_data='sugerencia')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.bot.send_message(chat_id=GRUPO_ID, message_thread_id=TEMA_CONSULTAS_SUGERENCIAS, text=mensaje, reply_markup=reply_markup)

# Manejo de botones
def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user_message = f"{query.from_user.first_name} ha enviado una {query.data}:\n" + query.message.text
    
    if query.data == 'consulta':
        context.bot.send_message(chat_id=GRUPO_EXTERNO_ID, message_thread_id=TEMA_CONSULTAS_EXTERNO, text=user_message)
    elif query.data == 'sugerencia':
        context.bot.send_message(chat_id=GRUPO_EXTERNO_ID, message_thread_id=TEMA_SUGERENCIAS_EXTERNO, text=user_message)
    
    query.edit_message_text(text="Tu mensaje ha sido enviado correctamente.")

# Configuración del bot
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_callback))
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
