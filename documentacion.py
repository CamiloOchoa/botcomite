from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Reemplaza 'TU_TOKEN_AQUI' con el token de tu bot
TOKEN = '7586734778:AAGB_F2I6KjErkNH6M8WZO9dzEdVwmo970c'

# IDs de chat y tema
CHAT_ID = -1002261336942 # Reemplaza con el ID de tu grupo
DOCUMENTACION_TEMA_ID = 11  # Reemplaza con el ID del tema DOCUMENTACIÓN

# URLs de los documentos
CALENDARIO_URL = 'https://ejemplo.com/calendario_laboral_2025.pdf'
CONVENIO_URL = 'https://ejemplo.com/convenio.pdf'
TABLAS_URL = 'https://ejemplo.com/tablas_salariales_2025.pdf'

async def enviar_documentacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía un mensaje al tema DOCUMENTACIÓN con botones de acceso a los documentos."""
    keyboard = [
        [InlineKeyboardButton("Calendario laboral 2025 📅", url=CALENDARIO_URL)],
        [InlineKeyboardButton("Convenio 📄", url=CONVENIO_URL)],
        [InlineKeyboardButton("Tablas salariales 2025 💰", url=TABLAS_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=CHAT_ID,
        message_thread_id=DOCUMENTACION_TEMA_ID,
        text="¿Qué documento quieres consultar?",
        reply_markup=reply_markup
    )

def main():
    """Inicia el bot y configura el comando /documentacion."""
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("documentacion", enviar_documentacion))
    application.run_polling()

if __name__ == '__main__':
    main()
