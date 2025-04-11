# -*- coding: utf-8 -*-
import os
import logging
import pickle
from pathlib import Path

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
    PicklePersistence # Recomendado si funciona en Railway
    # DictPersistence # Alternativa si Pickle falla
)
from telegram.constants import ParseMode, ChatAction
from telegram.error import TelegramError

# --- Configuración de Logging (Nivel INFO normal) ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
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
MIN_MSG_LENGTH = 15
PERSISTENCE_FILE = "bot_persistence.pkl" # Usado por PicklePersistence

# --- Validación de Variables (sin cambios) ---
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
# (post_action_panels, post_panels_command, documentacion_command omitidas por brevedad)
async def post_action_panels(context: ContextTypes.DEFAULT_TYPE) -> bool:
    success_count = 0
    # Panel de Consultas
    text_consultas = "Pulsa aquí si tienes alguna consulta..."
    kb_consultas = [[InlineKeyboardButton("Iniciar Consulta 🙋‍♂️", callback_data="iniciar_consulta")]]
    markup_consultas = InlineKeyboardMarkup(kb_consultas)
    try:
        await context.bot.send_message(GRUPO_ID, TEMA_ID_PANEL_CONSULTAS, text=text_consultas, reply_markup=markup_consultas)
        logger.info(f"Panel Consulta enviado a G:{GRUPO_ID}, T:{TEMA_ID_PANEL_CONSULTAS}")
        success_count += 1
    except Exception as e: logger.error(f"Error Panel Consulta: {e}", exc_info=True)
    # Panel de Sugerencias
    text_sugerencias = "Pulsa aquí si tienes alguna sugerencia..."
    kb_sugerencias = [[InlineKeyboardButton("Iniciar Sugerencia 💡", callback_data="iniciar_sugerencia")]]
    markup_sugerencias = InlineKeyboardMarkup(kb_sugerencias)
    try:
        await context.bot.send_message(GRUPO_ID, TEMA_ID_PANEL_SUGERENCIAS, text=text_sugerencias, reply_markup=markup_sugerencias)
        logger.info(f"Panel Sugerencia enviado a G:{GRUPO_ID}, T:{TEMA_ID_PANEL_SUGERENCIAS}")
        success_count += 1
    except Exception as e: logger.error(f"Error Panel Sugerencia: {e}", exc_info=True)
    return success_count > 0
async def post_panels_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != 'private': return
    logger.info(f"/postpaneles recibido de {update.effective_user.id}.")
    await update.message.reply_text("Intentando publicar paneles...")
    try: success = await post_action_panels(context)
    except Exception as e: logger.error(f"Excepción en post_action_panels: {e}", exc_info=True); await update.message.reply_text("❌ Error posteando."); return
    await update.message.reply_text("✅ Paneles posteados." if success else "⚠️ No se pudieron enviar.")
async def documentacion_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != 'private': return
    logger.info(f"/documentacion recibido de {update.effective_user.id}.")
    await update.message.reply_text("Intentando publicar documentación...")
    keyboard = [ [InlineKeyboardButton("Calendario laboral", url="...")], [InlineKeyboardButton("Tablas salariales 2025", url="...")], [InlineKeyboardButton("Convenio", url="...")], [InlineKeyboardButton("Estatuto trabajadores", url="...")], [InlineKeyboardButton("Desconexión digital", url="...")], [InlineKeyboardButton("Protocolo LGTBI", url="...")], [InlineKeyboardButton("Protocolo acoso", url="...")], ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await context.bot.send_message(GRUPO_ID, TEMA_ID_DOCUMENTACION, text="📄 *Documentación disponible:*", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Documentación enviada a G:{GRUPO_ID}, T:{TEMA_ID_DOCUMENTACION}")
        await update.message.reply_text("✅ Documentación posteada.")
    except Exception as e: logger.error(f"Error Documentación: {e}", exc_info=True); await update.message.reply_text("❌ Error enviando documentación.")


# --- Handlers de Conversación (Lógica interna sin cambios, solo configuración del handler) ---
async def callback_iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manejador para los botones 'iniciar_consulta' e 'iniciar_sugerencia'."""
    query = update.callback_query
    user = query.from_user
    data = query.data

    context.user_data.clear() # Iniciar siempre limpio para este flujo
    await query.answer()
    logger.debug(f"User {user.id} started conversation via callback '{data}'. Cleared user_data first.")

    try:
        action_text = ""
        if data == "iniciar_consulta":
            context.user_data['action_type'] = "consulta"
            action_text = "consulta"
            prompt = "Hola 👋 Por favor, escribe ahora tu *consulta*..." # Mensaje completo omitido
        elif data == "iniciar_sugerencia":
            context.user_data['action_type'] = "sugerencia"
            action_text = "sugerencia"
            prompt = "Hola 👋 Por favor, escribe ahora tu *sugerencia*..." # Mensaje completo omitido
        else:
            logger.warning(f"Callback data inesperado: {data}")
            return ConversationHandler.END

        await context.bot.send_message(chat_id=user.id, text=prompt, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Prompt for '{action_text}' sent to user {user.id}. Entering TYPING_REPLY state.")
        # Persistencia debería guardar aquí
        return TYPING_REPLY

    except TelegramError as e: # Manejo de errores sin cambios
        if "bot can't initiate conversation" in str(e) or "chat not found" in str(e):
            await query.answer(text=f"⚠️ Necesitas iniciar el chat (@{context.bot.username})...", show_alert=True)
        else: await query.answer("❌ Error técnico.", show_alert=True)
        logger.error(f"Error en callback_iniciar: {e}", exc_info=True)
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e: # Manejo de errores sin cambios
        logger.error(f"Excepción en callback_iniciar: {e}", exc_info=True)
        await query.answer("❌ Error inesperado.", show_alert=True)
        context.user_data.clear()
        return ConversationHandler.END

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manejador para /start."""
    user = update.effective_user
    chat = update.effective_chat
    args = context.args

    if chat.type != 'private': return ConversationHandler.END
    logger.info(f"/start de {user.id} con args: {args}")
    context.user_data.clear()

    if args: # Lógica de deep link sin cambios
        payload = args[0]
        if payload == "iniciar_consulta":
            context.user_data['action_type'] = "consulta"
            prompt = "Hola de nuevo 👋... (consulta)" # Mensaje omitido
            await update.message.reply_text(prompt, parse_mode=ParseMode.MARKDOWN)
            return TYPING_REPLY
        elif payload == "iniciar_sugerencia":
            context.user_data['action_type'] = "sugerencia"
            prompt = "Hola de nuevo 👋... (sugerencia)" # Mensaje omitido
            await update.message.reply_text(prompt, parse_mode=ParseMode.MARKDOWN)
            return TYPING_REPLY
        else:
            await update.message.reply_text("Hola 👋. Enlace no válido...")
            return ConversationHandler.END
    else: # /start normal
        await update.message.reply_text("Hola 👋 Soy el bot asistente...", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el mensaje de consulta/sugerencia y lo reenvía (versión funcional)."""
    user = update.effective_user
    message = update.message

    logger.info(f"receive_text: Message received from user {user.id}.")
    # Verificar user_data (ya no necesitamos el log detallado de persistencia aquí)
    logger.debug(f"receive_text: context.user_data: {context.user_data}")

    if not message or not message.text:
        logger.warning(f"receive_text: Empty/non-text message from {user.id}. Ending.")
        context.user_data.clear()
        return ConversationHandler.END

    user_text = message.text.strip()
    action_type = context.user_data.get('action_type')

    if not action_type:
        # Esto YA NO debería ocurrir si per_chat=False funciona
        logger.error(f"receive_text: 'action_type' MISSING for user {user.id}! user_data: {context.user_data}. Falling back.")
        await handle_unexpected_message(update, context, called_from_receive_text=True)
        context.user_data.clear()
        return ConversationHandler.END

    # --- Comprobación de longitud ---
    if len(user_text) < MIN_MSG_LENGTH:
        logger.info(f"{action_type} de {user.id} demasiado corta.")
        error_text = f"⚠️ Tu {action_type} parece demasiado corta..." # Mensaje omitido
        await update.message.reply_text(error_text, parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()
        return ConversationHandler.END

    # --- Preparación y envío al grupo externo ---
    logger.info(f"Preparando {action_type} de {user.id} para enviar.")
    target_chat_id = GRUPO_EXTERNO_ID
    if action_type == "consulta": target_thread_id = TEMA_ID_CONSULTAS_EXTERNO; action_emoji = "🙋‍♂️"
    elif action_type == "sugerencia": target_thread_id = TEMA_ID_SUGERENCIAS_EXTERNO; action_emoji = "💡"
    else: # No debería ocurrir
        logger.error(f"receive_text: action_type desconocido '{action_type}'.")
        await update.message.reply_text("❌ Error interno (RT_UNK_AT).")
        context.user_data.clear(); return ConversationHandler.END

    # Construir mensaje y escapar MarkdownV2
    user_mention = user.mention_markdown_v2() if user.username else user.full_name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
    fwd_msg_header = f"{action_emoji} *Nueva {action_type.capitalize()} de {user_mention}* `(ID: {user.id})`:\n{'-'*20}\n"
    escaped_body = user_text.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
    fwd_msg = fwd_msg_header + escaped_body

    message_sent_to_group = False
    try:
        logger.info(f"Enviando {action_type} de {user.id} a G:{target_chat_id} T:{target_thread_id}")
        await context.bot.send_message(
            chat_id=target_chat_id, message_thread_id=target_thread_id,
            text=fwd_msg, parse_mode=ParseMode.MARKDOWN_V2
        )
        message_sent_to_group = True
        logger.info(f"✅ {action_type} de {user.id} enviada.")
        await update.message.reply_text(f"✅ ¡Tu {action_type} ha sido enviada correctamente! Gracias.")
    except TelegramError as e:
        logger.error(f"TelegramError enviando {action_type}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Problema técnico al enviar (TG-{e.__class__.__name__})...")
    except Exception as e:
        logger.error(f"Excepción enviando {action_type}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error inesperado al procesar (EXC-{e.__class__.__name__})...")

    context.user_data.clear()
    return ConversationHandler.END


# --- Handlers Fuera de Conversación (sin cambios) ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE, called_from_receive_text: bool = False) -> None:
    """Maneja mensajes de texto fuera de conversación activa."""
    # ... (lógica igual que antes) ...
    user = update.effective_user; chat = update.effective_chat
    if not chat or chat.type != 'private' or not update.message or not update.message.text or update.message.text.startswith('/'): return
    if not called_from_receive_text: logger.info(f"Unexpected text from {user.id}: '{update.message.text[:50]}...'")
    try: await update.message.reply_text("Hola 👋 Recibí tu mensaje, pero no estoy esperando...", parse_mode=ParseMode.MARKDOWN)
    except Exception as e: logger.error(f"Error en handle_unexpected_message: {e}")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual."""
    # ... (lógica igual que antes) ...
    user = update.effective_user; chat = update.effective_chat
    if not chat or chat.type != 'private': return ConversationHandler.END
    logger.info(f"User {user.id} ejecutó /cancel.")
    if context.user_data: logger.debug(f"Cancelando. Datos previos: {context.user_data}"); context.user_data.clear(); await update.message.reply_text("Operación cancelada.")
    else: await update.message.reply_text("No hay operación activa.")
    return ConversationHandler.END

# --- Función Principal ---
def main() -> None:
    """Inicia el bot."""
    if not validar_variables():
        logger.critical("--- BOT DETENIDO: Errores críticos en la configuración ---")
        return

    try:
        # Usar PicklePersistence (recomendado si funciona en Railway)
        persistence = PicklePersistence(filepath=PERSISTENCE_FILE)
        logger.info(f"Usando PicklePersistence con archivo: {PERSISTENCE_FILE}")
        # O usar DictPersistence si Pickle da problemas
        # persistence = DictPersistence()
        # logger.info("--- USANDO DictPersistence (EN MEMORIA) ---")
    except Exception as e:
        logger.error(f"Error al inicializar Persistence: {e}", exc_info=True)
        persistence = None

    # Construir la aplicación
    application_builder = ApplicationBuilder().token(TOKEN)
    if persistence:
        application_builder = application_builder.persistence(persistence)
    application = application_builder.build()

    # --- Define el manejador de conversación ---
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(callback_iniciar, pattern="^iniciar_(consulta|sugerencia)$"),
            CommandHandler('start', start_handler, filters=filters.ChatType.PRIVATE)
        ],
        states={
            # Volver a usar la función receive_text normal
            TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_command, filters=filters.ChatType.PRIVATE),
            CommandHandler('start', start_handler, filters=filters.ChatType.PRIVATE),
            MessageHandler(filters.COMMAND & filters.ChatType.PRIVATE, cancel_command)
        ],
        allow_reentry=True,
        # *** CAMBIO CLAVE AQUÍ ***
        per_user=True,     # Mantener estado por usuario
        per_chat=False,    # <-- IGNORAR el chat de origen para el estado
        name="consulta_sugerencia_conv",
        persistent=True,   # Usar el objeto persistence configurado
    )

    # --- Añadir Handlers ---
    application.add_handler(conv_handler, group=0) # Prioridad
    application.add_handler(CommandHandler("postpaneles", post_panels_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("documentacion", documentacion_command, filters=filters.ChatType.PRIVATE))
    # Handler para mensajes inesperados (fuera de conversación)
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_unexpected_message), group=1)

    # --- Inicia el Bot ---
    logger.info("--- Iniciando Polling del Bot (per_chat=False) ---")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"--- ERROR CRÍTICO DURANTE EL POLLING ---: {e}", exc_info=True)
        # Asegurarse de que no haya errores 'Conflict' aquí si ya se solucionó
        if isinstance(e, TelegramError) and "Conflict" in str(e):
            logger.critical("!!! EL ERROR 'Conflict' SIGUE OCURRIENDO. DEBES DETENER INSTANCIAS ANTIGUAS DEL BOT !!!")
    finally:
        logger.info("--- Bot Detenido ---")

if __name__ == '__main__':
    main()
