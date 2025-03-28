import os
import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext, # Mantener por si se usa en post_initial_buttons
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes, # Usar este para type hints en handlers
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
# Reducir verbosidad de logs no esenciales
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
# !! Asegúrate de que estos IDs sean correctos para tu GRUPO_ID !!
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
        if not TOKEN or ":" not in TOKEN:
            raise ValueError("Formato de TELEGRAM_TOKEN inválido")

        grupo_id_raw = os.environ["GROUP_ID"].strip()
        grupo_id_limpio = re.sub(r"[^-\d]", "", grupo_id_raw)
        GRUPO_ID = int(grupo_id_limpio)
        # Validación simple para ID de grupo/supergrupo
        if not (GRUPO_ID < -100000000000):
             logger.warning(f"El GROUP_ID ({GRUPO_ID}) parece inusual (¿quizás no es un supergrupo?), pero se continuará.")

        BOT_USERNAME = os.environ["BOT_USERNAME"].strip().lstrip('@')
        if not BOT_USERNAME:
            raise ValueError("BOT_USERNAME es obligatorio y no puede estar vacío")

        # GROUP_LINK es opcional
        GROUP_LINK = os.environ.get("GROUP_LINK", "").strip()
        if GROUP_LINK and not GROUP_LINK.startswith("https://t.me/"):
            logger.warning("GROUP_LINK proporcionado pero no parece un enlace válido de Telegram.")
            GROUP_LINK = None # Invalidar si el formato es incorrecto

        logger.info(f"GRUPO_ID (Comité): {GRUPO_ID}")
        logger.info(f"TEMA_BOTON_CONSULTAS_COMITE: {TEMA_BOTON_CONSULTAS_COMITE}")
        logger.info(f"TEMA_BOTON_SUGERENCIAS_COMITE: {TEMA_BOTON_SUGERENCIAS_COMITE}")
        logger.info(f"GRUPO_EXTERNO_ID: {GRUPO_EXTERNO_ID}")
        logger.info(f"TEMA_CONSULTAS_EXTERNO: {TEMA_CONSULTAS_EXTERNO}")
        logger.info(f"TEMA_SUGERENCIAS_EXTERNO: {TEMA_SUGERENCIAS_EXTERNO}")
        logger.info(f"BOT_USERNAME: @{BOT_USERNAME}")
        if GROUP_LINK: logger.info(f"GROUP_LINK: {GROUP_LINK}")

        # Verificar IDs de temas externos (opcional pero útil)
        if not isinstance(TEMA_CONSULTAS_EXTERNO, int) or TEMA_CONSULTAS_EXTERNO <= 0:
             logger.warning(f"TEMA_CONSULTAS_EXTERNO ({TEMA_CONSULTAS_EXTERNO}) parece inválido.")
        if not isinstance(TEMA_SUGERENCIAS_EXTERNO, int) or TEMA_SUGERENCIAS_EXTERNO <= 0:
             logger.warning(f"TEMA_SUGERENCIAS_EXTERNO ({TEMA_SUGERENCIAS_EXTERNO}) parece inválido.")


        logger.info("✅ Variables validadas correctamente")
        return True
    except KeyError as e:
        logger.critical(f"❌ Error de configuración: Falta la variable de entorno obligatoria: {str(e)}")
        return False
    except ValueError as e:
         logger.critical(f"❌ Error de configuración: {str(e)}")
         return False
    except Exception as e:
        logger.critical(f"❌ Error de configuración inesperado: {str(e)}", exc_info=True)
        return False

# --- Función para Enviar Botones Iniciales ---
async def post_initial_buttons(context: CallbackContext) -> bool:
    """
    Envía los mensajes iniciales con botones URL y textos actualizados
    a los temas del comité. Devuelve True si ambos intentos fueron exitosos (sin errores fatales).
    """
    if not BOT_USERNAME: logger.error("post_initial_buttons: BOT_USERNAME no configurado."); return False
    if not GRUPO_ID: logger.error("post_initial_buttons: GRUPO_ID no configurado."); return False
    if not isinstance(TEMA_BOTON_CONSULTAS_COMITE, int) or TEMA_BOTON_CONSULTAS_COMITE <= 0: logger.error(f"ID de tema inválido para consultas: {TEMA_BOTON_CONSULTAS_COMITE}"); return False
    if not isinstance(TEMA_BOTON_SUGERENCIAS_COMITE, int) or TEMA_BOTON_SUGERENCIAS_COMITE <= 0: logger.error(f"ID de tema inválido para sugerencias: {TEMA_BOTON_SUGERENCIAS_COMITE}"); return False

    success_count = 0

    # 1. Mensaje para Consultas
    mensaje_consulta = (
        "Pulsa el botón si tienes alguna consulta sobre algún tema que no se haya visto en el grupo"
        "(permisos, bolsa de horas, excedencias, etc...). Recuerda que estás consultas son privadas y "
        "solo pueden verlas los miembros del comité. La consulta debe ser enviada en un solo mensaje."
    )
    url_consulta = f"https://t.me/{BOT_USERNAME}?start=iniciar_consulta"
    kb_consulta = [[InlineKeyboardButton("Iniciar Consulta 🙋‍♂️", url=url_consulta)]]
    markup_consulta = InlineKeyboardMarkup(kb_consulta)
    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_BOTON_CONSULTAS_COMITE,
            text=mensaje_consulta,
            reply_markup=markup_consulta
        )
        logger.info(f"Msg botón URL 'Consulta' enviado a GRUPO_ID: {GRUPO_ID}, TEMA: {TEMA_BOTON_CONSULTAS_COMITE}")
        success_count += 1
    except TelegramError as e:
        logger.error(f"Error enviando botón 'Consulta' T:{TEMA_BOTON_CONSULTAS_COMITE}: {e}")
    except Exception as e:
        logger.error(f"Error inesperado enviando botón 'Consulta': {e}", exc_info=True)

    # 2. Mensaje para Sugerencias
    mensaje_sugerencia = (
        "Pulsa el botón si tienes alguna sugerencia para mejorar el grupo o el funcionamiento del comité. "
        "Recuerda que estás sugerencias son privadas y solo pueden verlas los miembros del comité. "
        "La sugerencia debe ser enviada en un solo mensaje."
    )
    url_sugerencia = f"https://t.me/{BOT_USERNAME}?start=iniciar_sugerencia"
    kb_sugerencia = [[InlineKeyboardButton("Iniciar Sugerencia 💡", url=url_sugerencia)]]
    markup_sugerencia = InlineKeyboardMarkup(kb_sugerencia)
    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_BOTON_SUGERENCIAS_COMITE,
            text=mensaje_sugerencia,
            reply_markup=markup_sugerencia
        )
        logger.info(f"Msg botón URL 'Sugerencia' enviado a GRUPO_ID: {GRUPO_ID}, TEMA: {TEMA_BOTON_SUGERENCIAS_COMITE}")
        success_count += 1
    except TelegramError as e:
        logger.error(f"Error enviando botón 'Sugerencia' T:{TEMA_BOTON_SUGERENCIAS_COMITE}: {e}")
    except Exception as e:
        logger.error(f"Error inesperado enviando botón 'Sugerencia': {e}", exc_info=True)

    # Devolver True si al menos uno se envió (o si ambos lo hicieron)
    # Podrías cambiarlo a `return success_count == 2` si quieres éxito total
    return success_count > 0

# --- Comando para Postear Botones (Privado, sin check de admin) ---
async def post_buttons_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /postbotones para publicar los mensajes con botones.
    CUALQUIER usuario puede ejecutarlo en CHAT PRIVADO con el bot.
    """
    user = update.effective_user
    chat = update.effective_chat

    if not chat or chat.type != 'private':
        logger.warning(f"/postbotones ignorado: no en privado (chat_id: {chat.id if chat else '?'}).")
        return

    logger.info(f"/postbotones recibido en privado de {user.id} ({user.full_name}). Ejecutando...")
    await update.message.reply_text("Recibido. Intentando publicar/actualizar botones en los temas del grupo del comité...")
    try:
        success = await post_initial_buttons(context)
        if success:
            await update.message.reply_text("✅ ¡Hecho! Los botones de consulta y sugerencia deberían estar publicados/actualizados en sus temas.")
        else:
            await update.message.reply_text("⚠️ Se intentó publicar los botones, pero ocurrió un error al enviar uno o ambos mensajes. Revisa los logs del bot.")
    except Exception as e:
        logger.error(f"Error inesperado durante post_initial_buttons llamado por {user.id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Ocurrió un error inesperado al intentar publicar los botones.")


# --- Handler para /start (Entrada a la Conversación) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """
    Manejador del comando /start.
    - Inicia conversación si viene con payload válido en privado.
    - Saluda si es /start simple en privado.
    - Ignora en grupos.
    """
    user = update.effective_user
    chat = update.effective_chat
    args = context.args # Payload del deep link

    # Log detallado
    start_context = f"chat {chat.id} ({chat.type})" if chat else "chat desconocido"
    logger.info(f"Comando /start de {user.id} ({user.full_name}) en {start_context}. Args: {args}")

    # Caso 1: Privado y con payload (desde botón URL)
    if chat and chat.type == "private" and args:
        payload = args[0]
        action_type = None
        if payload == "iniciar_consulta":
            action_type = "consulta"
        elif payload == "iniciar_sugerencia":
            action_type = "sugerencia"

        if action_type:
            # Limpiar posible estado anterior por si acaso (reentrada)
            context.user_data.clear()
            logger.info(f"Payload '{payload}' válido de {user.id}. Iniciando flujo de {action_type}.")
            context.user_data['action_type'] = action_type # Guardar qué se está haciendo
            prompt_message = f"¡Hola {user.first_name}! Has iniciado el proceso para enviar una {action_type}.\n\nPor favor, escribe tu mensaje ahora en un único texto."
            await update.message.reply_text(prompt_message)
            return TYPING_REPLY # Pasar al estado de espera de texto
        else:
            # Payload desconocido
            logger.warning(f"Payload desconocido '{payload}' recibido de {user.id}.")
            await update.message.reply_text("Parece que has usado un enlace inválido o caducado. Si querías enviar algo, por favor, vuelve al grupo del comité y usa el botón correcto.")
            context.user_data.clear()
            return ConversationHandler.END # No iniciar conversación

    # Caso 2: Privado y SIN payload
    elif chat and chat.type == "private":
        logger.info(f"/start simple recibido en privado de {user.id}.")
        await update.message.reply_text(f"¡Hola {user.first_name}! Soy el bot del comité.\nPara enviar consultas o sugerencias, por favor, usa los botones dedicados en los temas correspondientes del grupo del comité.")
        context.user_data.clear() # Asegurarse de limpiar por si acaso
        return ConversationHandler.END # No iniciar conversación

    # Caso 3: En grupo o canal
    elif chat and chat.type in ["group", "supergroup", "channel"]:
         logger.info(f"/start recibido en {chat.type} {chat.id}. Ignorando.")
         # No enviar mensaje para no ensuciar el grupo
         return None # No es parte de la conversación

    # Otros casos (raro)
    return ConversationHandler.END

# --- MODIFICADO: receive_text para ser más robusto al finalizar ---
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Recibe el texto en privado. Si es consulta, valida palabras clave.
    Si es válido (o es sugerencia), lo envía al grupo/tema externo apropiado.
    Confirma en privado y finaliza la conversación de forma definitiva.
    """
    user = update.effective_user
    message = update.message
    if not message or not message.text:
        logger.warning(f"Update sin texto recibido en estado TYPING_REPLY de {user.id}. Ignorando.")
        return TYPING_REPLY

    user_text = message.text
    # Usar pop para obtener Y eliminar el estado, asegurando que no se reutilice accidentalmente
    action_type = context.user_data.pop('action_type', None)

    if not action_type:
        logger.warning(f"receive_text llamado sin action_type en user_data (pop) para {user.id}.")
        # No enviar mensaje aquí si ya no hay estado, podría ser confuso
        return ConversationHandler.END

    logger.info(f"Procesando texto de {user.id} para '{action_type}': {user_text[:100]}...")

    # --- Validación de Palabras Clave (SOLO para consultas) ---
    if action_type == 'consulta':
        # ... (Bloque de validación de palabras clave SIN CAMBIOS) ...
        text_lower = user_text.lower()
        forbidden_keywords_map = {
            "bolsa de horas": "bolsa de horas", "permiso": "permisos",
            "permisos": "permisos", "incapacidad temporal": "incapacidad temporal",
            "baja": "incapacidad temporal", "excedencia": "excedencias",
            "excedencias": "excedencias"
        }
        found_forbidden_topic = None
        for keyword, topic_name in forbidden_keywords_map.items():
            if keyword in text_lower: found_forbidden_topic = topic_name; break
        if found_forbidden_topic:
            logger.warning(f"Consulta de {user.id} rechazada: '{found_forbidden_topic}'")
            error_message = (f"❌ Tu consulta sobre '{found_forbidden_topic}' no se procesa por aquí.\n\nConsulta la info en el grupo/documentación. Si tienes dudas específicas no resueltas, replantea sin mencionar '{found_forbidden_topic}'.")
            try:
                 await update.message.reply_text(error_message)
            except Exception as e_reply:
                 logger.error(f"Error enviando msg rechazo a {user.id}: {e_reply}")
            # context.user_data ya se limpió con pop
            return ConversationHandler.END
    # --- Fin Validación ---

    # Determinar destino EXTERNO
    if action_type == 'consulta': target_chat_id = GRUPO_EXTERNO_ID; target_thread_id = TEMA_CONSULTAS_EXTERNO
    elif action_type == 'sugerencia': target_chat_id = GRUPO_EXTERNO_ID; target_thread_id = TEMA_SUGERENCIAS_EXTERNO
    else: logger.error(f"Tipo acción desconocido '{action_type}' en receive_text {user.id}"); await update.message.reply_text("Error interno."); return ConversationHandler.END # Limpiar user_data no es necesario (se hizo con pop)

    # Formatear y enviar
    user_info = f"{user.full_name}" + (f" (@{user.username})" if user.username else "")
    forward_message = f"ℹ️ **Nueva {action_type.capitalize()} de {user_info}**:\n\n{user_text}"
    send_success = False
    try:
        await context.bot.send_message(chat_id=target_chat_id, message_thread_id=target_thread_id, text=forward_message, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"{action_type.capitalize()} de {user_info} (ID: {user.id}) enviada a {target_chat_id} (T:{target_thread_id})")
        send_success = True
    except TelegramError as e: logger.error(f"Error TG enviando {action_type} de {user.id}: {e}")
    except Exception as e: logger.error(f"Error Inesperado enviando {action_type} de {user.id}: {e}", exc_info=True)

    # Confirmar al usuario DESPUÉS de intentar enviar
    if send_success:
        try:
            await update.message.reply_text(f"✅ ¡Tu {action_type} ha sido enviada correctamente! Gracias.")
            logger.info(f"Confirmación enviada en privado a {user.id}")
        except Exception as e_confirm:
             logger.error(f"Error enviando confirmación a {user.id}: {e_confirm}")
    else:
        try:
            await update.message.reply_text(f"❌ Hubo un error al enviar tu {action_type} al grupo externo. Por favor, contacta a un administrador.")
        except Exception as e_fail_confirm:
             logger.error(f"Error enviando msg de fallo a {user.id}: {e_fail_confirm}")


    # Asegurarse de que user_data esté limpio (aunque pop ya lo hizo)
    context.user_data.clear()

    # Indicar que la conversación ha terminado definitivamente para este update
    return ConversationHandler.END
    # --- Fin Validación ---

    # Determinar destino EXTERNO
    if action_type == 'consulta':
        target_chat_id = GRUPO_EXTERNO_ID; target_thread_id = TEMA_CONSULTAS_EXTERNO
    elif action_type == 'sugerencia':
        target_chat_id = GRUPO_EXTERNO_ID; target_thread_id = TEMA_SUGERENCIAS_EXTERNO
    else:
        logger.error(f"Tipo acción desconocido '{action_type}' en receive_text {user.id}"); await update.message.reply_text("Error interno."); context.user_data.clear(); return ConversationHandler.END

    # Formatear mensaje para el grupo externo (sin ID)
    user_info = f"{user.full_name}" + (f" (@{user.username})" if user.username else "")
    forward_message = f"ℹ️ **Nueva {action_type.capitalize()} de {user_info}**:\n\n{user_text}"

    try:
        await context.bot.send_message(
            chat_id=target_chat_id, message_thread_id=target_thread_id,
            text=forward_message, parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"{action_type.capitalize()} de {user_info} (ID: {user.id}) enviada a {target_chat_id} (T:{target_thread_id})")
        await update.message.reply_text(f"✅ ¡Tu {action_type} ha sido enviada correctamente! Gracias.")
        logger.info(f"Confirmación enviada en privado a {user.id}")
    except TelegramError as e:
        logger.error(f"Error de Telegram enviando la {action_type} de {user.id} al grupo externo: {e}")
        await update.message.reply_text(f"❌ Hubo un error al enviar tu {action_type} al grupo externo ({e}). Por favor, contacta a un administrador si el problema persiste.")
    except Exception as e:
        logger.error(f"Error inesperado enviando la {action_type} de {user.id}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Hubo un error inesperado al enviar tu {action_type}. Por favor, contacta a un administrador.")

    finally:
        context.user_data.clear() # Limpiar siempre al finalizar
        return ConversationHandler.END # Terminar la conversación

# --- Handler para /cancel (Fallback de la Conversación) ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación activa."""
    user = update.effective_user
    logger.info(f"Usuario {user.id} ({user.full_name}) canceló la conversación.")
    # Verificar si realmente estaba en una conversación
    if context.user_data.get('action_type'):
        await update.message.reply_text('Operación cancelada. Puedes iniciar una nueva desde el grupo del comité si lo deseas.')
    else:
        # Si no estaba en la conversación, simplemente saludar
         await update.message.reply_text('No hay ninguna operación activa para cancelar. Usa los botones del grupo para iniciar.')

    context.user_data.clear() # Limpiar en cualquier caso
    return ConversationHandler.END

# --- Handler para Mensajes Inesperados en Privado ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde a mensajes de texto inesperados en privado."""
    user = update.effective_user
    chat = update.effective_chat

    # Doble check por si acaso, aunque el filtro ya lo hace
    if not chat or chat.type != 'private': return
    if not update.message or not update.message.text: return # Ignorar si no es texto

    logger.info(f"Mensaje inesperado de {user.id} en privado: {update.message.text[:50]}...")

    if not GRUPO_ID or GRUPO_ID >= 0:
        logger.error("handle_unexpected_message: GRUPO_ID inválido para generar enlaces.")
        await update.message.reply_text("Lo siento, no entiendo. Usa los botones en el grupo del comité para enviar consultas/sugerencias.")
        return

    try:
        short_group_id = str(GRUPO_ID).replace("-100", "", 1)
        url_tema_consultas = f"https://t.me/c/{short_group_id}/{TEMA_BOTON_CONSULTAS_COMITE}"
        url_tema_sugerencias = f"https://t.me/c/{short_group_id}/{TEMA_BOTON_SUGERENCIAS_COMITE}"

        texto_respuesta = (
            "Hola 👋 Parece que has escrito directamente en el chat. \n\n"
            "Para enviar una consulta o una sugerencia, por favor, utiliza los botones dedicados "
            "que se encuentran en los siguientes temas del grupo del comité:"
        )
        keyboard = [
            [InlineKeyboardButton("Ir a Consultas 🤔", url=url_tema_consultas)],
            [InlineKeyboardButton("Ir a Sugerencias ✨", url=url_tema_sugerencias)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(texto_respuesta, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error al generar respuesta inesperada para {user.id}: {e}", exc_info=True)
        await update.message.reply_text("Lo siento, no entiendo. Usa los botones en el grupo del comité.")


# --- Configuración y Ejecución Principal ---
def main() -> None:
    """Configura y ejecuta el bot."""
    if not validar_variables():
       logger.critical("--- BOT DETENIDO DEBIDO A ERRORES DE CONFIGURACIÓN ---")
       return # Detener si la validación falla

    application = Application.builder().token(TOKEN).build()

    # --- Conversation Handler ---
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start, filters=filters.ChatType.PRIVATE)],
        states={
            TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel, filters=filters.ChatType.PRIVATE),
            CommandHandler('start', start, filters=filters.ChatType.PRIVATE) # Permite reiniciar con /start
        ],
        allow_reentry=True, # Importante para que /start funcione como reinicio
        per_user=True,
        per_chat=True, # Estado ligado al chat privado
    )

    # --- Registro de Handlers por Prioridad ---
    # Grupo 0: Conversación (máxima prioridad para mensajes relevantes)
    application.add_handler(conv_handler, group=0)

    # Grupo 1: Comandos específicos fuera de la conversación
    application.add_handler(CommandHandler("postbotones", post_buttons_command, filters=filters.ChatType.PRIVATE), group=1)
    # Aquí irían otros comandos como /help, etc. si los hubiera

    # Grupo 2: Mensajes de texto genéricos en privado (fallback)
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
        handle_unexpected_message
    ), group=2)

    # Ya no se necesita un handler genérico para /start en grupos

    logger.info("--- Iniciando Polling del Bot ---")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
         logger.critical(f"--- ERROR CRÍTICO DURANTE POLLING ---: {e}", exc_info=True)
    finally:
        logger.info("--- Bot Detenido ---")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # Captura errores fatales que puedan ocurrir ANTES de iniciar el polling
        logger.critical(f"Error fatal al inicializar el bot: {e}", exc_info=True)
