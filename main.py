import os
import logging
import re

# --- Imports Limpios ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    ConversationHandler,  # <-- Importar directamente
    MessageHandler,
    filters,
    ContextTypes,
    ApplicationHandlerStop  # <-- Para detener la propagación de updates
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
TEMA_BOTON_CONSULTAS_COMITE = 272
TEMA_BOTON_SUGERENCIAS_COMITE = 291
GRUPO_EXTERNO_ID = -1002433074372  # ID del chat donde se envían las consultas/sugerencias
TEMA_CONSULTAS_EXTERNO = 69         # ID del tema para consultas en el grupo externo
TEMA_SUGERENCIAS_EXTERNO = 71       # ID del tema para sugerencias en el grupo externo

# --- Validación de Variables de Entorno ---
def validar_variables():
    """Valida las variables de entorno necesarias."""
    global TOKEN, GRUPO_ID, BOT_USERNAME, GROUP_LINK
    try:
        TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
        if not TOKEN or ":" not in TOKEN:
            raise ValueError("Token inválido")
        grupo_id_raw = os.environ["GROUP_ID"].strip()  # Grupo donde se postean los BOTONES iniciales
        GRUPO_ID = int(re.sub(r"[^-\d]", "", grupo_id_raw))
        if not (GRUPO_ID < -100000000000):
            logger.warning(f"GROUP_ID ({GRUPO_ID}) inusual (esperado ID de supergrupo).")
        BOT_USERNAME = os.environ["BOT_USERNAME"].strip().lstrip('@')
        if not BOT_USERNAME:
            raise ValueError("BOT_USERNAME vacío")
        GROUP_LINK = os.environ.get("GROUP_LINK", "").strip() or None
        if GROUP_LINK and not GROUP_LINK.startswith("https://t.me/"):
            logger.warning("GROUP_LINK inválido.")
            GROUP_LINK = None

        # Log de IDs y Temas
        logger.info(f"GRUPO_ID (Comité - donde postear botones): {GRUPO_ID}")
        logger.info(f"TEMA_BOTON_CONSULTAS_COMITE: {TEMA_BOTON_CONSULTAS_COMITE}")
        logger.info(f"TEMA_BOTON_SUGERENCIAS_COMITE: {TEMA_BOTON_SUGERENCIAS_COMITE}")
        logger.info(f"GRUPO_EXTERNO_ID (Destino mensajes): {GRUPO_EXTERNO_ID}")
        logger.info(f"TEMA_CONSULTAS_EXTERNO: {TEMA_CONSULTAS_EXTERNO}")
        logger.info(f"TEMA_SUGERENCIAS_EXTERNO: {TEMA_SUGERENCIAS_EXTERNO}")
        logger.info(f"BOT_USERNAME: @{BOT_USERNAME}")
        if GROUP_LINK:
            logger.info(f"GROUP_LINK: {GROUP_LINK}")

        # Validaciones adicionales
        if not isinstance(TEMA_BOTON_CONSULTAS_COMITE, int) or TEMA_BOTON_CONSULTAS_COMITE <= 0:
            logger.warning(f"TEMA_BOTON_CONSULTAS_COMITE ({TEMA_BOTON_CONSULTAS_COMITE}) inválido.")
        if not isinstance(TEMA_BOTON_SUGERENCIAS_COMITE, int) or TEMA_BOTON_SUGERENCIAS_COMITE <= 0:
            logger.warning(f"TEMA_BOTON_SUGERENCIAS_COMITE ({TEMA_BOTON_SUGERENCIAS_COMITE}) inválido.")
        if not isinstance(GRUPO_EXTERNO_ID, int) or not (GRUPO_EXTERNO_ID < -100000000000):
            logger.warning(f"GRUPO_EXTERNO_ID ({GRUPO_EXTERNO_ID}) parece inválido (esperado ID de supergrupo).")
        if not isinstance(TEMA_CONSULTAS_EXTERNO, int) or TEMA_CONSULTAS_EXTERNO <= 0:
            logger.warning(f"TEMA_CONSULTAS_EXTERNO ({TEMA_CONSULTAS_EXTERNO}) inválido.")
        if not isinstance(TEMA_SUGERENCIAS_EXTERNO, int) or TEMA_SUGERENCIAS_EXTERNO <= 0:
            logger.warning(f"TEMA_SUGERENCIAS_EXTERNO ({TEMA_SUGERENCIAS_EXTERNO}) inválido.")

        logger.info("✅ Variables validadas correctamente")
        return True
    except KeyError as e:
        logger.critical(f"❌ Falta variable de entorno: {e}")
        return False
    except ValueError as e:
        logger.critical(f"❌ Error de configuración (valor inválido): {e}")
        return False
    except Exception as e:
        logger.critical(f"❌ Error de configuración inesperado: {e}", exc_info=True)
        return False

# --- Función para Enviar Botones Iniciales ---
async def post_initial_buttons(context: CallbackContext) -> bool:
    """ Envía los mensajes iniciales con botones URL al grupo principal (Comité). """
    if not BOT_USERNAME or not GRUPO_ID or GRUPO_ID >= 0:
        logger.error("Faltan BOT_USERNAME o GRUPO_ID (inválido) para postear botones.")
        return False
    if TEMA_BOTON_CONSULTAS_COMITE <= 0 or TEMA_BOTON_SUGERENCIAS_COMITE <= 0:
        logger.error("IDs de tema para botones son inválidos.")
        return False

    success_count = 0
    # Botón de Consultas
    msg_con = ("Pulsa aquí si tienes alguna consulta sobre permisos, bolsa de horas, excedencias, etc. Tu mensaje será privado y solo se permite enviar uno por vez.")
    url_con = f"https://t.me/{BOT_USERNAME}?start=iniciar_consulta"
    kb_con = [[InlineKeyboardButton("Iniciar Consulta 🙋‍♂️", url=url_con)]]
    markup_con = InlineKeyboardMarkup(kb_con)
    try:
        await context.bot.send_message(chat_id=GRUPO_ID, message_thread_id=TEMA_BOTON_CONSULTAS_COMITE, text=msg_con, reply_markup=markup_con)
        logger.info(f"Botón de Consulta enviado al Grupo {GRUPO_ID}, Tema {TEMA_BOTON_CONSULTAS_COMITE}")
        success_count += 1
    except TelegramError as e:
        logger.error(f"Error enviando Botón Consulta a G:{GRUPO_ID} T:{TEMA_BOTON_CONSULTAS_COMITE}: {e}", exc_info=False)
    except Exception as e:
        logger.error(f"Excepción inesperada enviando Botón Consulta a G:{GRUPO_ID} T:{TEMA_BOTON_CONSULTAS_COMITE}: {e}", exc_info=True)

    # Botón de Sugerencias
    msg_sug = ("Pulsa aquí si tienes alguna sugerencia sobre el funcionamiento del grupo, el comité, etc. Tu mensaje será privado y solo se permite enviar uno por vez.")
    url_sug = f"https://t.me/{BOT_USERNAME}?start=iniciar_sugerencia"
    kb_sug = [[InlineKeyboardButton("Iniciar Sugerencia 💡", url=url_sug)]]
    markup_sug = InlineKeyboardMarkup(kb_sug)
    try:
        await context.bot.send_message(chat_id=GRUPO_ID, message_thread_id=TEMA_BOTON_SUGERENCIAS_COMITE, text=msg_sug, reply_markup=markup_sug)
        logger.info(f"Botón de Sugerencia enviado al Grupo {GRUPO_ID}, Tema {TEMA_BOTON_SUGERENCIAS_COMITE}")
        success_count += 1
    except TelegramError as e:
        logger.error(f"Error enviando Botón Sugerencia a G:{GRUPO_ID} T:{TEMA_BOTON_SUGERENCIAS_COMITE}: {e}", exc_info=False)
    except Exception as e:
        logger.error(f"Excepción inesperada enviando Botón Sugerencia a G:{GRUPO_ID} T:{TEMA_BOTON_SUGERENCIAS_COMITE}: {e}", exc_info=True)

    return success_count > 0

# --- Comando para Postear Botones ---
async def post_buttons_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Comando /postbotones para uso del administrador en chat privado. """
    user = update.effective_user
    chat = update.effective_chat
    if not chat or chat.type != 'private':
        logger.warning(f"Intento de usar /postbotones fuera de chat privado por {user.id if user else '?'}")
        return

    logger.info(f"Comando /postbotones recibido de {user.id}. Ejecutando post_initial_buttons...")
    await update.message.reply_text("Intentando publicar/actualizar botones en el grupo Comité...")
    try:
        success = await post_initial_buttons(context)
    except Exception as e:
        logger.error(f"Excepción llamando a post_initial_buttons desde comando por {user.id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Ocurrió un error inesperado al intentar postear los botones.")
        raise ApplicationHandlerStop

    if success:
        await update.message.reply_text("✅ ¡Botones posteados/actualizados con éxito!")
    else:
        await update.message.reply_text("⚠️ No se pudieron enviar uno o ambos botones. Revisa los logs del bot para más detalles.")
    raise ApplicationHandlerStop

# --- Handler para /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """
    Manejador del comando /start.
    Si viene con payload (iniciar_consulta o iniciar_sugerencia), se inicia el flujo.
    """
    user = update.effective_user
    chat = update.effective_chat
    args = context.args

    logger.info(f"/start de {user.id if user else '?'} en chat:{chat.id if chat else '?'} (tipo: {chat.type if chat else '?'}). Args: {args}")

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
                logger.info(f"Payload '{payload}' válido recibido de {user.id}. Iniciando flujo para '{action_type}'.")
                context.user_data['action_type'] = action_type
                prompt = f"¡Hola {user.first_name}! Por favor, escribe ahora tu {action_type} en un único mensaje."
                await update.message.reply_text(prompt)
                # Se retorna el estado para que el primer mensaje se capture en receive_text
                return TYPING_REPLY
            else:
                logger.warning(f"Payload desconocido '{payload}' recibido de {user.id}. Ignorando.")
                await update.message.reply_text("Parece que el enlace que has usado no es válido o ha expirado.")
                context.user_data.clear()
                raise ApplicationHandlerStop
                return ConversationHandler.END
        else:
            # /start sin payload
            logger.info(f"/start simple (sin payload) de {user.id}. Enviando saludo genérico.")
            await update.message.reply_text(
                f"¡Hola {user.first_name}! Por favor, escribe ahora tu sugerencia en un único mensaje.\n - Recuerda que las sugerencias(consultas) solo las pueden ver los miembros del comité. \n - Recibirás una respuesta en la mayor brevedad posible."
            )
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
    Se procesa, se envía al grupo externo y se termina la conversación.
    """
    user = update.effective_user
    message = update.message
    chat = update.effective_chat

    if not user or not message or not message.text or not chat or chat.type != 'private':
        logger.warning(f"receive_text recibió un update inesperado o inválido. User: {user.id if user else '?'}")
        context.user_data.clear()
        raise ApplicationHandlerStop
        return ConversationHandler.END

    user_text = message.text
    action_type = context.user_data.pop('action_type', None)
    if not action_type:
        # Se reemplaza el mensaje de error por uno que invite a reiniciar el flujo mediante botones.
        keyboard = [
            [InlineKeyboardButton("Iniciar Consulta 🙋‍♂️", url=f"https://t.me/{BOT_USERNAME}?start=iniciar_consulta")],
            [InlineKeyboardButton("Iniciar Sugerencia 💡", url=f"https://t.me/{BOT_USERNAME}?start=iniciar_sugerencia")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await update.message.reply_text(
                "Si quieres hacer otra consulta o sugerencia, presiona los botones que hay a continuación:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error enviando mensaje de reinicio a {user.id}: {e}")
        raise ApplicationHandlerStop
        return ConversationHandler.END

    logger.info(f"Procesando '{action_type}' de {user.id}. Texto: {user_text[:50]}...")

    # Validación para consultas (solo aplica para consultas)
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
                logger.warning(f"Consulta de {user.id} rechazada. Contiene tema prohibido: '{topic_name}'.")
                try:
                    await update.message.reply_text(
                        f"❌ Tu consulta sobre '{topic_name}' no puede ser procesada a través de este bot.\n"
                        "Por favor, revisa la información disponible en el grupo o la documentación oficial."
                    )
                except Exception as e:
                    logger.error(f"Error enviando mensaje de rechazo a {user.id}: {e}")
                raise ApplicationHandlerStop
                return ConversationHandler.END

    # Determinar destino según la acción
    if action_type == 'consulta':
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_CONSULTAS_EXTERNO
    elif action_type == 'sugerencia':
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_SUGERENCIAS_EXTERNO
    else:
        logger.error(f"Valor inesperado para 'action_type' ({action_type}) en {user.id}.")
        try:
            await update.message.reply_text("❌ Ha ocurrido un error interno inesperado. No se ha podido procesar tu mensaje.")
        except Exception:
            pass
        raise ApplicationHandlerStop
        return ConversationHandler.END

    if target_chat_id and target_thread_id:
        user_info = user.full_name
        if user.username:
            user_info += f" (@{user.username})"
        fwd_msg = f"ℹ️ **Nueva {action_type.capitalize()} de {user_info}** (ID: {user.id}):\n\n{user_text}"
        try:
            await context.bot.send_message(
                chat_id=target_chat_id,
                message_thread_id=target_thread_id,
                text=fwd_msg,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"{action_type.capitalize()} de {user.id} enviada correctamente a Grupo {target_chat_id} (Tema: {target_thread_id})")
            try:
                await update.message.reply_text(f"✅ ¡Tu {action_type} ha sido enviada correctamente! Gracias.")
                logger.info(f"Mensaje de confirmación enviado a {user.id}")
            except Exception as e:
                logger.error(f"Error enviando mensaje de confirmación a {user.id}: {e}")
        except TelegramError as e:
            logger.error(f"Error de Telegram API enviando {action_type} de {user.id} a G:{target_chat_id} T:{target_thread_id}: {e}", exc_info=False)
            try:
                await update.message.reply_text(f"❌ Hubo un problema al enviar tu {action_type}.")
            except Exception as e:
                logger.error(f"Error enviando mensaje de fallo a {user.id}: {e}")
        except Exception as e:
            logger.error(f"Excepción inesperada enviando {action_type} de {user.id}: {e}", exc_info=True)
            try:
                await update.message.reply_text(f"❌ Ha ocurrido un error inesperado al procesar tu {action_type}.")
            except Exception:
                pass
    else:
        logger.error(f"Destino inválido para {action_type} de {user.id}.")
        try:
            await update.message.reply_text("❌ Error interno: destino no válido.")
        except Exception:
            pass

    # Se termina la conversación después del primer mensaje válido.
    raise ApplicationHandlerStop
    return ConversationHandler.END

# --- Handler para /cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ Cancela la conversación activa si la hay. """
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or chat.type != 'private':
        return ConversationHandler.END

    logger.info(f"Usuario {user.id} ejecutó /cancel.")
    was_in_conversation = bool(context.user_data)
    context.user_data.clear()

    msg = 'Operación cancelada. Puedes empezar de nuevo usando los botones del grupo.' if was_in_conversation else 'No hay ninguna operación activa para cancelar.'
    try:
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Error enviando mensaje de cancelación a {user.id}: {e}")

    raise ApplicationHandlerStop
    return ConversationHandler.END

# --- Handler para Mensajes Inesperados ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Si se recibe un mensaje fuera de una conversación activa (o tras haber enviado la consulta/sugerencia),
    se informa al usuario que para enviar una nueva consulta o sugerencia debe pulsar el botón correspondiente.
    """
    user = update.effective_user
    chat = update.effective_chat

    # Procesamos solo en chat privado y si hay texto
    if not chat or chat.type != 'private' or not update.message or not update.message.text:
        return

    # Si se encuentra 'action_type' activo, es parte de la conversación; no se actúa.
    if 'action_type' in context.user_data:
        return

    # Enviar mensaje informativo con botones para reiniciar el flujo.
    url_consulta = f"https://t.me/{BOT_USERNAME}?start=iniciar_consulta"
    url_sugerencia = f"https://t.me/{BOT_USERNAME}?start=iniciar_sugerencia"
    keyboard = [
        [InlineKeyboardButton("Iniciar Consulta 🙋‍♂️", url=url_consulta)],
        [InlineKeyboardButton("Iniciar Sugerencia 💡", url=url_sugerencia)]
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
    """ Configura y ejecuta el bot de Telegram. """
    if not validar_variables():
        logger.critical("--- BOT DETENIDO: ERRORES CRÍTICOS EN LA CONFIGURACIÓN ---")
        return

    logger.info("--- Configurando la aplicación del bot ---")
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start, filters=filters.ChatType.PRIVATE)],
        states={
            TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel, filters=filters.ChatType.PRIVATE),
            CommandHandler('start', start, filters=filters.ChatType.PRIVATE)
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
        name="consulta_sugerencia_conv",
        persistent=False
    )

    # Registro de handlers:
    application.add_handler(conv_handler, group=0)
    application.add_handler(CommandHandler("postbotones", post_buttons_command, filters=filters.ChatType.PRIVATE), group=1)
    # Handler para mensajes inesperados en privado
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
