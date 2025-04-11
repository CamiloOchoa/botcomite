# -*- coding: utf-8 -*-
import os
import logging
import pickle # Aún necesario si PicklePersistence estuviera activo
from pathlib import Path # Aún necesario si PicklePersistence estuviera activo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
    PicklePersistence, # Importado pero no usado en esta config
    DictPersistence   # Importar DictPersistence
)
from telegram.constants import ParseMode, ChatAction
from telegram.error import TelegramError

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO # Nivel INFO por defecto
)
# Habilitar DEBUG para módulos específicos
logging.getLogger("telegram.ext.Persistence").setLevel(logging.DEBUG)
logging.getLogger("telegram.ext.ConversationHandler").setLevel(logging.DEBUG)
# Silenciar httpx si es muy ruidoso
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# --- Estado para la Conversación ---
TYPING_REPLY = 0

# --- Variables Globales ---
TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
GRUPO_ID = int(os.environ.get("GROUP_ID", "0"))
TEMA_ID_PANEL_CONSULTAS = int(os.environ.get("TEMA_BOTON_CONSULTAS_COMITE", "0"))
TEMA_ID_PANEL_SUGERENCIAS = int(os.environ.get("TEMA_BOTON_SUGERENCIAS_COMITE", "0"))
GRUPO_EXTERNO_ID = int(os.environ.get("GRUPO_EXTERNO_ID", "0"))
TEMA_ID_CONSULTAS_EXTERNO = int(os.environ.get("TEMA_CONSULTAS_EXTERNO", "0"))
TEMA_ID_SUGERENCIAS_EXTERNO = int(os.environ.get("TEMA_SUGERENCIAS_EXTERNO", "0"))
TEMA_ID_DOCUMENTACION = int(os.environ.get("TEMA_DOCUMENTACION", "0"))
MIN_MSG_LENGTH = 15 # No se usa en modo diagnóstico
PERSISTENCE_FILE = "bot_persistence.pkl" # No se usa con DictPersistence

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

# --- Funciones de Comandos (sin cambios) ---
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


# --- Handlers de Conversación (sin cambios en lógica interna, pero con logging) ---
async def callback_iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manejador para los botones 'iniciar_consulta' e 'iniciar_sugerencia'."""
    query = update.callback_query
    user = query.from_user
    data = query.data

    context.user_data.clear()
    await query.answer()
    logger.debug(f"User {user.id} started conversation via callback '{data}'. Cleared user_data first.")

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
            context.user_data.clear()
            return ConversationHandler.END

        await context.bot.send_message(chat_id=user.id, text=prompt, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Prompt for '{action_text}' sent to user {user.id}. Entering TYPING_REPLY state.")
        logger.debug(f"User {user.id} user_data set to: {context.user_data}. State should be saved by persistence.")
        # Forzar guardado inmediato de persistencia (puede no ser necesario con DictPersistence)
        if context.application.persistence:
             await context.application.update_persistence()
             logger.debug("Forced persistence update after setting user_data in callback_iniciar.")

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

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manejador para el comando /start, puede incluir payload de deep linking."""
    user = update.effective_user
    chat = update.effective_chat
    args = context.args

    if chat.type != 'private':
        return ConversationHandler.END

    logger.info(f"/start received from {user.id} ({user.full_name}) with args: {args}")
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
            logger.debug(f"User {user.id} user_data set to: {context.user_data}. State should be saved.")
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
            logger.debug(f"User {user.id} user_data set to: {context.user_data}. State should be saved.")
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

# --- Handler de Diagnóstico para TYPING_REPLY (con verificación de persistencia) ---
async def diagnostic_receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler de diagnóstico para el estado TYPING_REPLY."""
    user = update.effective_user
    chat = update.effective_chat
    message_text = update.message.text if update.message else "N/A"
    conv_handler_name = "consulta_sugerencia_conv" # Nombre que le dimos al handler

    # LOG CRÍTICO: Verificar user_data y datos de conversación INMEDIATAMENTE
    logger.info(f"DIAGNOSTIC HANDLER: Message received from user {user.id} / chat {chat.id}.")

    # Obtener datos directamente de la persistencia si está disponible
    conversation_key = (chat.id, user.id)
    persisted_state = None
    persisted_user_data_snapshot = None # Snapshot de user_data de persistencia
    raw_conv_state = None # Estado directo de la conversación persistida

    if context.application.persistence:
        logger.debug(f"Attempting to fetch persisted data for key: {conversation_key}")
        # Obtener el estado directamente
        all_conv_data = await context.application.persistence.get_conversations(conv_handler_name)
        raw_conv_state = all_conv_data.get(conversation_key) # Esto debería ser TYPING_REPLY (0)
        # Obtener user_data de la persistencia
        all_user_data = await context.application.persistence.get_user_data()
        persisted_user_data_snapshot = all_user_data.get(user.id, {}).copy() # Copiar para evitar modificar

        logger.info(f"DIAGNOSTIC HANDLER: Raw persisted state for key {conversation_key}: {raw_conv_state}")
        logger.info(f"DIAGNOSTIC HANDLER: Snapshot of persisted User Data for user {user.id}: {persisted_user_data_snapshot}")
    else:
        logger.warning("DIAGNOSTIC HANDLER: Persistence is not configured/available.")

    # Verificar context.user_data que la biblioteca proporciona al handler
    logger.info(f"DIAGNOSTIC HANDLER: context.user_data available in handler: {context.user_data}")
    action_type = context.user_data.get('action_type')

    reply_message = ""
    if action_type:
        logger.info(f"DIAGNOSTIC HANDLER: 'action_type' FOUND in context.user_data: '{action_type}'.")
        reply_message = f"✅ Diagnóstico: Recibido con estado '{action_type}' en context.user_data."
        # Verificar si coincide con el estado persistido
        if raw_conv_state == TYPING_REPLY:
             reply_message += "\nEstado persistido coincide (TYPING_REPLY)."
             logger.info("DIAGNOSTIC HANDLER: Persisted state matches TYPING_REPLY.")
        else:
             reply_message += f"\n⚠️ Estado persistido NO coincide ({raw_conv_state})."
             logger.warning(f"DIAGNOSTIC HANDLER: Mismatch! Persisted state is {raw_conv_state}, expected {TYPING_REPLY}.")

    else:
        logger.error(f"DIAGNOSTIC HANDLER: 'action_type' NOT FOUND in context.user_data for user {user.id}! State was lost or not loaded.")
        reply_message = "❌ Diagnóstico: Recibido pero 'action_type' NO está en context.user_data."
        # Comprobar si al menos estaba en la persistencia
        if persisted_user_data_snapshot and persisted_user_data_snapshot.get('action_type'):
            persisted_action = persisted_user_data_snapshot.get('action_type')
            reply_message += f"\nℹ️ Sin embargo, 'action_type' ({persisted_action}) SÍ estaba en los datos persistidos del usuario."
            logger.info(f"DIAGNOSTIC HANDLER: action_type found in raw persisted user data: {persisted_action}")
        if raw_conv_state == TYPING_REPLY:
            reply_message += "\nℹ️ Y el estado persistido SÍ era TYPING_REPLY."
            logger.info("DIAGNOSTIC HANDLER: Raw persisted state was TYPING_REPLY.")
        else:
            reply_message += f"\nℹ️ El estado persistido era {raw_conv_state}."

    reply_message += f"\nMensaje: '{message_text[:30]}...'\n(Conversación terminada para prueba)"
    await update.message.reply_text(reply_message)

    # Terminar la conversación después del diagnóstico
    context.user_data.clear()
    return ConversationHandler.END

# --- Handlers fuera de Conversación (sin cambios) ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE, called_from_receive_text: bool = False) -> None:
    """Maneja mensajes de texto enviados al bot en privado fuera de una conversación activa."""
    user = update.effective_user
    chat = update.effective_chat

    if not chat or chat.type != 'private' or not update.message or not update.message.text or update.message.text.startswith('/'):
        return

    if not called_from_receive_text:
        logger.info(f"Unexpected text message received from {user.id} in private chat (handler group 1 triggered): '{update.message.text[:50]}...'")

    try:
        await update.message.reply_text(
            "Hola 👋 Recibí tu mensaje, pero no estoy esperando una consulta o sugerencia en este momento.\n\n"
            "Si quieres enviar una, por favor, ve al grupo del Comité y utiliza los botones 🙋‍♂️ (Consulta) o 💡 (Sugerencia) en los temas correspondientes.\n\n"
            "También puedes usar /start para ver las opciones o /cancel si crees que estás en medio de una acción."
            , parse_mode=ParseMode.MARKDOWN
        )
    except TelegramError as e:
        logger.error(f"Failed to send unexpected message response to user {user.id}: {e}")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Permite al usuario cancelar la operación actual (consulta/sugerencia)."""
    user = update.effective_user
    chat = update.effective_chat

    if not chat or chat.type != 'private':
         return ConversationHandler.END

    logger.info(f"User {user.id} ({user.full_name}) executed /cancel.")
    if context.user_data: # Solo si había datos
        logger.debug(f"Cancelling conversation for user {user.id}. Previous user_data: {context.user_data}")
        context.user_data.clear()
        await update.message.reply_text("Operación cancelada.")
    else:
        await update.message.reply_text("No hay operación activa que cancelar.")

    return ConversationHandler.END

# --- Función Principal ---
def main() -> None:
    """Inicia el bot."""
    if not validar_variables():
        logger.critical("--- BOT DETENIDO: Errores críticos en la configuración ---")
        return

    try:
        # *** USA DictPersistence ***
        persistence = DictPersistence()
        logger.info("--- USANDO DictPersistence (EN MEMORIA) ---")
        # --- PicklePersistence comentado ---
        # persistence = PicklePersistence(filepath=PERSISTENCE_FILE)
        # logger.info(f"Usando PicklePersistence con archivo: {PERSISTENCE_FILE}")
    except Exception as e:
        logger.error(f"Error al inicializar Persistence: {e}", exc_info=True)
        persistence = None # Continuar sin persistencia si falla

    # Construir la aplicación
    application_builder = ApplicationBuilder().token(TOKEN)
    if persistence:
        application_builder = application_builder.persistence(persistence)
    application = application_builder.build()

    # Definir el ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(callback_iniciar, pattern="^iniciar_(consulta|sugerencia)$"),
            CommandHandler('start', start_handler, filters=filters.ChatType.PRIVATE)
        ],
        states={
            # Usar el handler de diagnóstico
            TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, diagnostic_receive_text)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_command, filters=filters.ChatType.PRIVATE),
            CommandHandler('start', start_handler, filters=filters.ChatType.PRIVATE),
            MessageHandler(filters.COMMAND & filters.ChatType.PRIVATE, cancel_command)
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
        name="consulta_sugerencia_conv",
        persistent=True, # Usará el objeto persistence configurado (DictPersistence)
    )

    # Añadir Handlers
    application.add_handler(conv_handler, group=0)
    application.add_handler(CommandHandler("postpaneles", post_panels_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("documentacion", documentacion_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_unexpected_message), group=1)

    # Inicia el Bot
    logger.info("--- Iniciando Polling del Bot (DictPersistence, DIAGNÓSTICO, DEBUG HABILITADO) ---")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"--- ERROR CRÍTICO DURANTE EL POLLING ---: {e}", exc_info=True)
    finally:
        logger.info("--- Bot Detenido ---")

if __name__ == '__main__':
    main()
