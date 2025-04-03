import os
import logging
import re

# --- Imports Limpios ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
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

# --- Estado para la Conversación ---
TYPING_REPLY = 0

# --- IDs y Variables Globales ---
# Grupo del Comité (interno) para botones
GRUPO_ID = int(os.environ.get("GROUP_ID", "-1001234567890"))
TEMA_BOTON_CONSULTAS_COMITE = 272
TEMA_BOTON_SUGERENCIAS_COMITE = 291
# Grupo externo para recibir mensajes de consultas y sugerencias
GRUPO_EXTERNO_ID = -1002433074372  
TEMA_CONSULTAS_EXTERNO = 69         
TEMA_SUGERENCIAS_EXTERNO = 71       
# Tema de Documentación (en el grupo interno)
TEMA_DOCUMENTACION = 11  # Ajusta este valor según corresponda

# --- Funciones auxiliares para obtener los short id ---
def get_short_committee_id() -> str:
    """Convierte el ID del grupo del Comité al formato de enlace (sin el prefijo -100)."""
    return str(GRUPO_ID).replace("-100", "", 1)

def get_short_externo_id() -> str:
    """Convierte el ID del grupo externo al formato de enlace (sin el prefijo -100)."""
    return str(GRUPO_EXTERNO_ID).replace("-100", "", 1)

# --- Validación de Variables de Entorno ---
def validar_variables():
    """Valida las variables de entorno necesarias."""
    global TOKEN, GRUPO_ID
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

# --- Función para Enviar Botones Iniciales (Comité Interno) ---
async def post_initial_buttons(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Envía los mensajes iniciales con botones URL al grupo del Comité (interno)."""
    if not TOKEN or not GRUPO_ID or GRUPO_ID >= 0:
        logger.error("Faltan TOKEN o GROUP_ID (inválido) para postear botones.")
        return False
    if TEMA_BOTON_CONSULTAS_COMITE <= 0 or TEMA_BOTON_SUGERENCIAS_COMITE <= 0:
        logger.error("IDs de tema para botones son inválidos.")
        return False

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
        logger.info(f"Botón de Consulta enviado al Grupo {GRUPO_ID}, Tema {TEMA_BOTON_CONSULTAS_COMITE}")
        success_count += 1
    except TelegramError as e:
        logger.error(f"Error enviando Botón Consulta: {e}", exc_info=False)
    except Exception as e:
        logger.error(f"Excepción inesperada enviando Botón Consulta: {e}", exc_info=True)

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
        logger.info(f"Botón de Sugerencia enviado al Grupo {GRUPO_ID}, Tema {TEMA_BOTON_SUGERENCIAS_COMITE}")
        success_count += 1
    except TelegramError as e:
        logger.error(f"Error enviando Botón Sugerencia: {e}", exc_info=False)
    except Exception as e:
        logger.error(f"Excepción inesperada enviando Botón Sugerencia: {e}", exc_info=True)

    return success_count > 0

# --- Comando para Postear Botones ---
async def post_buttons_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /postbotones para uso del administrador en chat privado."""
    user = update.effective_user
    chat = update.effective_chat
    if not chat or chat.type != 'private':
        logger.warning(f"Intento de usar /postbotones fuera de chat privado por {user.id if user else '?'}")
        return
    logger.info(f"Comando /postbotones recibido de {user.id}.")
    await update.message.reply_text("Intentando publicar/actualizar botones en el grupo del Comité...")
    try:
        success = await post_initial_buttons(context)
    except Exception as e:
        logger.error(f"Excepción en post_initial_buttons: {e}", exc_info=True)
        await update.message.reply_text("❌ Ocurrió un error inesperado al intentar postear los botones.")
        raise ApplicationHandlerStop
    if success:
        await update.message.reply_text("✅ ¡Botones posteados/actualizados con éxito!")
    else:
        await update.message.reply_text("⚠️ No se pudieron enviar uno o ambos botones. Revisa los logs del bot.")
    raise ApplicationHandlerStop

# --- Comando para Documentación ---
async def documentacion_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Envía un mensaje al tema de Documentación en el grupo interno, mostrando 4 botones.
    El mensaje mostrará solo 'Documentación disponible:' y los botones.
    """
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

# --- Handler para /start ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """
    Manejador del comando /start.
    Si viene con payload (iniciar_consulta o iniciar_sugerencia), se inicia el flujo.
    """
    user = update.effective_user
    chat = update.effective_chat
    args = context.args
    logger.info(f"/start de {user.id if user else '?'} en chat:{chat.id if chat else '?'} - Args: {args}")
    if chat and chat.type == "private":
        if args:
            payload = args[0]
            action_type = None
            if payload == "iniciar_consulta":
                action_type = "consulta"
            elif payload == "iniciar_sugerencia":
                action_type = "sugerencia"
            if action_type:
                context.user_data.clear()
                logger.info(f"Payload '{payload}' válido recibido de {user.id}.")
                context.user_data['action_type'] = action_type
                if action_type == "consulta":
                    prompt = (
                        "Si no has encontrado la información que buscas en las secciones del grupo (permisos, bolsa de horas, excedencias, etc...), "
                        "pulsa el siguiente botón y envíanos un mensaje. Recuerda que estas consultas son privadas y solo pueden verlas los miembros del comité. "
                        "La consulta debe ser enviada en un solo mensaje."
                    )
                else:  # sugerencia
                    prompt = (
                        "Si no has encontrado la información que buscas en las secciones del grupo (permisos, bolsa de horas, excedencias, etc...), "
                        "pulsa el siguiente botón y envíanos un mensaje. Recuerda que estas sugerencias son privadas y solo pueden verlas los miembros del comité. "
                        "La sugerencia debe ser enviada en un solo mensaje."
                    )
                await update.message.reply_text(prompt)
                return TYPING_REPLY
            else:
                logger.warning(f"Payload desconocido '{payload}' recibido de {user.id}.")
                await update.message.reply_text("El enlace que has usado no es válido o ha expirado.")
                context.user_data.clear()
                raise ApplicationHandlerStop
                return ConversationHandler.END
        else:
            logger.info(f"/start simple de {user.id}.")
            await update.message.reply_text("Hola, para enviar una consulta o sugerencia, por favor, usa los botones en el grupo del Comité.")
            context.user_data.clear()
            raise ApplicationHandlerStop
            return ConversationHandler.END
    elif chat:
        logger.info(f"/start ignorado en chat no privado ({chat.id}, tipo: {chat.type})")
    return None

# --- Handler para Recibir Texto (Consulta/Sugerencia) ---
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Recibe el primer mensaje (consulta o sugerencia) en chat privado.
    Se procesa y se envía al grupo EXTERNO, y se termina la conversación.
    """
    user = update.effective_user
    message = update.message
    chat = update.effective_chat
    if not user or not message or not message.text or not chat or chat.type != 'private':
        logger.warning(f"receive_text recibió un update inválido. User: {user.id if user else '?'}")
        context.user_data.clear()
        raise ApplicationHandlerStop
        return ConversationHandler.END

    user_text = message.text
    action_type = context.user_data.pop('action_type', None)
    if not action_type:
        keyboard = [
            [InlineKeyboardButton("Ir al tema de Consulta", url=f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_CONSULTAS_COMITE}")],
            [InlineKeyboardButton("Ir al tema de Sugerencia", url=f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_SUGERENCIAS_COMITE}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await update.message.reply_text("Si quieres hacer otra consulta o sugerencia, presiona los botones que hay a continuación:", reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error enviando mensaje de reinicio a {user.id}: {e}")
        raise ApplicationHandlerStop
        return ConversationHandler.END

    logger.info(f"Procesando '{action_type}' de {user.id}. Texto: {user_text[:50]}...")
    # Validación de longitud: mínimo 15 caracteres
    if len(user_text.strip()) < 15:
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
        raise ApplicationHandlerStop
        return ConversationHandler.END

    # Validación adicional para consultas (temas prohibidos)
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
                logger.warning(f"Consulta de {user.id} rechazada por tema prohibido: '{topic_name}'.")
                try:
                    await update.message.reply_text(
                        f"❌ Tu consulta sobre '{topic_name}' no puede ser procesada por este bot.\n"
                        "Por favor, revisa la información en el grupo o la documentación oficial."
                    )
                except Exception as e:
                    logger.error(f"Error enviando mensaje de rechazo a {user.id}: {e}")
                raise ApplicationHandlerStop
                return ConversationHandler.END

    # Determinar destino: enviar al grupo EXTERNO
    if action_type == 'consulta':
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_CONSULTAS_EXTERNO
    elif action_type == 'sugerencia':
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_SUGERENCIAS_EXTERNO
    else:
        logger.error(f"Valor inesperado para 'action_type' ({action_type}) en {user.id}.")
        try:
            await update.message.reply_text("❌ Ha ocurrido un error interno inesperado. No se pudo procesar tu mensaje.")
        except Exception:
            pass
        raise ApplicationHandlerStop
        return ConversationHandler.END

    if target_chat_id and target_thread_id:
        user_info = user.full_name
        if user.username:
            user_info += f" (@{user.username})"
        # Enviar sin incluir el ID del usuario
        fwd_msg = f"ℹ️ **Nueva {action_type.capitalize()} de {user_info}**:\n\n{user_text}"
        try:
            await context.bot.send_message(
                chat_id=target_chat_id,
                message_thread_id=target_thread_id,
                text=fwd_msg,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(
                f"{action_type.capitalize()} de {user.id} enviada correctamente a Grupo {target_chat_id} (Tema: {target_thread_id})"
            )
            try:
                await update.message.reply_text(
                    f"✅ ¡Tu {action_type} ha sido enviada correctamente! Gracias."
                )
                logger.info(f"Mensaje de confirmación enviado a {user.id}")
            except Exception as e:
                logger.error(f"Error enviando mensaje de confirmación a {user.id}: {e}")
        except TelegramError as e:
            logger.error(
                f"Error de Telegram API enviando {action_type} de {user.id}: {e}",
                exc_info=False
            )
            try:
                await update.message.reply_text(
                    f"❌ Hubo un problema al enviar tu {action_type}."
                )
            except Exception as e:
                logger.error(f"Error enviando mensaje de fallo a {user.id}: {e}")
        except Exception as e:
            logger.error(
                f"Excepción inesperada enviando {action_type} de {user.id}: {e}",
                exc_info=True
            )
            try:
                await update.message.reply_text(
                    f"❌ Ha ocurrido un error inesperado al procesar tu {action_type}."
                )
            except Exception:
                pass
    else:
        logger.error(f"Destino inválido para {action_type} de {user.id}.")
        try:
            await update.message.reply_text("❌ Error interno: destino no válido.")
        except Exception:
            pass

    raise ApplicationHandlerStop
    return ConversationHandler.END

# --- Handler para /cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or chat.type != 'private':
        return ConversationHandler.END

    logger.info(f"Usuario {user.id} ejecutó /cancel.")
    context.user_data.clear()
    try:
        await update.message.reply_text("Operación cancelada. Puedes empezar de nuevo usando los botones del grupo.")
    except Exception as e:
        logger.error(f"Error enviando mensaje de cancelación a {user.id}: {e}")
    raise ApplicationHandlerStop
    return ConversationHandler.END

# --- Handler para Mensajes Inesperados ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not chat or chat.type != 'private' or not update.message or not update.message.text:
        return
    if 'action_type' in context.user_data:
        return
    keyboard = [
        [InlineKeyboardButton("Ir al tema de Consulta", url=f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_CONSULTAS_COMITE}")],
        [InlineKeyboardButton("Ir al tema de Sugerencia", url=f"https://t.me/c/{get_short_committee_id()}/{TEMA_BOTON_SUGERENCIAS_COMITE}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        "⚠️ Ya has enviado tu consulta o sugerencia.\n\n"
        "Si deseas enviar otra, por favor, pulsa uno de los botones para iniciar un nuevo ciclo."
    )
    try:
        await update.message.reply_text(mensaje, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error enviando mensaje de redirección a {user.id}: {e}")

# --- Configuración y Ejecución Principal ---
def main() -> None:
    if not validar_variables():
        logger.critical("--- BOT DETENIDO: ERRORES CRÍTICOS EN LA CONFIGURACIÓN ---")
        return

    logger.info("--- Configurando la aplicación del bot ---")
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_handler, filters=filters.ChatType.PRIVATE)],
        states={
            TYPING_REPLY: [
                MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel, filters=filters.ChatType.PRIVATE),
            CommandHandler('start', start_handler, filters=filters.ChatType.PRIVATE)
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
        name="consulta_sugerencia_conv",
        persistent=False
    )

    application.add_handler(conv_handler, group=0)
    application.add_handler(CommandHandler("postbotones", post_buttons_command, filters=filters.ChatType.PRIVATE), group=1)
    application.add_handler(CommandHandler("documentacion", documentacion_command, filters=filters.ChatType.PRIVATE), group=1)
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_unexpected_message), group=2)

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
