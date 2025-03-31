import os
import logging
import re
from telegram.ext import ConversationHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ApplicationHandlerStop # <-- IMPORTAR LA EXCEPCIÓN
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
TOKEN = None
GRUPO_ID = None # Grupo del Comité
BOT_USERNAME = None # Necesario para botones URL
GROUP_LINK = None # Opcional

# IDs de Temas en el GRUPO DEL COMITÉ (GRUPO_ID)
TEMA_BOTON_CONSULTAS_COMITE = 272  # <- REEMPLAZA SI ES NECESARIO
TEMA_BOTON_SUGERENCIAS_COMITE = 291 # <- REEMPLAZA SI ES NECESARIO

# IDs de Temas en el GRUPO EXTERNO (GRUPO_EXTERNO_ID)
TEMA_CONSULTAS_EXTERNO = 69
TEMA_SUGERENCIAS_EXTERNO = 71
GRUPO_EXTERNO_ID = -1002433074372

# --- Validación de Variables de Entorno ---
def validar_variables():
    """Valida las variables de entorno necesarias."""
    global TOKEN, GRUPO_ID, BOT_USERNAME, GROUP_LINK
    try:
        TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
        if not TOKEN or ":" not in TOKEN: raise ValueError("Token inválido")
        grupo_id_raw = os.environ["GROUP_ID"].strip()
        grupo_id_limpio = re.sub(r"[^-\d]", "", grupo_id_raw)
        GRUPO_ID = int(grupo_id_limpio)
        if not (GRUPO_ID < -100000000000): logger.warning(f"GROUP_ID ({GRUPO_ID}) inusual.")
        BOT_USERNAME = os.environ["BOT_USERNAME"].strip().lstrip('@')
        if not BOT_USERNAME: raise ValueError("BOT_USERNAME vacío")
        GROUP_LINK = os.environ.get("GROUP_LINK", "").strip()
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
    if not BOT_USERNAME or not GRUPO_ID: logger.error("post_initial_buttons: Vars incompletas."); return False
    if TEMA_BOTON_CONSULTAS_COMITE <= 0 or TEMA_BOTON_SUGERENCIAS_COMITE <= 0: logger.error("post_initial_buttons: IDs tema comité inválidos."); return False
    success_count = 0
    mensaje_consulta = ("Pulsa el botón si tienes alguna consulta sobre algún tema que no se haya visto en el grupo(permisos, bolsa de horas, excedencias, etc...). Recuerda que estás consultas son privadas y solo pueden verlas los miembros del comité. La consulta debe ser enviada en un solo mensaje.")
    url_consulta = f"https://t.me/{BOT_USERNAME}?start=iniciar_consulta"; kb_consulta = [[InlineKeyboardButton("Iniciar Consulta 🙋‍♂️", url=url_consulta)]]; markup_consulta = InlineKeyboardMarkup(kb_consulta)
    try: await context.bot.send_message(chat_id=GRUPO_ID, message_thread_id=TEMA_BOTON_CONSULTAS_COMITE, text=mensaje_consulta, reply_markup=markup_consulta); logger.info(f"Msg botón 'Consulta' T:{TEMA_BOTON_CONSULTAS_COMITE}"); success_count += 1
    except Exception as e: logger.error(f"Error enviando botón 'Consulta' T:{TEMA_BOTON_CONSULTAS_COMITE}: {e}", exc_info=isinstance(e, (ValueError, TypeError))) # Log traceback solo para errores inesperados
    mensaje_sugerencia = ("Pulsa el botón si tienes alguna sugerencia para mejorar el grupo o el funcionamiento del comité. Recuerda que estás sugerencias son privadas y solo pueden verlas los miembros del comité. La sugerencia debe ser enviada en un solo mensaje.")
    url_sugerencia = f"https://t.me/{BOT_USERNAME}?start=iniciar_sugerencia"; kb_sugerencia = [[InlineKeyboardButton("Iniciar Sugerencia 💡", url=url_sugerencia)]]; markup_sugerencia = InlineKeyboardMarkup(kb_sugerencia)
    try: await context.bot.send_message(chat_id=GRUPO_ID, message_thread_id=TEMA_BOTON_SUGERENCIAS_COMITE, text=mensaje_sugerencia, reply_markup=markup_sugerencia); logger.info(f"Msg botón 'Sugerencia' T:{TEMA_BOTON_SUGERENCIAS_COMITE}"); success_count += 1
    except Exception as e: logger.error(f"Error enviando botón 'Sugerencia' T:{TEMA_BOTON_SUGERENCIAS_COMITE}: {e}", exc_info=isinstance(e, (ValueError, TypeError)))
    return success_count > 0

# --- Comando para Postear Botones (Privado) ---
async def post_buttons_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Comando /postbotones para publicar/actualizar botones (uso privado). """
    user = update.effective_user; chat = update.effective_chat
    if not chat or chat.type != 'private': return
    logger.info(f"/postbotones recibido en privado de {user.id} ({user.full_name}). Ejecutando...")
    await update.message.reply_text("Recibido. Intentando publicar/actualizar botones...")
    try: success = await post_initial_buttons(context)
    except Exception as e: logger.error(f"Excepción en post_initial_buttons llamado por {user.id}: {e}", exc_info=True); await update.message.reply_text("❌ Error inesperado."); return
    if success: await update.message.reply_text("✅ ¡Hecho!")
    else: await update.message.reply_text("⚠️ Error al enviar uno o ambos botones. Revisa logs.")

# --- Handler para /start (Entrada a la Conversación) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """ Manejador del comando /start. """
    user = update.effective_user; chat = update.effective_chat; args = context.args
    start_context = f"chat {chat.id} ({chat.type})" if chat else "chat desconocido"; logger.info(f"/start de {user.id} ({user.full_name}) en {start_context}. Args: {args}")
    if chat and chat.type == "private" and args:
        payload = args[0]; action_type = None
        if payload == "iniciar_consulta": action_type = "consulta"
        elif payload == "iniciar_sugerencia": action_type = "sugerencia"
        if action_type: context.user_data.clear(); logger.info(f"Payload '{payload}' de {user.id}. Iniciando {action_type}."); context.user_data['action_type'] = action_type; prompt_message = f"¡Hola {user.first_name}! Escribe tu {action_type}."; await update.message.reply_text(prompt_message); return TYPING_REPLY
        else: logger.warning(f"Payload desconocido '{payload}' de {user.id}."); await update.message.reply_text("Enlace inválido."); context.user_data.clear(); return ConversationHandler.END
    elif chat and chat.type == "private": logger.info(f"/start simple de {user.id}."); await update.message.reply_text(f"¡Hola {user.first_name}! Usa los botones del grupo."); context.user_data.clear(); return ConversationHandler.END
    elif chat and chat.type in ["group", "supergroup", "channel"]: logger.info(f"/start en {chat.type} {chat.id}. Ignorando."); return None
    return ConversationHandler.END # Default a terminar

# --- MODIFICADO: receive_text volviendo a return ConversationHandler.END ---
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Recibe el texto en privado. Valida. Envía. Confirma.
    Retorna ConversationHandler.END para finalizar.
    """
    user = update.effective_user
    message = update.message
    if not message or not message.text:
        logger.warning(f"Update sin texto recibido en estado TYPING_REPLY de {user.id}. Ignorando.")
        return TYPING_REPLY # Mantener estado

    user_text = message.text
    # Usar get() primero para loguear, luego pop() para asegurar limpieza si existe
    action_type_check = context.user_data.get('action_type') # Solo para loguear si existe
    action_type = context.user_data.pop('action_type', None) # Obtener y eliminar

    if not action_type:
        # Si el pop devolvió None, la conversación ya terminó.
        # No deberíamos llegar aquí idealmente si el ConversationHandler funciona bien,
        # pero si lo hacemos, solo logueamos y terminamos.
        logger.warning(f"receive_text llamado PERO action_type ya no estaba en user_data para {user.id}. Estado original era: {action_type_check}. Terminando.")
        # No lanzar excepción aquí, simplemente terminar.
        return ConversationHandler.END

    logger.info(f"Procesando texto de {user.id} para '{action_type}': {user_text[:100]}...")
    found_forbidden_topic = None # Inicializar

    # Validación de Palabras Clave (SOLO para consultas)
    if action_type == 'consulta':
        text_lower = user_text.lower()
        forbidden_keywords_map = { "bolsa de horas": "bolsa de horas", "permiso": "permisos", "permisos": "permisos", "incapacidad temporal": "incapacidad temporal", "baja": "incapacidad temporal", "excedencia": "excedencias", "excedencias": "excedencias" }
        for keyword, topic_name in forbidden_keywords_map.items():
            if keyword in text_lower: found_forbidden_topic = topic_name; break
        if found_forbidden_topic:
            logger.warning(f"Consulta de {user.id} rechazada: '{found_forbidden_topic}'")
            error_message = (f"❌ Tu consulta sobre '{found_forbidden_topic}' no se procesa por aquí.\n\nConsulta info en grupo/docs. Si dudas específicas, replantea sin mencionar '{found_forbidden_topic}'.")
            try: await update.message.reply_text(error_message)
            except Exception as e_reply: logger.error(f"Error enviando msg rechazo a {user.id}: {e_reply}")
            # user_data ya se limpió con pop
            return ConversationHandler.END # Terminar aquí

    # Si NO fue rechazada por palabras clave, proceder a enviar
    if not found_forbidden_topic:
        target_chat_id = None
        if action_type == 'consulta': target_chat_id = GRUPO_EXTERNO_ID; target_thread_id = TEMA_CONSULTAS_EXTERNO
        elif action_type == 'sugerencia': target_chat_id = GRUPO_EXTERNO_ID; target_thread_id = TEMA_SUGERENCIAS_EXTERNO
        else:
             logger.error(f"Tipo acción '{action_type}' inesperado {user.id}");
             try: await update.message.reply_text("Error interno.");
             except Exception: pass
             # user_data ya se limpió con pop
             return ConversationHandler.END # Terminar por error

        if target_chat_id:
            user_info = f"{user.full_name}" + (f" (@{user.username})" if user.username else ""); forward_message = f"ℹ️ **Nueva {action_type.capitalize()} de {user_info}**:\n\n{user_text}"
            send_success = False
            try:
                await context.bot.send_message(chat_id=target_chat_id, message_thread_id=target_thread_id, text=forward_message, parse_mode=ParseMode.MARKDOWN);
                logger.info(f"{action_type.capitalize()} de {user_info} (ID:{user.id}) enviada a {target_chat_id}(T:{target_thread_id})");
                send_success = True
            except Exception as e:
                logger.error(f"Error enviando {action_type} de {user.id}: {e}", exc_info=True)

            if send_success:
                try: await update.message.reply_text(f"✅ ¡Tu {action_type} ha sido enviada!"); logger.info(f"Confirmación enviada a {user.id}")
                except Exception as e_confirm: logger.error(f"Error enviando confirmación a {user.id}: {e_confirm}")
            else:
                try: await update.message.reply_text(f"❌ Error al enviar tu {action_type}. Contacta admin.")
                except Exception as e_fail_confirm: logger.error(f"Error enviando msg fallo a {user.id}: {e_fail_confirm}")

            # user_data ya se limpió con pop
            return ConversationHandler.END # Terminar tras procesar (éxito o fallo)

    # Si llegamos aquí, fue una consulta rechazada (ya se envió el msg de error)
    # o un error interno manejado arriba. Asegurar que se retorna END.
    # user_data ya debería estar limpio por el pop inicial o en los bloques anteriores.
    logger.debug(f"receive_text alcanzando el final para {user.id} después de manejar {action_type}.")
    return ConversationHandler.END

# --- Handler para /cancel (Fallback de la Conversación) ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ Cancela la conversación activa. """
    user = update.effective_user; logger.info(f"Usuario {user.id} ({user.full_name}) canceló.")
    # action_type ya fue eliminado por pop en receive_text si se envió algo.
    # Aquí sólo necesitamos limpiar por si el usuario usa /cancel antes de enviar.
    # Si queremos dar un mensaje diferente si estaba en la conversación vs no:
    is_in_conversation = bool(context.user_data) # Comprobar si queda algo (aunque no debería ser action_type)
    context.user_data.clear() # Limpiar de todos modos
    if is_in_conversation: await update.message.reply_text('Operación cancelada.')
    else: await update.message.reply_text('No hay operación activa para cancelar.')
    return ConversationHandler.END

# --- Handler para Mensajes Inesperados en Privado ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Responde a mensajes de texto inesperados en privado. """
    user = update.effective_user; chat = update.effective_chat
    if not chat or chat.type != 'private' or not update.message or not update.message.text: return
    logger.info(f"Mensaje inesperado de {user.id} en privado: {update.message.text[:50]}...")
    if not GRUPO_ID or GRUPO_ID >= 0: logger.error("handle_unexpected_message: GRUPO_ID inválido."); await update.message.reply_text("Usa los botones del grupo."); return
    try:
        short_group_id = str(GRUPO_ID).replace("-100", "", 1); url_consultas = f"https://t.me/c/{short_group_id}/{TEMA_BOTON_CONSULTAS_COMITE}"; url_sugerencias = f"https://t.me/c/{short_group_id}/{TEMA_BOTON_SUGERENCIAS_COMITE}"
        texto = ("Hola 👋 Parece que has escrito directamente.\n\nPara enviar una consulta o sugerencia, usa los botones dedicados en los temas del grupo comité:"); keyboard = [[InlineKeyboardButton("Ir a Consultas 🤔", url=url_consultas)], [InlineKeyboardButton("Ir a Sugerencias ✨", url=url_sugerencias)]]; reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(texto, reply_markup=reply_markup)
    except Exception as e: logger.error(f"Error en handle_unexpected_message para {user.id}: {e}", exc_info=True); await update.message.reply_text("Usa los botones del grupo.")

# --- Configuración y Ejecución Principal ---
def main() -> None:
    """ Configura y ejecuta el bot. """
    if not validar_variables(): logger.critical("--- BOT DETENIDO: ERRORES CONFIG ---"); return
    application = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start, filters=filters.ChatType.PRIVATE)],
        states={ TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)] },
        fallbacks=[ CommandHandler('cancel', cancel, filters=filters.ChatType.PRIVATE), CommandHandler('start', start, filters=filters.ChatType.PRIVATE)],
        allow_reentry=True, per_user=True, per_chat=True,
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
