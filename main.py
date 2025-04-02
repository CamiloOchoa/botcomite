from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext

TOKEN = "TOKEN_DEL_BOT"
GROUP_ID = -1001234567890  # ID del grupo donde se enviarán los mensajes
DOCUMENTACION_TOPIC = 12345  # ID del tema de documentación en el grupo
CONSULTAS_TOPIC = 67890  # ID del tema de consultas en el grupo
SUGERENCIAS_TOPIC = 13579  # ID del tema de sugerencias en el grupo

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Consultar documentos", callback_data="docs")],
        [InlineKeyboardButton("Hacer una consulta", callback_data="consulta")],
        [InlineKeyboardButton("Hacer una sugerencia", callback_data="sugerencia")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Hola, ¿qué necesitas hacer?", reply_markup=reply_markup)

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "docs":
        keyboard = [
            [InlineKeyboardButton("Convenio", url=f"https://t.me/c/{abs(GROUP_ID)}/{DOCUMENTACION_TOPIC}")],
            [InlineKeyboardButton("Calendario laboral", url=f"https://t.me/c/{abs(GROUP_ID)}/{DOCUMENTACION_TOPIC}")],
            [InlineKeyboardButton("Tablas salariales", url=f"https://t.me/c/{abs(GROUP_ID)}/{DOCUMENTACION_TOPIC}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Aquí tienes los documentos disponibles:", reply_markup=reply_markup)
    
    elif query.data == "consulta":
        await query.message.reply_text(
            "Hola, por favor, escribe ahora tu consulta en un único mensaje.\n"
            "- Recuerda que las consultas solo las pueden ver los miembros del comité.\n"
            "- Recibirás una respuesta en la mayor brevedad posible."
        )
    
    elif query.data == "sugerencia":
        await query.message.reply_text(
            "Hola, por favor, escribe ahora tu sugerencia en un único mensaje.\n"
            "- Recuerda que las sugerencias solo las pueden ver los miembros del comité."
        )

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text
    user_id = update.message.from_user.id
    
    if user_message.startswith("/consulta"):
        if len(user_message[9:].strip()) < 30:
            keyboard = [[InlineKeyboardButton("Ir a consultas", url=f"https://t.me/c/{abs(GROUP_ID)}/{CONSULTAS_TOPIC}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Mensaje demasiado corto, el mensaje no ha sido enviado. "
                "Inicia una nueva consulta presionando el siguiente botón.",
                reply_markup=reply_markup
            )
            return
        await context.bot.send_message(GROUP_ID, text=f"Nueva consulta de {user_id}:\n{user_message[9:]}", message_thread_id=CONSULTAS_TOPIC)
    
    elif user_message.startswith("/sugerencia"):
        if len(user_message[12:].strip()) < 30:
            keyboard = [[InlineKeyboardButton("Ir a sugerencias", url=f"https://t.me/c/{abs(GROUP_ID)}/{SUGERENCIAS_TOPIC}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Mensaje demasiado corto, el mensaje no ha sido enviado. "
                "Inicia una nueva sugerencia presionando el siguiente botón.",
                reply_markup=reply_markup
            )
            return
        await context.bot.send_message(GROUP_ID, text=f"Nueva sugerencia de {user_id}:\n{user_message[12:]}", message_thread_id=SUGERENCIAS_TOPIC)

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()
