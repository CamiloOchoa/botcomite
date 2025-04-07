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
from telegram.constants import ParseMode
from telegram.error import TelegramError

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Estado para la Conversación ---
TYPING_REPLY = 0

# --- Variables Globales ---
TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
if not TOKEN:
    logger.critical("TELEGRAM_TOKEN no está configurada correctamente.")
    exit(1)

# Grupo del Comité (interno) para botones y documentación
GRUPO_ID = int(os.environ.get("GROUP_ID", "-1001234567890"))
TEMA_BOTON_CONSULTAS_COMITE = 272
TEMA_BOTON_SUGERENCIAS_COMITE = 291
# Grupo EXTERNO para recibir mensajes (debe ser un grupo con temas habilitados)
GRUPO_EXTERNO_ID = -1002433074372  
TEMA_CONSULTAS_EXTERNO = 69         
TEMA_SUGERENCIAS_EXTERNO = 71       
# Tema de Documentación (interno)
TEMA_DOCUMENTACION = 11  # Ajusta este valor según corresponda

def get_short_committee_id() -> str:
    return str(GRUPO_ID).replace("-100", "", 1)

def get_short_externo_id() -> str:
    return str(GRUPO_EXTERNO_ID).replace("-100", "", 1)

def validar_variables():
    try:
        if not TOKEN:
            raise ValueError("TELEGRAM_TOKEN no está configurada.")
        if GRUPO_ID >= 0:
            logger.warning(f"GROUP_ID ({GRUPO_ID}) inusual (se espera un ID negativo).")
        logger.info("✅ Variables validadas correctamente")
        return True
    except Exception as e:
        logger.critical(f"❌ Error en la validación de variables de entorno: {e}", exc_info=True)
        return False

# --- Función para enviar botones iniciales (en el grupo interno) ---
async def post_initial_buttons(context: ContextTypes.DEFAULT_TYPE) -> bool:
    success_count = 0

    # Botón de Consultas
    msg_con = (
        "Pulsa aquí si tienes alguna consulta sobre permisos, bolsa de horas, excedencias, etc. "
        "Tu mensaje será privado y solo se permite enviar uno por vez."
    )
    url_con = f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_CONSULTAS_COMITE}"
    kb_con = [[InlineKeyboardButton("Iniciar Consulta 🙋‍♂️", url=url_con)]]
    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_BOTON_CONSULTAS_COMITE,
            text=msg_con,
            reply_markup=InlineKeyboardMarkup(kb_con)
        )
        logger.info(f"Botón de Consulta enviado a G:{GRUPO_ID}, T:{TEMA_BOTON_CONSULTAS_COMITE}")
        success_count += 1
    except Exception as e:
        logger.error(f"Error enviando Botón Consulta: {e}", exc_info=True)

    # Botón de Sugerencias
    msg_sug = (
        "Pulsa aquí si tienes alguna sugerencia sobre el funcionamiento del grupo o el comité. "
        "Tu mensaje será privado y solo se permite enviar uno por vez."
    )
    url_sug = f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_SUGERENCIAS_COMITE}"
    kb_sug = [[InlineKeyboardButton("Iniciar Sugerencia 💡", url=url_sug)]]
    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_BOTON_SUGERENCIAS_COMITE,
            text=msg_sug,
            reply_markup=InlineKeyboardMarkup(kb_sug)
        )
        logger.info(f"Botón de Sugerencia enviado a G:{GRUPO_ID}, T:{TEMA_BOTON_SUGERENCIAS_COMITE}")
        success_count += 1
    except Exception as e:
        logger.error(f"Error enviando Botón Sugerencia: {e}", exc_info=True)

    return success_count > 0

async def post_buttons_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != 'private':
        return
    logger.info(f"/postbotones recibido de {update.effective_user.id}.")
    await update.message.reply_text("Intentando publicar/actualizar botones en el grupo del Comité...")
    try:
        success = await post_initial_buttons(context)
    except Exception as e:
        logger.error(f"Excepción en post_initial_buttons: {e}", exc_info=True)
        await update.message.reply_text("❌ Ocurrió un error al intentar postear los botones.")
        return
    if success:
        await update.message.reply_text("✅ ¡Botones posteados/actualizados con éxito!")
    else:
        await update.message.reply_text("⚠️ No se pudieron enviar los botones.")

async def documentacion_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            message_thread_id=TEMA_DOCUMENTACION,
            text="Documentación disponible:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Mensaje de Documentación enviado a G:{GRUPO_ID}, T:{TEMA_DOCUMENTACION}")
    except Exception as e:
        logger.error(f"Error enviando Documentación a T:{TEMA_DOCUMENTACION}: {e}")

# --- Callback Handler para iniciar el flujo en privado ---
async def callback_iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    context.user_data.clear()

    try:
        if data == "iniciar_consulta":
            context.user_data['action_type'] = "consulta"
            prompt = (
                "Hola, por favor, escribe ahora tu consulta en un único mensaje.\n"
                "- Recibirás una respuesta en la mayor brevedad posible.\n"
                "- Recuerda que las consultas solo las pueden ver los miembros del comité."
            )
        elif data == "iniciar_sugerencia":
            context.user_data['action_type'] = "sugerencia"
            prompt = (
                "Hola, por favor, escribe ahora tu sugerencia en un único mensaje.\n"
                "- Recuerda que las sugerencias solo las pueden ver los miembros del comité."
            )
        else:
            await context.bot.send_message(chat_id=user.id, text="Acción no reconocida.")
            return ConversationHandler.END

        # Comprobar si el usuario puede recibir mensajes privados
        try:
            await context.bot.send_chat_action(chat_id=user.id, action="typing")
        except TelegramError as e:
            raise e

        await context.bot.send_message(chat_id=user.id, text=prompt)
        return TYPING_REPLY

    except TelegramError as e:
        # Si falla, el usuario no ha iniciado conversación con el bot
        start_link = f"https://t.me/ComitePolobot?start={data}"
        await query.message.reply_text(
            f"Parece que aún no has iniciado una conversación privada conmigo. Inicia el chat pulsando este enlace y luego vuelve a presionar el botón:\n{start_link}"
        )
        return ConversationHandler.END

# --- Handler para /start (flujo de conversación) ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    chat = update.effective_chat
    args = context.args

    if chat.type != 'private':
        return ConversationHandler.END

    if args:
        payload = args[0]
        if payload == "iniciar_consulta":
            context.user_data.clear()
            context.user_data['action_type'] = "consulta"
            prompt = (
                "Hola, por favor, escribe ahora tu consulta en un único mensaje.\n"
                "- Recibirás una respuesta en la mayor brevedad posible.\n"
                "- Recuerda que las consultas solo las pueden ver los miembros del comité."
            )
            await update.message.reply_text(prompt)
            return TYPING_REPLY
        elif payload == "iniciar_sugerencia":
            context.user_data.clear()
            context.user_data['action_type'] = "sugerencia"
            prompt = (
                "Hola, por favor, escribe ahora tu sugerencia en un único mensaje.\n"
                "- Recuerda que las sugerencias solo las pueden ver los miembros del comité."
            )
            await update.message.reply_text(prompt)
            return TYPING_REPLY
        else:
            await update.message.reply_text("El enlace que has usado no es válido o ha expirado.")
            context.user_data.clear()
            return ConversationHandler.END
    else:
        await update.message.reply_text("Hola, para enviar una consulta o sugerencia, usa los botones en el grupo del Comité.")
        context.user_data.clear()
        return ConversationHandler.END

# --- Handler para recibir el texto del usuario (flujo de conversación) ---
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    message = update.message
    if not message or not message.text:
        context.user_data.clear()
        return ConversationHandler.END

    user_text = message.text.strip()
    action_type = context.user_data.pop('action_type', None)
    if not action_type:
        await handle_unexpected_message(update, context)
        return ConversationHandler.END

    # Validar longitud mínima
    if len(user_text) < 15:
        if action_type == "consulta":
            error_text = (
                "Mensaje demasiado corto, el mensaje no ha sido enviado.\n"
                "Inicia una nueva consulta presionando el siguiente botón."
            )
            button = InlineKeyboardButton(
                "Ir al tema de Consulta",
                url=f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_CONSULTAS_COMITE}"
            )
        else:
            error_text = (
                "Mensaje demasiado corto, el mensaje no ha sido enviado.\n"
                "Inicia una nueva sugerencia presionando el siguiente botón."
            )
            button = InlineKeyboardButton(
                "Ir al tema de Sugerencia",
                url=f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_SUGERENCIAS_COMITE}"
            )
        markup = InlineKeyboardMarkup([[button]])
        await update.message.reply_text(error_text, reply_markup=markup)
        return ConversationHandler.END

    # Log adicional para verificar datos de envío
    logger.info(f"Enviando {action_type} al grupo EXTERNO: chat_id={GRUPO_EXTERNO_ID}, tema={TEMA_CONSULTAS_EXTERNO if action_type=='consulta' else TEMA_SUGERENCIAS_EXTERNO}")

    if action_type == "consulta":
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_CONSULTAS_EXTERNO
    else:
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_SUGERENCIAS_EXTERNO

    user_info = user.full_name
    if user.username:
        user_info += f" (@{user.username})"
    fwd_msg = f"ℹ️ **Nueva {action_type.capitalize()} de {user_info}**:\n\n{user_text}"
    try:
        await context.bot.send_message(
            chat_id=target_chat_id,
            message_thread_id=target_thread_id,
            text=fwd_msg,
            parse_mode=ParseMode.MARKDOWN
        )
        await update.message.reply_text(f"✅ ¡Tu {action_type} ha sido enviada correctamente! Gracias.")
    except TelegramError as e:
        logger.error(f"Error de Telegram API enviando {action_type}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Hubo un problema al enviar tu {action_type}.")
    except Exception as e:
        logger.error(f"Excepción inesperada enviando {action_type}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ocurrió un error inesperado al procesar tu {action_type}.")

    context.user_data.clear()
    return ConversationHandler.END

# --- Handler para mensajes fuera de flujo ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Ir al tema de Consulta", url=f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_CONSULTAS_COMITE}")],
        [InlineKeyboardButton("Ir al tema de Sugerencia", url=f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_SUGERENCIAS_COMITE}")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Si quieres hacer otra consulta o sugerencia, presiona los botones que hay a continuación:",
        reply_markup=markup
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operación cancelada. Puedes empezar de nuevo usando los botones del grupo.")
    context.user_data.clear()
    return ConversationHandler.END

async def foro_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != 'private':
        return

    text_consultas = (
        "Si no has encontrado la información que buscas en las secciones del grupo (permisos, bolsa de horas, excedencias, etc...), "
        "pulsa el siguiente botón y envíanos un mensaje.\n"
        "- Recuerda que estas consultas son privadas y solo pueden verlas los miembros del comité.\n"
        "- La consulta debe ser enviada en un solo mensaje."
    )
    kb_consultas = [[InlineKeyboardButton("Iniciar consulta", callback_data="iniciar_consulta")]]
    markup_consultas = InlineKeyboardMarkup(kb_consultas)
    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_BOTON_CONSULTAS_COMITE,
            text=text_consultas,
            reply_markup=markup_consultas
        )
        logger.info("Mensaje de consultas enviado al foro interno de consultas.")
    except Exception as e:
        logger.error(f"Error enviando mensaje de consultas: {e}", exc_info=True)

    text_sugerencias = (
        "Pulsa el botón si tienes alguna sugerencia para mejorar el grupo o el funcionamiento del comité.\n"
        "- Recuerda que estas sugerencias son privadas y solo pueden verlas los miembros del comité.\n"
        "- La sugerencia debe ser enviada en un solo mensaje."
    )
    kb_sugerencias = [[InlineKeyboardButton("Iniciar sugerencia", callback_data="iniciar_sugerencia")]]
    markup_sugerencias = InlineKeyboardMarkup(kb_sugerencias)
    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_BOTON_SUGERENCIAS_COMITE,
            text=text_sugerencias,
            reply_markup=markup_sugerencias
        )
        logger.info("Mensaje de sugerencias enviado al foro interno de sugerencias.")
    except Exception as e:
        logger.error(f"Error enviando mensaje de sugerencias: {e}", exc_info=True)

def main() -> None:
    if not validar_variables():
        logger.critical("--- BOT DETENIDO: Errores críticos en la configuración ---")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start_handler, filters=filters.ChatType.PRIVATE),
            CallbackQueryHandler(callback_iniciar, pattern="^iniciar_.*")
        ],
        states={
            TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_command, filters=filters.ChatType.PRIVATE),
            CommandHandler('start', start_handler, filters=filters.ChatType.PRIVATE)
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
        name="consulta_sugerencia_conv",
        persistent=False
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("postbotones", post_buttons_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("documentacion", documentacion_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("postforo", foro_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_unexpected_message))

    logger.info("--- Iniciando Polling del Bot ---")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"--- ERROR CRÍTICO DURANTE EL POLLING ---: {e}", exc_info=True)
    finally:
        logger.info("--- Bot Detenido ---")

if __name__ == '__main__':
    main()
