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

# --- Configuración de Logging, Estado, IDs y Variables Globales ---
# ... (igual que antes) ...
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

TYPING_REPLY = 0
TOKEN = None
GRUPO_ID = None
BOT_USERNAME = None
GROUP_LINK = None
TEMA_BOTON_CONSULTAS_COMITE = 272  # <- USA TU ID CORRECTO
TEMA_BOTON_SUGERENCIAS_COMITE = 291 # <- USA TU ID CORRECTO
TEMA_CONSULTAS_EXTERNO = 69
TEMA_SUGERENCIAS_EXTERNO = 71
GRUPO_EXTERNO_ID = -1002433074372

# --- Validación de Variables de Entorno (igual) ---
def validar_variables():
    # ... (igual que antes) ...
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
        if GROUP_LINK and not GROUP_LINK.startswith("https://t.me/"): logger.warning("GROUP_LINK inválido.")
        logger.info(f"GRUPO_ID (Comité): {GRUPO_ID}")
        logger.info(f"TEMA_BOTON_CONSULTAS_COMITE: {TEMA_BOTON_CONSULTAS_COMITE}")
        logger.info(f"TEMA_BOTON_SUGERENCIAS_COMITE: {TEMA_BOTON_SUGERENCIAS_COMITE}")
        logger.info(f"GRUPO_EXTERNO_ID: {GRUPO_EXTERNO_ID}")
        logger.info(f"TEMA_CONSULTAS_EXTERNO: {TEMA_CONSULTAS_EXTERNO}")
        logger.info(f"TEMA_SUGERENCIAS_EXTERNO: {TEMA_SUGERENCIAS_EXTERNO}")
        logger.info(f"BOT_USERNAME: @{BOT_USERNAME}")
        logger.info("✅ Variables validadas correctamente")
        return True
    except KeyError as e: logger.critical(f"❌ Falta var entorno: {e}"); return False
    except ValueError as e: logger.critical(f"❌ Error config: {e}"); return False
    except Exception as e: logger.critical(f"❌ Error config inesperado: {e}"); return False

# --- post_initial_buttons (Sin cambios) ---
async def post_initial_buttons(context: CallbackContext) -> bool:
    # ... (igual que antes, con textos largos) ...
    if not BOT_USERNAME: logger.error("BOT_USERNAME no config."); return False
    if not GRUPO_ID: logger.error("GRUPO_ID no config."); return False
    success = True
    mensaje_consulta = ("Pulsa el botón si tienes alguna consulta sobre algún tema que no se haya visto en el grupo(permisos, bolsa de horas, excedencias, etc...). Recuerda que estás consultas son privadas y solo pueden verlas los miembros del comité. La consulta debe ser enviada en un solo mensaje.")
    url_consulta = f"https://t.me/{BOT_USERNAME}?start=iniciar_consulta"
    kb_consulta = [[InlineKeyboardButton("Iniciar Consulta 🙋‍♂️", url=url_consulta)]]
    markup_consulta = InlineKeyboardMarkup(kb_consulta)
    try: await context.bot.send_message(chat_id=GRUPO_ID, message_thread_id=TEMA_BOTON_CONSULTAS_COMITE, text=mensaje_consulta, reply_markup=markup_consulta); logger.info(f"Msg botón 'Consulta' T:{TEMA_BOTON_CONSULTAS_COMITE}")
    except TelegramError as e: logger.error(f"Error enviando botón 'Consulta' T:{TEMA_BOTON_CONSULTAS_COMITE}: {e}"); success = False
    except Exception as e: logger.error(f"Error inesperado enviando botón 'Consulta': {e}", exc_info=True); success = False
    mensaje_sugerencia = ("Pulsa el botón si tienes alguna sugerencia para mejorar el grupo o el funcionamiento del comité. Recuerda que estás sugerencias son privadas y solo pueden verlas los miembros del comité. La sugerencia debe ser enviada en un solo mensaje.")
    url_sugerencia = f"https://t.me/{BOT_USERNAME}?start=iniciar_sugerencia"
    kb_sugerencia = [[InlineKeyboardButton("Iniciar Sugerencia 💡", url=url_sugerencia)]]
    markup_sugerencia = InlineKeyboardMarkup(kb_sugerencia)
    try: await context.bot.send_message(chat_id=GRUPO_ID, message_thread_id=TEMA_BOTON_SUGERENCIAS_COMITE, text=mensaje_sugerencia, reply_markup=markup_sugerencia); logger.info(f"Msg botón 'Sugerencia' T:{TEMA_BOTON_SUGERENCIAS_COMITE}")
    except TelegramError as e: logger.error(f"Error enviando botón 'Sugerencia' T:{TEMA_BOTON_SUGERENCIAS_COMITE}: {e}"); success = False
    except Exception as e: logger.error(f"Error inesperado enviando botón 'Sugerencia': {e}", exc_info=True); success = False
    return success

# --- post_buttons_command (Sin cambios) ---
async def post_buttons_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (igual que antes) ...
    user = update.effective_user; chat = update.effective_chat
    if not chat or chat.type != 'private': logger.warning(f"/postbotones ignorado: no en privado."); return
    logger.info(f"/postbotones recibido en privado de {user.id}. Ejecutando...")
    await update.message.reply_text("Recibido. Intentando publicar/actualizar botones...")
    try:
        success = await post_initial_buttons(context)
        if success: await update.message.reply_text("✅ ¡Hecho!")
        else: await update.message.reply_text("⚠️ Error al enviar uno o ambos. Revisa logs.")
    except Exception as e: logger.error(f"Error inesperado en post_initial_buttons por {user.id}: {e}", exc_info=True); await update.message.reply_text("❌ Error inesperado.")

# --- start (Sin cambios) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    # ... (igual que antes) ...
    user = update.effective_user; chat = update.effective_chat; args = context.args
    logger.info(f"Comando /start de {user.id} ({user.full_name}) chat {chat.id} ({chat.type}). Args: {args}")
    if chat.type == "private" and args:
        payload = args[0]; action_type = None
        if payload == "iniciar_consulta": action_type = "consulta"
        elif payload == "iniciar_sugerencia": action_type = "sugerencia"
        if action_type: logger.info(f"Payload '{payload}' de {user.id}. Iniciando {action_type}."); context.user_data['action_type'] = action_type; await update.message.reply_text(f"¡Hola {user.first_name}! Escribe tu {action_type}."); return TYPING_REPLY
        else: logger.warning(f"Payload desconocido '{payload}' de {user.id}."); await update.message.reply_text("Enlace inválido."); return ConversationHandler.END
    elif chat.type == "private": logger.info(f"/start simple de {user.id}."); await update.message.reply_text(f"¡Hola {user.first_name}! Usa los botones del grupo."); return ConversationHandler.END
    elif chat.type in ["group", "supergroup"]: logger.info(f"/start en grupo {chat.id}. Ignorando."); return None
    return ConversationHandler.END

# --- MODIFICADO: receive_text para añadir validación de palabras clave en consultas ---
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Recibe el texto en privado. Si es consulta, valida palabras clave.
    Si es válido (o es sugerencia), lo envía al grupo/tema externo apropiado.
    Confirma en privado.
    """
    user = update.effective_user
    user_text = update.message.text
    action_type = context.user_data.get('action_type')

    if not action_type:
        logger.warning(f"receive_text llamado sin action_type en user_data para {user.id}.")
        await update.message.reply_text("Error interno. Empieza de nuevo.")
        return ConversationHandler.END

    logger.info(f"Texto recibido de {user.id} para '{action_type}': {user_text[:50]}...")

    # --- INICIO: Validación de Palabras Clave (SOLO para consultas) ---
    if action_type == 'consulta':
        text_lower = user_text.lower() # Convertir a minúsculas una vez

        # Diccionario: clave = palabra/frase a buscar (en minúsculas), valor = nombre del tema para el mensaje de error
        forbidden_keywords_map = {
            "bolsa de horas": "bolsa de horas",
            "permiso": "permisos",
            "permisos": "permisos",
            "incapacidad temporal": "incapacidad temporal",
            "baja": "incapacidad temporal", # Mapear "baja" al mismo tema
            "excedencia": "excedencias",
            "excedencias": "excedencias"
        }

        found_forbidden_topic = None
        for keyword, topic_name in forbidden_keywords_map.items():
            # Usar find() puede ser un poco más robusto que 'in' para evitar subcadenas no deseadas
            # Pero 'in' es más simple para este caso. Si necesitas más precisión, considera regex.
            if keyword in text_lower:
                found_forbidden_topic = topic_name
                break # Salir del bucle al encontrar la primera coincidencia

        if found_forbidden_topic:
            logger.warning(f"Consulta de {user.id} rechazada por palabra clave relacionada a: '{found_forbidden_topic}'")
            error_message = (
                f"❌ Tu consulta relacionada con '{found_forbidden_topic}' no puede ser enviada por este medio.\n\n"
                f"Este tipo de consultas ya están resueltas en la sección '{found_forbidden_topic}' del grupo o en la documentación general. "
                f"Por favor, revisa la información disponible allí antes de enviar una nueva consulta."
            )
            await update.message.reply_text(error_message)
            context.user_data.clear() # Limpiar datos
            return ConversationHandler.END # Terminar la conversación
    # --- FIN: Validación de Palabras Clave ---

    # Si la validación pasa (o no es una consulta), continuar...

    # Determinar destino EXTERNO
    if action_type == 'consulta':
        # Ya sabemos que es consulta y pasó el filtro
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_CONSULTAS_EXTERNO
    elif action_type == 'sugerencia':
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_SUGERENCIAS_EXTERNO
    else:
        # Este caso no debería ocurrir si action_type está validado al principio
        logger.error(f"Tipo de acción desconocido '{action_type}' después de validación? {user.id}")
        await update.message.reply_text("Error interno inesperado.")
        context.user_data.clear()
        return ConversationHandler.END

    # Formatear mensaje para el grupo externo (sin ID)
    user_info = f"{user.full_name}" + (f" (@{user.username})" if user.username else "")
    forward_message = f"ℹ️ **Nueva {action_type.capitalize()} de {user_info}**:\n\n" \
                      f"{user_text}"

    try:
        # Enviar al grupo/tema EXTERNO
        await context.bot.send_message(
            chat_id=target_chat_id,
            message_thread_id=target_thread_id,
            text=forward_message,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"{action_type.capitalize()} de {user_info} (ID: {user.id}) enviada a {target_chat_id} (T:{target_thread_id})")
        # Confirmar al usuario EN PRIVADO
        await update.message.reply_text(f"✅ ¡Tu {action_type} ha sido enviada correctamente!")
        logger.info(f"Confirmación enviada en privado a {user.id}")

    except Exception as e:
        logger.error(f"Error enviando la {action_type} de {user.id} al grupo externo: {e}")
        await update.message.reply_text(f"❌ Hubo un error al enviar tu {action_type}. Por favor, contacta a un administrador.")

    finally:
        # Limpiar datos y terminar conversación
        context.user_data.clear()
        return ConversationHandler.END

# --- cancel (Sin cambios) ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (igual que antes) ...
    user = update.effective_user; logger.info(f"User {user.id} canceló."); await update.message.reply_text('Cancelado.'); context.user_data.clear(); return ConversationHandler.END

# --- handle_unexpected_message (Sin cambios) ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (igual que antes) ...
    user = update.effective_user; chat = update.effective_chat
    logger.info(f"Mensaje inesperado de {user.id} en privado: {update.message.text[:50]}...")
    if not GRUPO_ID or GRUPO_ID >= 0: logger.error("GRUPO_ID inválido para enlaces tema."); await update.message.reply_text("Usa botones del grupo comité."); return
    try:
        short_group_id = str(GRUPO_ID).replace("-100", "", 1)
        url_consultas = f"https://t.me/c/{short_group_id}/{TEMA_BOTON_CONSULTAS_COMITE}"
        url_sugerencias = f"https://t.me/c/{short_group_id}/{TEMA_BOTON_SUGERENCIAS_COMITE}"
        texto = ("Hola 👋 Parece que has escrito directamente.\n\nPara enviar una consulta o sugerencia, usa los botones en los temas del grupo comité:")
        keyboard = [[InlineKeyboardButton("Ir a Consultas 🤔", url=url_consultas)], [InlineKeyboardButton("Ir a Sugerencias ✨", url=url_sugerencias)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(texto, reply_markup=reply_markup)
    except Exception as e: logger.error(f"Error gen respuesta inesperada {user.id}: {e}", exc_info=True); await update.message.reply_text("Usa botones del grupo comité.")


# --- Configuración y Ejecución (Sin cambios) ---
def main() -> None:
    """Inicia el bot."""
    # ... (igual que antes) ...
    if not validar_variables(): logger.critical("Deteniendo bot por errores config."); return
    application = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(entry_points=[CommandHandler('start', start, filters=filters.ChatType.PRIVATE)], states={TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)]}, fallbacks=[CommandHandler('cancel', cancel, filters=filters.ChatType.PRIVATE), CommandHandler('start', start, filters=filters.ChatType.PRIVATE)], per_user=True, per_chat=True,)
    application.add_handler(conv_handler, group=0)
    application.add_handler(CommandHandler("postbotones", post_buttons_command, filters=filters.ChatType.PRIVATE), group=1)
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_unexpected_message), group=2)
    application.add_handler(CommandHandler("start", start), group=1)
    logger.info("Iniciando polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot detenido.")

if __name__ == '__main__':
    main()
