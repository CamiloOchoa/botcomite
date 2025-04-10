# -*- coding: utf-8 -*-
import os
import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode, ChatAction
from telegram.error import TelegramError

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
# Silenciar logs de httpx que pueden ser muy verbosos
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Estado para la Conversación ---
TYPING_REPLY = 0

# --- Variables Globales ---
TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
GRUPO_ID = int(os.environ.get("GROUP_ID", "0")) # Grupo del Comité (interno)
TEMA_ID_PANEL_CONSULTAS = int(os.environ.get("TEMA_BOTON_CONSULTAS_COMITE", "0")) # Tema para el *panel* de consultas
TEMA_ID_PANEL_SUGERENCIAS = int(os.environ.get("TEMA_BOTON_SUGERENCIAS_COMITE", "0")) # Tema para el *panel* de sugerencias
GRUPO_EXTERNO_ID = int(os.environ.get("GRUPO_EXTERNO_ID", "0")) # Grupo EXTERNO para recibir mensajes
TEMA_ID_CONSULTAS_EXTERNO = int(os.environ.get("TEMA_CONSULTAS_EXTERNO", "0")) # Tema para *recibir* consultas
TEMA_ID_SUGERENCIAS_EXTERNO = int(os.environ.get("TEMA_SUGERENCIAS_EXTERNO", "0")) # Tema para *recibir* sugerencias
TEMA_ID_DOCUMENTACION = int(os.environ.get("TEMA_DOCUMENTACION", "0")) # Tema de Documentación (interno)
MIN_MSG_LENGTH = 15 # Longitud mínima del mensaje

# --- Validación de Variables ---
def validar_variables():
    valid = True
    if not TOKEN:
        logger.critical("❌ TELEGRAM_TOKEN no está configurada.")
        valid = False
    if GRUPO_ID >= 0 or GRUPO_ID == 0:
        logger.error(f"❌ GROUP_ID ({GRUPO_ID}) debe ser un ID de grupo válido (negativo).")
        valid = False
    if GRUPO_EXTERNO_ID >= 0 or GRUPO_EXTERNO_ID == 0:
        logger.error(f"❌ GRUPO_EXTERNO_ID ({GRUPO_EXTERNO_ID}) debe ser un ID de grupo válido (negativo).")
        valid = False
    if TEMA_ID_PANEL_CONSULTAS <= 0:
         logger.error(f"❌ TEMA_BOTON_CONSULTAS_COMITE ({TEMA_ID_PANEL_CONSULTAS}) debe ser un ID de tema válido (positivo).")
         valid = False
    if TEMA_ID_PANEL_SUGERENCIAS <= 0:
         logger.error(f"❌ TEMA_BOTON_SUGERENCIAS_COMITE ({TEMA_ID_PANEL_SUGERENCIAS}) debe ser un ID de tema válido (positivo).")
         valid = False
    if TEMA_ID_CONSULTAS_EXTERNO <= 0:
         logger.error(f"❌ TEMA_CONSULTAS_EXTERNO ({TEMA_ID_CONSULTAS_EXTERNO}) debe ser un ID de tema válido (positivo).")
         valid = False
    if TEMA_ID_SUGERENCIAS_EXTERNO <= 0:
         logger.error(f"❌ TEMA_SUGERENCIAS_EXTERNO ({TEMA_ID_SUGERENCIAS_EXTERNO}) debe ser un ID de tema válido (positivo).")
         valid = False
    if TEMA_ID_DOCUMENTACION <= 0:
         logger.error(f"❌ TEMA_DOCUMENTACION ({TEMA_ID_DOCUMENTACION}) debe ser un ID de tema válido (positivo).")
         valid = False

    if valid:
        logger.info("✅ Variables de entorno validadas correctamente")
    else:
        logger.critical("❌ Errores críticos encontrados en las variables de entorno.")
    return valid

# --- Función para enviar/actualizar los paneles de acción en el grupo interno ---
async def post_action_panels(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Envía o actualiza los mensajes con botones de acción en los temas designados."""
    success_count = 0
    # Panel de Consultas
    text_consultas = (
        "Pulsa aquí si tienes alguna consulta sobre permisos, bolsa de horas, excedencias, etc.\n"
        "Tu mensaje será privado y solo se permite enviar uno por vez."
    )
    kb_consultas = [[InlineKeyboardButton("Iniciar Consulta 🙋‍♂️", callback_data="iniciar_consulta")]]
    markup_consultas = InlineKeyboardMarkup(kb_consultas)
    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_ID_PANEL_CONSULTAS,
            text=text_consultas,
            reply_markup=markup_consultas
        )
        logger.info(f"Panel de Consulta enviado/actualizado en G:{GRUPO_ID}, T:{TEMA_ID_PANEL_CONSULTAS}")
        success_count += 1
    except TelegramError as e:
        logger.error(f"Error enviando Panel Consulta a T:{TEMA_ID_PANEL_CONSULTAS}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Excepción inesperada enviando Panel Consulta: {e}", exc_info=True)

    # Panel de Sugerencias
    text_sugerencias = (
        "Pulsa aquí si tienes alguna sugerencia sobre el funcionamiento del grupo o el comité.\n"
        "Tu mensaje será privado y solo se permite enviar uno por vez."
    )
    kb_sugerencias = [[InlineKeyboardButton("Iniciar Sugerencia 💡", callback_data="iniciar_sugerencia")]]
    markup_sugerencias = InlineKeyboardMarkup(kb_sugerencias)
    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_ID_PANEL_SUGERENCIAS,
            text=text_sugerencias,
            reply_markup=markup_sugerencias
        )
        logger.info(f"Panel de Sugerencia enviado/actualizado en G:{GRUPO_ID}, T:{TEMA_ID_PANEL_SUGERENCIAS}")
        success_count += 1
    except TelegramError as e:
        logger.error(f"Error enviando Panel Sugerencia a T:{TEMA_ID_PANEL_SUGERENCIAS}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Excepción inesperada enviando Panel Sugerencia: {e}", exc_info=True)

    return success_count > 0

# --- Comando para que un admin postee/actualice los paneles ---
async def post_panels_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando para (re)postear los paneles de consulta y sugerencia."""
    if update.effective_chat.type != 'private':
        await update.message.reply_text("Este comando solo se puede usar en chat privado.")
        return

    logger.info(f"/postpaneles recibido de {update.effective_user.id}.")
    await update.message.reply_text("Intentando publicar/actualizar paneles en el grupo del Comité...")
    try:
        success = await post_action_panels(context)
    except Exception as e:
        logger.error(f"Excepción en post_action_panels: {e}", exc_info=True)
        await update.message.reply_text("❌ Ocurrió un error al intentar postear los paneles.")
        return
    if success:
        await update.message.reply_text("✅ ¡Paneles posteados/actualizados con éxito!")
    else:
        await update.message.reply_text("⚠️ No se pudieron enviar uno o ambos paneles. Revisa los logs.")

# --- Comando para postear/actualizar el panel de Documentación ---
async def documentacion_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía el mensaje con enlaces a la documentación al tema correspondiente."""
    if update.effective_chat.type != 'private':
        await update.message.reply_text("Este comando solo se puede usar en chat privado.")
        return

    logger.info(f"/documentacion recibido de {update.effective_user.id}.")
    await update.message.reply_text("Intentando publicar/actualizar panel de documentación...")

    keyboard = [
        [InlineKeyboardButton("Calendario laboral", url="https://drive.google.com/file/d/1fnQ20Ez9lYMqzObNWMd-XZt5RVj9JBZX/view?usp=drive_link")],
        [InlineKeyboardButton("Tablas salariales 2025", url="https://drive.google.com/file/d/1653DgFn7B2mGqI-liaVcpYNuM4-8iTWC/view?usp=drive_link")],
        [InlineKeyboardButton("Convenio", url="https://drive.google.com/file/d/10LWmAFuKUtj6tX5A0RWMA1GF5KCw4s0z/view?usp=drive_link")],
        [InlineKeyboardButton("Estatuto de los trabajadores", url="https://drive.google.com/file/d/1WtVo-dr4Bb1Qp-qA53iiWfIzxHPwA8fG/view?usp=drive_link")],
        [InlineKeyboardButton("Protocolo de desconexión digital", url="https://drive.google.com/file/d/1zYWlATSrTfBH8izmGS9TePL8gp99P3fz/view?usp=drive_link")],
        [InlineKeyboardButton("Protocolo LGTBI", url="https://drive.google.com/file/d/1LmrGtb7Sic-wN4Bstz2gRegeD0ljMT02/view?usp=drive_link")],
        [InlineKeyboardButton("Protocolo de acoso", url="https://drive.google.com/file/d/1JBrCyBXel-0JxCwhamv2L2zLzPgsDMyT/view?usp=drive_link")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_ID_DOCUMENTACION,
            text="📄 *Documentación disponible:*",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"Mensaje de Documentación enviado a G:{GRUPO_ID}, T:{TEMA_ID_DOCUMENTACION}")
        await update.message.reply_text("✅ Panel de documentación posteado/actualizado.")
    except TelegramError as e:
        logger.error(f"Error de Telegram API enviando Documentación a T:{TEMA_ID_DOCUMENTACION}: {e}")
        await update.message.reply_text(f"❌ Error de Telegram al enviar documentación: {e.message}")
    except Exception as e:
        logger.error(f"Excepción inesperada enviando Documentación: {e}", exc_info=True)
        await update.message.reply_text("❌ Ocurrió un error inesperado al enviar la documentación.")

# --- Callback Handler para iniciar el flujo en privado (desde botones del grupo) ---
async def callback_iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manejador para los botones 'iniciar_consulta' e 'iniciar_sugerencia'."""
    query = update.callback_query
    user = query.from_user
    data = query.data

    await query.answer()
    context.user_data.clear()
    logger.debug(f"User {user.id} started conversation via callback '{data}'. Cleared user_data.")

    try:
        action_text = ""
        if data == "iniciar_consulta":
            context.user_data['action_type'] = "consulta"
            action_text = "consulta"
            prompt = (
                "Hola 👋 Por favor, escribe ahora tu *consulta* en un único mensaje.\n\n"
                "Recibirás una respuesta tan pronto como sea posible.\n"
                "_Recuerda que solo los miembros del comité verán tu mensaje._"
            )
        elif data == "iniciar_sugerencia":
            context.user_data['action_type'] = "sugerencia"
            action_text = "sugerencia"
            prompt = (
                "Hola 👋 Por favor, escribe ahora tu *sugerencia* en un único mensaje.\n\n"
                "_Recuerda que solo los miembros del comité verán tu mensaje._"
            )
        else:
            logger.warning(f"CallbackQuery con data inesperado recibido de user {user.id}: {data}")
            await context.bot.send_message(chat_id=user.id, text="Acción no reconocida.")
            return ConversationHandler.END

        await context.bot.send_message(chat_id=user.id, text=prompt, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Prompt for '{action_text}' sent to user {user.id}. Entering TYPING_REPLY state.")
        # Log user_data justo después de establecerlo
        logger.debug(f"User {user.id} user_data after setting action_type: {context.user_data}")
        return TYPING_REPLY

    except TelegramError as e:
        if "bot can't initiate conversation with a user" in str(e) or "chat not found" in str(e):
            logger.info(f"User {user.id} ({user.full_name}) attempted action '{data}' without starting bot.")
            await query.answer(
                text=f"⚠️ Necesitas iniciar el chat conmigo (@{context.bot.username}) y pulsar 'Iniciar', luego vuelve a pulsar el botón.",
                show_alert=True
            )
        else:
            logger.error(f"TelegramError initiating conversation with {user.id} for action '{data}': {e}", exc_info=True)
            await query.answer("❌ Ocurrió un error técnico al iniciar.", show_alert=True)
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Unexpected exception in callback_iniciar for user {user.id}, data '{data}': {e}", exc_info=True)
        await query.answer("❌ Ocurrió un error inesperado.", show_alert=True)
        context.user_data.clear()
        return ConversationHandler.END

# --- Handler para /start (flujo de conversación y deep linking) ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manejador para el comando /start, puede incluir payload de deep linking."""
    user = update.effective_user
    chat = update.effective_chat
    args = context.args

    if chat.type != 'private':
        return ConversationHandler.END

    logger.info(f"/start received from {user.id} ({user.full_name}) with args: {args}")
    # Log si había datos previos antes de limpiar
    if context.user_data:
        logger.debug(f"Clearing existing user_data for {user.id} on /start: {context.user_data}")
    context.user_data.clear()

    if args:
        payload = args[0]
        if payload == "iniciar_consulta":
            context.user_data['action_type'] = "consulta"
            prompt = (
                "Hola de nuevo 👋 Parece que hiciste clic en un enlace para iniciar una consulta.\n\n"
                "Por favor, escribe ahora tu *consulta* en un único mensaje.\n"
                "_Solo los miembros del comité verán tu mensaje._"
            )
            await update.message.reply_text(prompt, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Deep link '/start iniciar_consulta' processed for {user.id}. Entering TYPING_REPLY.")
            logger.debug(f"User {user.id} user_data after deep link start: {context.user_data}")
            return TYPING_REPLY
        elif payload == "iniciar_sugerencia":
            context.user_data['action_type'] = "sugerencia"
            prompt = (
                "Hola de nuevo 👋 Parece que hiciste clic en un enlace para iniciar una sugerencia.\n\n"
                "Por favor, escribe ahora tu *sugerencia* en un único mensaje.\n"
                "_Solo los miembros del comité verán tu mensaje._"
            )
            await update.message.reply_text(prompt, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Deep link '/start iniciar_sugerencia' processed for {user.id}. Entering TYPING_REPLY.")
            logger.debug(f"User {user.id} user_data after deep link start: {context.user_data}")
            return TYPING_REPLY
        else:
            await update.message.reply_text(
                "Hola 👋. El enlace que has usado no es válido o ha expirado.\n"
                "Si quieres enviar una consulta o sugerencia, por favor, usa los botones correspondientes en el grupo del Comité."
            )
            logger.warning(f"Invalid deep link payload '{payload}' received from user {user.id}.")
            return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Hola 👋 Soy el bot asistente del Comité.\n"
            "Para enviar una *consulta* o *sugerencia* de forma privada, por favor, utiliza los botones 🙋‍♂️ o 💡 en los temas correspondientes del grupo del Comité."
            , parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"Standard /start processed for user {user.id}.")
        return ConversationHandler.END

# --- Handler para recibir el texto del usuario (dentro de la conversación) ---
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el mensaje de consulta/sugerencia del usuario y lo reenvía."""
    user = update.effective_user
    message = update.message

    # === LOGGING ADICIONAL INICIO ===
    logger.info(f"Received message from user {user.id} in potentially TYPING_REPLY state.")
    logger.debug(f"Current user_data for {user.id} upon receiving message: {context.user_data}")
    # === LOGGING ADICIONAL FIN ===

    if not message or not message.text:
        logger.warning(f"Empty or non-text message received from {user.id} in TYPING_REPLY state.")
        # No enviar respuesta aquí, podría ser confuso si el estado realmente se perdió
        context.user_data.clear()
        return ConversationHandler.END # Salir silenciosamente si no hay texto

    user_text = message.text.strip()
    # Usamos .get() para evitar KeyError si user_data está vacío por alguna razón
    action_type = context.user_data.get('action_type')

    if not action_type:
        logger.warning(f"receive_text called for {user.id} but 'action_type' is missing in user_data. Message: '{user_text[:50]}...'")
        # Llamar a handle_unexpected_message SIEMPRE que no haya action_type
        await handle_unexpected_message(update, context, called_from_receive_text=True)
        context.user_data.clear() # Asegurarse de limpiar
        return ConversationHandler.END

    # --- Comprobación de longitud ---
    if len(user_text) < MIN_MSG_LENGTH:
        logger.info(f"{action_type.capitalize()} from {user.id} is too short ({len(user_text)} chars). Replying and ending conversation.")
        error_text = (
            f"⚠️ Tu {action_type} parece demasiado corta (mínimo {MIN_MSG_LENGTH} caracteres).\n"
            f"El mensaje *no* ha sido enviado.\n\n"
            f"Si fue un error, por favor, inicia el proceso de nuevo desde el botón en el grupo del Comité."
        )
        try:
            await update.message.reply_text(error_text, parse_mode=ParseMode.MARKDOWN)
        except TelegramError as reply_err:
            logger.error(f"Failed to send 'too short' message to user {user.id}: {reply_err}")

        context.user_data.clear()
        return ConversationHandler.END

    # --- Preparación para enviar al grupo externo ---
    logger.info(f"Message from {user.id} passed length check for {action_type}. Preparing to forward.")

    target_chat_id = GRUPO_EXTERNO_ID
    if action_type == "consulta":
        target_thread_id = TEMA_ID_CONSULTAS_EXTERNO
        action_emoji = "🙋‍♂️"
    elif action_type == "sugerencia":
        target_thread_id = TEMA_ID_SUGERENCIAS_EXTERNO
        action_emoji = "💡"
    else:
        logger.error(f"Internal logic error: Unknown action_type '{action_type}' in receive_text for user {user.id}.")
        try:
            await update.message.reply_text("❌ Hubo un error interno inesperado (código: RT_UNK_AT). Por favor, contacta a un administrador.")
        except TelegramError as reply_err:
            logger.error(f"Failed to send internal error message to user {user.id}: {reply_err}")
        context.user_data.clear()
        return ConversationHandler.END

    # Construir mensaje a reenviar
    user_mention = user.mention_markdown_v2() if user.username else user.full_name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
    fwd_msg_header = f"{action_emoji} *Nueva {action_type.capitalize()} de {user_mention}* `(ID: {user.id})`:\n{'-'*20}\n"
    escaped_body = user_text.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
    fwd_msg = fwd_msg_header + escaped_body

    # === LOGGING ANTES DE ENVIAR ===
    logger.info(f"Attempting to send {action_type} from user {user.id} to external group.")
    logger.debug(f"Target Chat ID: {target_chat_id}")
    logger.debug(f"Target Thread ID: {target_thread_id}")
    # No loguear fwd_msg completo por privacidad, solo confirmar que se va a enviar
    logger.debug(f"Parse Mode: {ParseMode.MARKDOWN_V2}")
    # === FIN LOGGING ANTES DE ENVIAR ===

    message_sent_to_group = False
    try:
        # Enviar mensaje al grupo/tema externo
        await context.bot.send_message(
            chat_id=target_chat_id,
            message_thread_id=target_thread_id,
            text=fwd_msg,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        message_sent_to_group = True
        logger.info(f"✅ Successfully sent {action_type} from {user.id} to G:{target_chat_id} T:{target_thread_id}.")
        # Confirmar al usuario SOLO si el envío fue exitoso
        await update.message.reply_text(f"✅ ¡Tu {action_type} ha sido enviada correctamente! Gracias por tu aportación.")

    except TelegramError as e:
        # === LOGGING DETALLADO DE TelegramError ===
        logger.error(f"TelegramError sending {action_type} from {user.id} to G:{target_chat_id} T:{target_thread_id}. Error: {e}", exc_info=True)
        # === FIN LOGGING DETALLADO ===
        try:
            # Informar al usuario del fallo técnico
            await update.message.reply_text(f"❌ Hubo un problema técnico al enviar tu {action_type} (Error: TG-{e.__class__.__name__}). Por favor, inténtalo de nuevo más tarde o contacta a un administrador si el problema persiste.")
        except TelegramError as reply_err:
            logger.error(f"Failed to send TelegramError feedback message to user {user.id}: {reply_err}")

    except Exception as e:
        # === LOGGING DETALLADO DE Exception ===
        logger.error(f"Unexpected Exception sending {action_type} from {user.id} to G:{target_chat_id} T:{target_thread_id}. Error: {e}", exc_info=True)
        # === FIN LOGGING DETALLADO ===
        try:
             # Informar al usuario del fallo inesperado
            await update.message.reply_text(f"❌ Ocurrió un error inesperado al procesar tu {action_type} (Error: EXC-{e.__class__.__name__}). Por favor, contacta a un administrador.")
        except TelegramError as reply_err:
             logger.error(f"Failed to send Exception feedback message to user {user.id}: {reply_err}")

    # Limpiar y finalizar la conversación, independientemente del resultado del envío al grupo
    logger.debug(f"Clearing user_data for {user.id} after processing {action_type} (sent to group: {message_sent_to_group}). Ending conversation.")
    context.user_data.clear()
    return ConversationHandler.END

# --- Handler para mensajes fuera de flujo (en chat privado) ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE, called_from_receive_text: bool = False) -> None:
    """Maneja mensajes de texto enviados al bot en privado fuera de una conversación activa."""
    user = update.effective_user
    chat = update.effective_chat

    # Asegurarse que es un chat privado y no un comando
    if not chat or chat.type != 'private' or not update.message or not update.message.text or update.message.text.startswith('/'):
        # Ignorar otros casos (ej. comandos ya manejados, mensajes en grupos)
        # No loguear aquí para evitar ruido si es un comando válido procesado por otro handler
        return

    # Log específico para mensajes inesperados
    # Si viene de receive_text, el log ya se hizo allí
    if not called_from_receive_text:
        logger.info(f"Unexpected text message received from {user.id} in private chat (not in active conversation): '{update.message.text[:50]}...'")

    try:
        await update.message.reply_text(
            "Hola 👋 Recibí tu mensaje, pero no estoy esperando una consulta o sugerencia en este momento.\n\n"
            "Si quieres enviar una, por favor, ve al grupo del Comité y utiliza los botones 🙋‍♂️ (Consulta) o 💡 (Sugerencia) en los temas correspondientes.\n\n"
            "También puedes usar /start para ver las opciones o /cancel si crees que estás en medio de una acción."
            , parse_mode=ParseMode.MARKDOWN
        )
    except TelegramError as e:
        logger.error(f"Failed to send unexpected message response to user {user.id}: {e}")


# --- Comando para cancelar la conversación actual ---
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Permite al usuario cancelar la operación actual (consulta/sugerencia)."""
    user = update.effective_user
    chat = update.effective_chat

    if not chat or chat.type != 'private':
         # Ignorar /cancel en grupos
         return ConversationHandler.END # O simplemente no retornar nada

    logger.info(f"User {user.id} ({user.full_name}) executed /cancel.")
    if not context.user_data:
         await update.message.reply_text("No hay ninguna operación activa que cancelar.")
         # Asegurarse que si había un estado de conversación, termine
         return ConversationHandler.END

    # Si había datos, limpiarlos
    logger.debug(f"Cancelling conversation for user {user.id}. Previous user_data: {context.user_data}")
    context.user_data.clear()
    await update.message.reply_text("Operación cancelada. Puedes empezar de nuevo cuando quieras usando los botones del grupo.")
    return ConversationHandler.END

# --- Función Principal ---
def main() -> None:
    """Inicia el bot."""
    if not validar_variables():
        logger.critical("--- BOT DETENIDO: Errores críticos en la configuración ---")
        return

    # Configura la aplicación del bot
    # Considera añadir persistencia si los reinicios son frecuentes
    # from telegram.ext import DictPersistence
    # persistence = DictPersistence(filepath='bot_persistence') # O PicklePersistence
    # application = ApplicationBuilder().token(TOKEN).persistence(persistence).build()
    application = ApplicationBuilder().token(TOKEN).build()


    # --- Define el manejador de conversación ---
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(callback_iniciar, pattern="^iniciar_(consulta|sugerencia)$"),
            CommandHandler('start', start_handler, filters=filters.ChatType.PRIVATE)
        ],
        states={
            TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_command, filters=filters.ChatType.PRIVATE),
            CommandHandler('start', start_handler, filters=filters.ChatType.PRIVATE), # Reinicia con /start
             # Captura cualquier otro comando inesperado durante la conversación
             MessageHandler(filters.COMMAND & filters.ChatType.PRIVATE, cancel_command) # Forzar cancelación si envían otro comando
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
        name="consulta_sugerencia_conv",
        # persistent=True # Necesitaría configurar persistence en ApplicationBuilder
    )

    # --- Añade los Handlers a la aplicación ---
    application.add_handler(conv_handler, group=0) # Dar prioridad al ConversationHandler

    # Comandos de administración (ejecutables en privado)
    application.add_handler(CommandHandler("postpaneles", post_panels_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("documentacion", documentacion_command, filters=filters.ChatType.PRIVATE))

    # Manejador para mensajes de texto inesperados (fuera de conversación, en privado)
    # Se ejecuta si conv_handler no está activo o el mensaje no coincide con sus estados/filtros
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_unexpected_message), group=1)

    # --- Inicia el Bot ---
    logger.info("--- Iniciando Polling del Bot ---")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"--- ERROR CRÍTICO DURANTE EL POLLING ---: {e}", exc_info=True)
    finally:
        logger.info("--- Bot Detenido ---")

if __name__ == '__main__':
    # Establecer nivel de log DEBUG para pruebas locales si es necesario
    # logging.getLogger().setLevel(logging.DEBUG)
    # logging.getLogger("__main__").setLevel(logging.DEBUG)
    main()
