import os
import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

# --- Toda la configuración, validación y funciones de handlers (start, receive_text, etc.) ---
# --- permanecen EXACTAMENTE IGUAL que en la versión anterior ---
# ... (incluyendo la validación de palabras clave en receive_text) ...
# ... (y handle_unexpected_message) ...

# --- Configuración y Ejecución (Ajustes en el registro de handlers) ---
def main() -> None:
    """Inicia el bot."""
    if not validar_variables():
       logger.critical("Deteniendo bot por errores config.")
       return

    application = Application.builder().token(TOKEN).build()

    # --- Conversation Handler ---
    # Debe manejar /start en privado como entrada y fallback
    # y los mensajes de texto cuando está en estado TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start, filters=filters.ChatType.PRIVATE)],
        states={
            TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel, filters=filters.ChatType.PRIVATE),
            # Re-evaluar /start si se envía a mitad de conversación
            CommandHandler('start', start, filters=filters.ChatType.PRIVATE)
        ],
        # Permitir reentrada si el usuario usa /start de nuevo
        allow_reentry=True,
        per_user=True,
        per_chat=True, # Importante para estado en chat privado
    )

    # --- Añadir Handlers POR ORDEN DE PRIORIDAD (Usando Grupos) ---

    # GRUPO 0: La conversación tiene la máxima prioridad
    application.add_handler(conv_handler, group=0)

    # GRUPO 1: Comandos específicos que NO son parte de la conversación
    application.add_handler(CommandHandler("postbotones", post_buttons_command, filters=filters.ChatType.PRIVATE), group=1)
    # Si tuvieras otros comandos como /help, irían aquí también

    # GRUPO 2: Mensajes de texto inesperados en privado (fallback)
    # Se ejecuta solo si la conversación NO lo capturó y NO es un comando
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
        handle_unexpected_message
    ), group=2)

    # --- ELIMINADO: El CommandHandler genérico para /start al final ---
    # Ya no es necesario, start() maneja el caso de grupos internamente
    # y conv_handler maneja el caso privado.

    logger.info("Iniciando polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot detenido.")


# --- RESTO DEL CÓDIGO (validar_variables, start, receive_text, etc.) ---
# --- ES EL MISMO QUE LA VERSIÓN ANTERIOR ---
# ... (Asegúrate de tener todo el código anterior aquí) ...

if __name__ == '__main__':
    main()
