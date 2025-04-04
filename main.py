import os
import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ApplicationHandlerStop
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Verificar token desde variable de entorno ---
TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
logger.info(f"Token length: {len(TOKEN)}")
if not TOKEN:
    logger.critical("TELEGRAM_TOKEN no está configurada correctamente.")
    exit(1)

# --- Variables Globales ---
# Grupo del Comité (interno) para botones y documentación
GRUPO_ID = int(os.environ.get("GROUP_ID", "-1001234567890"))
TEMA_BOTON_CONSULTAS_COMITE = 272
TEMA_BOTON_SUGERENCIAS_COMITE = 291
# Grupo EXTERNO para recibir mensajes de consultas/sugerencias
GRUPO_EXTERNO_ID = -1002433074372  
TEMA_CONSULTAS_EXTERNO = 69         
TEMA_SUGERENCIAS_EXTERNO = 71       
# Tema de Documentación (interno)
TEMA_DOCUMENTACION = 11  # Ajusta este valor según corresponda

# --- Funciones auxiliares ---
def get_short_committee_id() -> str:
    return str(GRUPO_ID).replace("-100", "", 1)

def get_short_externo_id() -> str:
    return str(GRUPO_EXTERNO_ID).replace("-100", "", 1)

def validar_variables():
    try:
        if not TOKEN:
            raise ValueError("TELEGRAM_TOKEN no está configurada.")
        if GRUPO_ID >= 0:
            logger.warning(f"GROUP_ID ({GRUPO_ID}) inusual (se espera un ID negativo para supergrupos).")
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
    markup_con = InlineKeyboardMarkup(kb_con)
    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_BOTON_CONSULTAS_COMITE,
            text=msg_con,
            reply_markup=markup_con
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
    markup_sug = InlineKeyboardMarkup(kb_sug)
    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_BOTON_SUGERENCIAS_COMITE,
            text=msg_sug,
            reply_markup=markup_sug
        )
        logger.info(f"Botón de Sugerencia enviado a G:{GRUPO_ID}, T:{TEMA_BOTON_SUGERENCIAS_COMITE}")
        success_count += 1
    except Exception as e:
        logger.error(f"Error enviando Botón Sugerencia: {e}", exc_info=True)

    return success_count > 0

# --- Comando /postbotones (no afecta al flujo de consultas) ---
async def post_buttons_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if update.effective_chat.type != 'private':
        return
    logger.info(f"/postbotones recibido de {user.id}.")
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
        await update.message.reply_text("⚠️ No se pudieron enviar uno o ambos botones.")
    
# --- Comando /documentacion ---
async def documentacion_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Calendario Laboral", url="https://t.me/c/YOUR_GROUP_ID/11")],
        [InlineKeyboardButton("Tablas Salariales 2025", url="https://t.me/c/YOUR_GROUP_ID/12")],
        [InlineKeyboardButton("Convenio", url="https://t.me/c/YOUR_GROUP_ID/13")],
        [InlineKeyboardButton("Protocolo Acoso", url="https://t.me/c/YOUR_GROUP_ID/14")]
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

# --- Callback Handler: cuando se pulsa el botón en /postforo ---
async def callback_iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data
    if data == "iniciar_consulta":
        context.user_data.clear()
        context.user_data['action_type'] = "consulta"
        prompt = (
            "Hola, por favor, escribe ahora tu consulta en un único mensaje.\n"
            "- Recibirás una respuesta en la mayor brevedad posible.\n"
            "- Recuerda que las consultas solo las pueden ver los miembros del comité."
        )
        await context.bot.send_message(chat_id=user.id, text=prompt)
    elif data == "iniciar_sugerencia":
        context.user_data.clear()
        context.user_data['action_type'] = "sugerencia"
        prompt = (
            "Hola, por favor, escribe ahora tu sugerencia en un único mensaje.\n"
            "- Recuerda que las sugerencias solo las pueden ver los miembros del comité."
        )
        await context.bot.send_message(chat_id=user.id, text=prompt)
    else:
        await context.bot.send_message(chat_id=user.id, text="Acción no reconocida.")

# --- Comando /postforo: envía los mensajes a los temas internos ---
async def foro_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Mensaje para consultas
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
        logger.info("Mensaje de consultas enviado al tema interno de consultas.")
    except Exception as e:
        logger.error(f"Error enviando mensaje de consultas: {e}")
    # Mensaje para sugerencias
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
        logger.info("Mensaje de sugerencias enviado al tema interno de sugerencias.")
    except Exception as e:
        logger.error(f"Error enviando mensaje de sugerencias: {e}")

# --- Handler Global para mensajes en privado (flujo de conversación) ---
async def private_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Procesa los mensajes en privado:
    - Si se tiene 'action_type' en context.user_data, se procesa como parte del flujo (llama a receive_text).
    - Si no, se llama a handle_unexpected_message.
    """
    if context.user_data.get('action_type'):
        await receive_text(update, context)
    else:
        await handle_unexpected_message(update, context)

# --- Handler para /cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    try:
        await update.message.reply_text("Operación cancelada. Puedes empezar de nuevo usando los botones del grupo.")
    except Exception as e:
        logger.error(f"Error enviando mensaje de cancelación a {user.id}: {e}")
    context.user_data.clear()

# --- Handler para Recibir Texto (Flujo de Conversación) ---
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not message or not message.text:
        return
    user_text = message.text.strip()
    action_type = context.user_data.pop('action_type', None)
    if not action_type:
        # Si no hay flujo activo, se considera mensaje fuera de contexto
        await handle_unexpected_message(update, context)
        return

    # Validación de longitud: mínimo 15 caracteres
    if len(user_text) < 15:
        if action_type == "consulta":
            error_text = (
                "Mensaje demasiado corto, el mensaje no ha sido enviado. "
                "Inicia una nueva consulta presionando el siguiente botón."
            )
            button = InlineKeyboardButton(
                "Ir al tema de Consulta",
                url=f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_CONSULTAS_COMITE}"
            )
        else:
            error_text = (
                "Mensaje demasiado corto, el mensaje no ha sido enviado. "
                "Inicia una nueva sugerencia presionando el siguiente botón."
            )
            button = InlineKeyboardButton(
                "Ir al tema de Sugerencia",
                url=f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_SUGERENCIAS_COMITE}"
            )
        reply_markup = InlineKeyboardMarkup([[button]])
        try:
            await update.message.reply_text(error_text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error enviando mensaje de longitud insuficiente a {user.id}: {e}")
        return

    # Validación adicional para consultas prohibidas
    if action_type == 'consulta':
        text_lower = user_text.lower()
        forbidden_map = {
            "bolsa de horas": "bolsa de horas",
            "permiso": "permisos",
            "permisos": "permisos",
            "incapacidad temporal": "incapacidad temporal / baja",
            "baja": "incapacidad temporal / baja",
            "excedencia": "excedencias",
            "excedencias": "excedencias"
        }
        for keyword, topic_name in forbidden_map.items():
            if keyword in text_lower:
                try:
                    await update.message.reply_text(
                        f"❌ Tu consulta sobre '{topic_name}' no puede ser procesada por este bot.\n"
                        "Por favor, revisa la información en el grupo o la documentación oficial."
                    )
                except Exception as e:
                    logger.error(f"Error enviando mensaje de rechazo a {user.id}: {e}")
                return

    # Enviar mensaje al grupo EXTERNO sin incluir el ID
    if action_type == 'consulta':
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_CONSULTAS_EXTERNO
    elif action_type == 'sugerencia':
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_SUGERENCIAS_EXTERNO
    else:
        await update.message.reply_text("❌ Error interno: acción no reconocida.")
        return

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
        logger.error(f"Error de Telegram API enviando {action_type} de {user.id}: {e}", exc_info=False)
        await update.message.reply_text(f"❌ Hubo un problema al enviar tu {action_type}.")
    except Exception as e:
        logger.error(f"Excepción inesperada enviando {action_type} de {user.id}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ocurrió un error inesperado al procesar tu {action_type}.")

    # Fin del flujo
    context.user_data.clear()

# --- Handler para Mensajes Fuera de Flujo ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('action_type'):
        await receive_text(update, context)
    else:
        keyboard = [
            [InlineKeyboardButton("Ir al tema de Consulta", url=f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_CONSULTAS_COMITE}")],
            [InlineKeyboardButton("Ir al tema de Sugerencia", url=f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_SUGERENCIAS_COMITE}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Si quieres hacer otra consulta o sugerencia, presiona los botones que hay a continuación:", reply_markup=reply_markup)

# --- Configuración y Ejecución Principal ---
def main() -> None:
    if not validar_variables():
        logger.critical("--- BOT DETENIDO: ERRORES CRÍTICOS EN LA CONFIGURACIÓN ---")
        return

    application = Application.builder().token(TOKEN).build()

    # Registramos los comandos y handlers en chat privado
    application.add_handler(CommandHandler("postbotones", post_buttons_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("documentacion", documentacion_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("postforo", foro_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CallbackQueryHandler(callback_iniciar, pattern="^iniciar_.*"), group=1)
    # Handler global para mensajes privados
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, private_message_handler), group=2)
    application.add_handler(CommandHandler("cancel", cancel, filters=filters.ChatType.PRIVATE), group=2)

    logger.info("--- Iniciando Polling del Bot ---")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"--- ERROR CRÍTICO DURANTE EL POLLING ---: {e}", exc_info=True)
    finally:
        logger.info("--- Bot Detenido ---")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"Error fatal durante la inicialización del bot: {e}", exc_info=True)
