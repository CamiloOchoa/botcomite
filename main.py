import os
import logging
import re

# --- Imports Limpios ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    ConversationHandler, # <-- Importar directamente
    MessageHandler,
    filters,
    ContextTypes,
    ApplicationHandlerStop # <-- Importar excepción
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Estado para la Conversación ---
TYPING_REPLY = 0

# --- IDs y Variables Globales ---
TOKEN = None; GRUPO_ID = None; BOT_USERNAME = None; GROUP_LINK = None
TEMA_BOTON_CONSULTAS_COMITE = 272; TEMA_BOTON_SUGERENCIAS_COMITE = 291
TEMA_CONSULTAS_EXTERNO = 69; TEMA_SUGERENCIAS_EXTERNO = 71
GRUPO_EXTERNO_ID = -1002433074372

# --- Validación de Variables de Entorno ---
def validar_variables():
    # ... (Sin cambios) ...
    global TOKEN, GRUPO_ID, BOT_USERNAME, GROUP_LINK
    try: TOKEN = os.environ["TELEGRAM_TOKEN"].strip(); #... (resto igual)
    except Exception as e: logger.critical(f"Error validando: {e}", exc_info=True); return False
    logger.info("✅ Variables validadas") # Mensaje más corto
    return True # Asumiendo que el resto de la validación está bien

# --- Función para Enviar Botones Iniciales ---
async def post_initial_buttons(context: CallbackContext) -> bool:
    """ Envía los mensajes iniciales con botones URL. """
    # ... (Sin cambios) ...
    if not BOT_USERNAME or not GRUPO_ID: return False; #... (resto igual)
    return True # Asumiendo éxito si no hay excepciones

# --- Comando para Postear Botones ---
async def post_buttons_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Comando /postbotones (uso privado). """
    # ... (Sin cambios) ...
    user = update.effective_user; chat = update.effective_chat; #... (resto igual)

# --- Handler para /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """ Manejador del comando /start. """
    # ... (Sin cambios) ...
    user = update.effective_user; chat = update.effective_chat; args = context.args; #... (resto igual)
    return TYPING_REPLY # o ConversationHandler.END o None

# --- Handler para Recibir Texto (Consulta/Sugerencia) ---
# --- INTENTO FINAL: Combinando END y Stop ---
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: # Volver a int
    """
    Recibe texto, valida, envía, confirma.
    Retorna END y luego lanza ApplicationHandlerStop.
    """
    user = update.effective_user; message = update.message
    if not message or not message.text: return TYPING_REPLY
    user_text = message.text
    action_type = context.user_data.pop('action_type', None)

    if not action_type:
        logger.warning(f"receive_text sin action_type {user.id}.")
        # No debería pasar, pero si pasa, terminar y detener
        return ConversationHandler.END # Intentar terminar limpiamente primero
        # raise ApplicationHandlerStop # No lanzar aquí si no se procesó nada

    logger.info(f"Procesando '{action_type}' de {user.id}: {user_text[:50]}...")
    found_forbidden_topic = None

    # Validación (solo consultas)
    if action_type == 'consulta':
        text_lower = user_text.lower(); forbidden_map = { "bolsa de horas": "bolsa de horas", "permiso": "permisos", "permisos": "permisos", "incapacidad temporal": "incapacidad temporal", "baja": "incapacidad temporal", "excedencia": "excedencias", "excedencias": "excedencias" }
        for keyword, topic_name in forbidden_map.items():
            if keyword in text_lower: found_forbidden_topic = topic_name; break
        if found_forbidden_topic:
            logger.warning(f"Consulta {user.id} rechazada:'{found_forbidden_topic}'")
            error_msg = (f"❌ Consulta sobre '{found_forbidden_topic}' no procesada. Revisa info.")
            try: await update.message.reply_text(error_msg)
            except Exception as e: logger.error(f"Error msg rechazo {user.id}: {e}")
            context.user_data.clear()
            # Retornar END y luego detener
            # Esta combinación podría ser la clave
            context.application.create_task(context.application.stop_propagation_task(update)) # Programar detención
            return ConversationHandler.END

    # Envío si no fue rechazada
    if not found_forbidden_topic:
        target_chat_id = None
        if action_type == 'consulta': target_chat_id = GRUPO_EXTERNO_ID; target_thread_id = TEMA_CONSULTAS_EXTERNO
        elif action_type == 'sugerencia': target_chat_id = GRUPO_EXTERNO_ID; target_thread_id = TEMA_SUGERENCIAS_EXTERNO
        else: # Error interno
            logger.error(f"Tipo '{action_type}' inesperado {user.id}")
            try: await update.message.reply_text("Error interno.")
            except Exception: pass
            context.user_data.clear()
            context.application.create_task(context.application.stop_propagation_task(update)) # Programar detención
            return ConversationHandler.END # Terminar por error

        if target_chat_id:
            user_info = f"{user.full_name}" + (f" (@{user.username})" if user.username else ""); fwd_msg = f"ℹ️ **{action_type.capitalize()} de {user_info}**:\n\n{user_text}"
            send_success = False
            try: await context.bot.send_message(chat_id=target_chat_id, message_thread_id=target_thread_id, text=fwd_msg, parse_mode=ParseMode.MARKDOWN); logger.info(f"{action_type.capitalize()} de {user.id} enviada a {target_chat_id}(T:{target_thread_id})"); send_success = True
            except Exception as e: logger.error(f"Error enviando {action_type} de {user.id}: {e}", exc_info=True)

            if send_success:
                try: await update.message.reply_text(f"✅ ¡Tu {action_type} ha sido enviada!"); logger.info(f"Confirmación {user.id}")
                except Exception as e: logger.error(f"Error confirmación {user.id}: {e}")
            else:
                try: await update.message.reply_text(f"❌ Error al enviar. Contacta admin.")
                except Exception as e: logger.error(f"Error msg fallo {user.id}: {e}")

            context.user_data.clear()
            context.application.create_task(context.application.stop_propagation_task(update)) # Programar detención
            return ConversationHandler.END # Terminar tras procesar

    # Fallback final (no debería alcanzarse)
    logger.warning(f"receive_text alcanzó fin inesperado {user.id}.")
    context.user_data.clear()
    context.application.create_task(context.application.stop_propagation_task(update)) # Programar detención
    return ConversationHandler.END

# --- Handler para /cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ Cancela la conversación activa. """
    # ... (Sin cambios) ...
    user = update.effective_user; logger.info(f"User {user.id} canceló.")
    was_in_conversation = bool(context.user_data); context.user_data.clear()
    msg = 'Operación cancelada.' if was_in_conversation else 'No hay operación activa para cancelar.'
    await update.message.reply_text(msg); return ConversationHandler.END

# --- Handler para Mensajes Inesperados ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Responde a mensajes de texto inesperados en privado. """
    # ... (Sin cambios, mantiene el check de 'action_type') ...
    user = update.effective_user; chat = update.effective_chat
    if not chat or chat.type != 'private' or not update.message or not update.message.text: return
    if 'action_type' in context.user_data: logger.debug(f"handle_unexpected_message: Ignorando msg de {user.id} ('action_type' existe)."); return
    logger.info(f"Mensaje inesperado de {user.id}: {update.message.text[:50]}...")
    if not GRUPO_ID or GRUPO_ID >= 0: await update.message.reply_text("Usa botones grupo."); return
    try: short_id = str(GRUPO_ID).replace("-100", "", 1); url_con = f"https://t.me/c/{short_id}/{TEMA_BOTON_CONSULTAS_COMITE}"; url_sug = f"https://t.me/c/{short_id}/{TEMA_BOTON_SUGERENCIAS_COMITE}"; texto = ("Hola 👋. Para consultas/sugerencias, usa los botones en los temas del grupo comité:"); kb = [[InlineKeyboardButton("Ir a Consultas 🤔", url=url_con)], [InlineKeyboardButton("Ir a Sugerencias ✨", url=url_sug)]]; markup = InlineKeyboardMarkup(kb); await update.message.reply_text(texto, reply_markup=markup)
    except Exception as e: logger.error(f"Error handle_unexpected_message {user.id}: {e}", exc_info=True); await update.message.reply_text("Usa botones grupo.")

# --- Configuración y Ejecución Principal ---
def main() -> None:
    """ Configura y ejecuta el bot. """
    if not validar_variables(): logger.critical("--- BOT DETENIDO: ERRORES CONFIG ---"); return
    application = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start, filters=filters.ChatType.PRIVATE)],
        states={ TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)] }, # Usando receive_text que retorna END
        fallbacks=[ CommandHandler('cancel', cancel, filters=filters.ChatType.PRIVATE), CommandHandler('start', start, filters=filters.ChatType.PRIVATE)],
        allow_reentry=True, per_user=True, per_chat=True, name="consulta_sugerencia_conv", persistent=False
    )
    # --- Registro de Handlers ---
    application.add_handler(conv_handler, group=0)
    application.add_handler(CommandHandler("postbotones", post_buttons_command, filters=filters.ChatType.PRIVATE), group=1)
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_unexpected_message), group=2)
    #---
    logger.info("--- Iniciando Polling del Bot ---")
    try: application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e: logger.critical(f"--- ERROR CRÍTICO POLLING ---: {e}", exc_info=True)
    finally: logger.info("--- Bot Detenido ---")

if __name__ == '__main__':
    try: main()
    except Exception as e: logger.critical(f"Error fatal inicializando bot: {e}", exc_info=True)
