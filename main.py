import os
import logging
import re

# --- Imports Limpios ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ApplicationHandlerStop # Aunque no la usemos activamente ahora, es bueno tenerla
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
    """Valida las variables de entorno necesarias."""
    global TOKEN, GRUPO_ID, BOT_USERNAME, GROUP_LINK
    try:
        TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
        if not TOKEN or ":" not in TOKEN: raise ValueError("Token inválido")
        grupo_id_raw = os.environ["GROUP_ID"].strip()
        GRUPO_ID = int(re.sub(r"[^-\d]", "", grupo_id_raw))
        if not (GRUPO_ID < -100000000000): logger.warning(f"GROUP_ID ({GRUPO_ID}) inusual.")
        BOT_USERNAME = os.environ["BOT_USERNAME"].strip().lstrip('@')
        if not BOT_USERNAME: raise ValueError("BOT_USERNAME vacío")
        GROUP_LINK = os.environ.get("GROUP_LINK", "").strip() or None
        if GROUP_LINK and not GROUP_LINK.startswith("https://t.me/"): logger.warning("GROUP_LINK inválido."); GROUP_LINK = None
        logger.info(f"GRUPO_ID (Comité): {GRUPO_ID}")
        logger.info(f"TEMA_BOTON_CONSULTAS_COMITE: {TEMA_BOTON_CONSULTAS_COMITE}")
        logger.info(f"TEMA_BOTON_SUGERENCIAS_COMITE: {TEMA_BOTON_SUGERENCIAS_COMITE}")
        logger.info(f"GRUPO_EXTERNO_ID: {GRUPO_EXTERNO_ID}")
        logger.info(f"TEMA_CONSULTAS_EXTERNO: {TEMA_CONSULTAS_EXTERNO}")
        logger.info(f"TEMA_SUGERENCIAS_EXTERNO: {TEMA_SUGERENCIAS_EXTERNO}")
        logger.info(f"BOT_USERNAME: @{BOT_USERNAME}")
        if GROUP_LINK: logger.info(f"GROUP_LINK: {GROUP_LINK}")
        if not isinstance(TEMA_CONSULTAS_EXTERNO, int) or TEMA_CONSULTAS_EXTERNO <= 0: logger.warning(f"TEMA_CONSULTAS_EXTERNO ({TEMA_CONSULTAS_EXTERNO}) inválido.")
        if not isinstance(TEMA_SUGERENCIAS_EXTERNO, int) or TEMA_SUGERENCIAS_EXTERNO <= 0: logger.warning(f"TEMA_SUGERENCIAS_EXTERNO ({TEMA_SUGERENCIAS_EXTERNO}) inválido.")
        logger.info("✅ Variables validadas correctamente")
        return True
    except KeyError as e: logger.critical(f"❌ Falta var entorno: {e}"); return False
    except ValueError as e: logger.critical(f"❌ Error config: {e}"); return False
    except Exception as e: logger.critical(f"❌ Error config inesperado: {e}", exc_info=True); return False

# --- Función para Enviar Botones Iniciales ---
async def post_initial_buttons(context: CallbackContext) -> bool:
    """ Envía los mensajes iniciales con botones URL. """
    if not BOT_USERNAME or not GRUPO_ID: return False
    if TEMA_BOTON_CONSULTAS_COMITE <= 0 or TEMA_BOTON_SUGERENCIAS_COMITE <= 0: return False
    success_count = 0
    # Consulta
    msg_con = ("Pulsa el botón si tienes alguna consulta sobre algún tema que no se haya visto en el grupo(permisos, bolsa de horas, excedencias, etc...). Recuerda que estás consultas son privadas y solo pueden verlas los miembros del comité. La consulta debe ser enviada en un solo mensaje.")
    url_con = f"https://t.me/{BOT_USERNAME}?start=iniciar_consulta"; kb_con = [[InlineKeyboardButton("Iniciar Consulta 🙋‍♂️", url=url_con)]]; markup_con = InlineKeyboardMarkup(kb_con)
    try: await context.bot.send_message(chat_id=GRUPO_ID, message_thread_id=TEMA_BOTON_CONSULTAS_COMITE, text=msg_con, reply_markup=markup_con); logger.info(f"Btn Consulta T:{TEMA_BOTON_CONSULTAS_COMITE}"); success_count += 1
    except Exception as e: logger.error(f"Error Btn Consulta T:{TEMA_BOTON_CONSULTAS_COMITE}: {e}", exc_info=False)
    # Sugerencia
    msg_sug = ("Pulsa el botón si tienes alguna sugerencia para mejorar el grupo o el funcionamiento del comité. Recuerda que estás sugerencias son privadas y solo pueden verlas los miembros del comité. La sugerencia debe ser enviada en un solo mensaje.")
    url_sug = f"https://t.me/{BOT_USERNAME}?start=iniciar_sugerencia"; kb_sug = [[InlineKeyboardButton("Iniciar Sugerencia 💡", url=url_sug)]]; markup_sug = InlineKeyboardMarkup(kb_sug)
    try: await context.bot.send_message(chat_id=GRUPO_ID, message_thread_id=TEMA_BOTON_SUGERENCIAS_COMITE, text=msg_sug, reply_markup=markup_sug); logger.info(f"Btn Sugerencia T:{TEMA_BOTON_SUGERENCIAS_COMITE}"); success_count += 1
    except Exception as e: logger.error(f"Error Btn Sugerencia T:{TEMA_BOTON_SUGERENCIAS_COMITE}: {e}", exc_info=False)
    return success_count > 0

# --- Comando para Postear Botones ---
async def post_buttons_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Comando /postbotones (uso privado). """
    user = update.effective_user; chat = update.effective_chat
    if not chat or chat.type != 'private': return
    logger.info(f"/postbotones de {user.id}. Ejecutando...")
    await update.message.reply_text("Intentando publicar/actualizar botones...")
    try: success = await post_initial_buttons(context)
    except Exception as e: logger.error(f"Excepción post_initial_buttons por {user.id}: {e}", exc_info=True); await update.message.reply_text("❌ Error."); return
    if success: await update.message.reply_text("✅ ¡Hecho!")
    else: await update.message.reply_text("⚠️ Error al enviar uno o ambos botones.")

# --- Handler para /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """ Manejador del comando /start. """
    user = update.effective_user; chat = update.effective_chat; args = context.args
    logger.info(f"/start de {user.id} chat:{chat.id if chat else '?'} ({chat.type if chat else '?'}). Args:{args}")
    if chat and chat.type == "private" and args:
        payload = args[0]; action_type = None
        if payload == "iniciar_consulta": action_type = "consulta"
        elif payload == "iniciar_sugerencia": action_type = "sugerencia"
        if action_type: context.user_data.clear(); logger.info(f"Payload '{payload}' de {user.id}. Iniciando {action_type}."); context.user_data['action_type'] = action_type; prompt = f"¡Hola {user.first_name}! Escribe tu {action_type}."; await update.message.reply_text(prompt); return TYPING_REPLY
        else: logger.warning(f"Payload desconocido '{payload}' de {user.id}."); await update.message.reply_text("Enlace inválido."); context.user_data.clear(); return ConversationHandler.END
    elif chat and chat.type == "private": logger.info(f"/start simple de {user.id}."); await update.message.reply_text(f"¡Hola {user.first_name}! Usa los botones del grupo."); context.user_data.clear(); return ConversationHandler.END
    # Ignorar en otros tipos de chat
    return None

# --- Handler para Recibir Texto (Consulta/Sugerencia) ---
# --- CORREGIDO: SyntaxError en bloque if found_forbidden_topic ---
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ Recibe texto en privado. Valida. Envía. Confirma. Retorna END. """
    user = update.effective_user; message = update.message
    if not message or not message.text: return TYPING_REPLY
    user_text = message.text
    action_type = context.user_data.pop('action_type', None)

    if not action_type: logger.warning(f"receive_text sin action_type para {user.id}. Terminando."); return ConversationHandler.END

    logger.info(f"Procesando '{action_type}' de {user.id}: {user_text[:50]}...")
    found_forbidden_topic = None

    # Validación (solo consultas)
    if action_type == 'consulta':
        text_lower = user_text.lower(); forbidden_map = { "bolsa de horas": "bolsa de horas", "permiso": "permisos", "permisos": "permisos", "incapacidad temporal": "incapacidad temporal", "baja": "incapacidad temporal", "excedencia": "excedencias", "excedencias": "excedencias" }
        for keyword, topic_name in forbidden_map.items():
            if keyword in text_lower: found_forbidden_topic = topic_name; break
        # --- BLOQUE if CORREGIDO (separado en líneas) ---
        if found_forbidden_topic:
            logger.warning(f"Consulta {user.id} rechazada:'{found_forbidden_topic}'")
            error_msg = (f"❌ Consulta sobre '{found_forbidden_topic}' no procesada. Revisa info grupo/docs.")
            try:
                await update.message.reply_text(error_msg)
            except Exception as e_reply:
                 logger.error(f"Error enviando msg rechazo a {user.id}: {e_reply}")
            context.user_data.clear()
            return ConversationHandler.END # Terminar aquí si es rechazada
        # --- FIN BLOQUE if CORREGIDO ---

    # Envío si no fue rechazada
    if not found_forbidden_topic:
        target_chat_id = None
        if action_type == 'consulta': target_chat_id = GRUPO_EXTERNO_ID; target_thread_id = TEMA_CONSULTAS_EXTERNO
        elif action_type == 'sugerencia': target_chat_id = GRUPO_EXTERNO_ID; target_thread_id = TEMA_SUGERENCIAS_EXTERNO
        else:
            logger.error(f"Tipo '{action_type}' inesperado {user.id}")
            try: await update.message.reply_text("Error.")
            except Exception: pass
            context.user_data.clear()
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

    context.user_data.clear() # Asegurar limpieza
    return ConversationHandler.END # Terminar

# --- Handler para /cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ Cancela la conversación activa. """
    user = update.effective_user; logger.info(f"User {user.id} canceló.")
    was_in_conversation = bool(context.user_data)
    context.user_data.clear()
    msg = 'Operación cancelada.' if was_in_conversation else 'No hay operación activa para cancelar.'
    await update.message.reply_text(msg)
    return ConversationHandler.END

# --- Handler para Mensajes Inesperados ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Responde a mensajes de texto inesperados en privado. """
    user = update.effective_user; chat = update.effective_chat
    if not chat or chat.type != 'private' or not update.message or not update.message.text: return
    if 'action_type' in context.user_data: logger.debug(f"handle_unexpected_message: Ignorando msg de {user.id} ('action_type' existe)."); return # Ignorar si la conversación está activa

    logger.info(f"Mensaje inesperado de {user.id}: {update.message.text[:50]}...")
    if not GRUPO_ID or GRUPO_ID >= 0: await update.message.reply_text("Usa botones grupo."); return
    try:
        short_id = str(GRUPO_ID).replace("-100", "", 1); url_con = f"https://t.me/c/{short_id}/{TEMA_BOTON_CONSULTAS_COMITE}"; url_sug = f"https://t.me/c/{short_id}/{TEMA_BOTON_SUGERENCIAS_COMITE}"
        texto = ("Hola 👋. Para consultas/sugerencias, usa los botones en los temas del grupo comité:"); kb = [[InlineKeyboardButton("Ir a Consultas 🤔", url=url_con)], [InlineKeyboardButton("Ir a Sugerencias ✨", url=url_sug)]]; markup = InlineKeyboardMarkup(kb)
        await update.message.reply_text(texto, reply_markup=markup)
    except Exception as e: logger.error(f"Error handle_unexpected_message {user.id}: {e}", exc_info=True); await update.message.reply_text("Usa botones grupo.")

# --- Configuración y Ejecución Principal ---
def main() -> None:
    """ Configura y ejecuta el bot. """
    if not validar_variables(): logger.critical("--- BOT DETENIDO: ERRORES CONFIG ---"); return
    application = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start, filters=filters.ChatType.PRIVATE)],
        states={ TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)] },
        fallbacks=[ CommandHandler('cancel', cancel, filters=filters.ChatType.PRIVATE), CommandHandler('start', start, filters=filters.ChatType.PRIVATE)],
        allow_reentry=True, per_user=True, per_chat=True, name="consulta_sugerencia_conv", persistent=False
    )
    application.add_handler(conv_handler, group=0)
    application.add_handler(CommandHandler("postbotones", post_buttons_command, filters=filters.ChatType.PRIVATE), group=1)
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_unexpected_message), group=2)
    logger.info("--- Iniciando Polling del Bot ---")
    try: application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e: logger.critical(f"--- ERROR CRÍTICO POLLING ---: {e}", exc_info=True)
    finally: logger.info("--- Bot Detenido ---")

if __name__ == '__main__':
    try: main()
    except Exception as e: logger.critical(f"Error fatal inicializando bot: {e}", exc_info=True)
