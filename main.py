import os
import logging
import re

# --- Imports Limpios ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    ConversationHandler, # <-- Importar directamente
    MessageHandler,
    filters,
    ContextTypes,
    ApplicationHandlerStop # <-- Mantener importación por si acaso
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
# Asegúrate de que estos IDs de tema sean correctos para tu grupo principal
TEMA_BOTON_CONSULTAS_COMITE = 272
TEMA_BOTON_SUGERENCIAS_COMITE = 291
# Asegúrate de que estos IDs de grupo/tema sean correctos para el grupo externo de destino
GRUPO_EXTERNO_ID = -1002433074372 # ID del chat donde se envían las consultas/sugerencias
TEMA_CONSULTAS_EXTERNO = 69      # ID del tema para consultas en el grupo externo
TEMA_SUGERENCIAS_EXTERNO = 71    # ID del tema para sugerencias en el grupo externo


# --- Validación de Variables de Entorno ---
def validar_variables():
    """Valida las variables de entorno necesarias."""
    global TOKEN, GRUPO_ID, BOT_USERNAME, GROUP_LINK
    try:
        TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
        if not TOKEN or ":" not in TOKEN: raise ValueError("Token inválido")
        grupo_id_raw = os.environ["GROUP_ID"].strip() # Grupo donde se postean los BOTONES iniciales
        GRUPO_ID = int(re.sub(r"[^-\d]", "", grupo_id_raw))
        if not (GRUPO_ID < -100000000000): logger.warning(f"GROUP_ID ({GRUPO_ID}) inusual (esperado ID de supergrupo).")
        BOT_USERNAME = os.environ["BOT_USERNAME"].strip().lstrip('@')
        if not BOT_USERNAME: raise ValueError("BOT_USERNAME vacío")
        GROUP_LINK = os.environ.get("GROUP_LINK", "").strip() or None
        if GROUP_LINK and not GROUP_LINK.startswith("https://t.me/"): logger.warning("GROUP_LINK inválido."); GROUP_LINK = None

        # Log de IDs y Temas
        logger.info(f"GRUPO_ID (Comité - donde postear botones): {GRUPO_ID}")
        logger.info(f"TEMA_BOTON_CONSULTAS_COMITE: {TEMA_BOTON_CONSULTAS_COMITE}")
        logger.info(f"TEMA_BOTON_SUGERENCIAS_COMITE: {TEMA_BOTON_SUGERENCIAS_COMITE}")
        logger.info(f"GRUPO_EXTERNO_ID (Destino mensajes): {GRUPO_EXTERNO_ID}")
        logger.info(f"TEMA_CONSULTAS_EXTERNO: {TEMA_CONSULTAS_EXTERNO}")
        logger.info(f"TEMA_SUGERENCIAS_EXTERNO: {TEMA_SUGERENCIAS_EXTERNO}")
        logger.info(f"BOT_USERNAME: @{BOT_USERNAME}")
        if GROUP_LINK: logger.info(f"GROUP_LINK: {GROUP_LINK}")

        # Validaciones adicionales de tipos y valores
        if not isinstance(TEMA_BOTON_CONSULTAS_COMITE, int) or TEMA_BOTON_CONSULTAS_COMITE <= 0: logger.warning(f"TEMA_BOTON_CONSULTAS_COMITE ({TEMA_BOTON_CONSULTAS_COMITE}) inválido.")
        if not isinstance(TEMA_BOTON_SUGERENCIAS_COMITE, int) or TEMA_BOTON_SUGERENCIAS_COMITE <= 0: logger.warning(f"TEMA_BOTON_SUGERENCIAS_COMITE ({TEMA_BOTON_SUGERENCIAS_COMITE}) inválido.")
        if not isinstance(GRUPO_EXTERNO_ID, int) or not (GRUPO_EXTERNO_ID < -100000000000): logger.warning(f"GRUPO_EXTERNO_ID ({GRUPO_EXTERNO_ID}) parece inválido (esperado ID de supergrupo).")
        if not isinstance(TEMA_CONSULTAS_EXTERNO, int) or TEMA_CONSULTAS_EXTERNO <= 0: logger.warning(f"TEMA_CONSULTAS_EXTERNO ({TEMA_CONSULTAS_EXTERNO}) inválido.")
        if not isinstance(TEMA_SUGERENCIAS_EXTERNO, int) or TEMA_SUGERENCIAS_EXTERNO <= 0: logger.warning(f"TEMA_SUGERENCIAS_EXTERNO ({TEMA_SUGERENCIAS_EXTERNO}) inválido.")

        logger.info("✅ Variables validadas correctamente")
        return True
    except KeyError as e: logger.critical(f"❌ Falta variable de entorno: {e}"); return False
    except ValueError as e: logger.critical(f"❌ Error de configuración (valor inválido): {e}"); return False
    except Exception as e: logger.critical(f"❌ Error de configuración inesperado: {e}", exc_info=True); return False

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
    # Mensaje y botón para Consultas
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

    # Mensaje y botón para Sugerencias
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
    # Asegurar que el comando solo se ejecute en chat privado (por seguridad/simplicidad)
    if not chat or chat.type != 'private':
        logger.warning(f"Intento de usar /postbotones fuera de chat privado por {user.id if user else '?'}")
        return
    # Aquí podrías añadir una verificación del ID del usuario si quieres restringirlo más
    # if user.id != ADMIN_USER_ID:
    #    await update.message.reply_text("No tienes permiso para usar este comando.")
    #    return

    logger.info(f"Comando /postbotones recibido de {user.id}. Ejecutando post_initial_buttons...")
    await update.message.reply_text("Intentando publicar/actualizar botones en el grupo Comité...")
    try:
        success = await post_initial_buttons(context)
    except Exception as e:
        logger.error(f"Excepción llamando a post_initial_buttons desde comando por {user.id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Ocurrió un error inesperado al intentar postear los botones.")
        return

    if success:
        await update.message.reply_text("✅ ¡Botones posteados/actualizados con éxito!")
    else:
        await update.message.reply_text("⚠️ No se pudieron enviar uno o ambos botones. Revisa los logs del bot para más detalles (posibles errores de permisos, IDs incorrectos, etc.).")

# --- Handler para /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """ Manejador del comando /start. Inicia la conversación si viene con payload. """
    user = update.effective_user
    chat = update.effective_chat
    args = context.args

    logger.info(f"/start de {user.id} en chat:{chat.id if chat else '?'} (tipo: {chat.type if chat else '?'}). Args: {args}")

    # Solo actuar si es en chat privado
    if chat and chat.type == "private":
        # Si hay argumentos (payload del botón)
        if args:
            payload = args[0]
            action_type = None
            if payload == "iniciar_consulta":
                action_type = "consulta"
            elif payload == "iniciar_sugerencia":
                action_type = "sugerencia"

            if action_type:
                # CLAVE: Iniciar una nueva conversación
                context.user_data.clear() # Limpiar datos de posible conversación anterior
                logger.info(f"Payload '{payload}' válido recibido de {user.id}. Iniciando flujo para '{action_type}'.")
                context.user_data['action_type'] = action_type # Guardar qué tipo de acción es
                prompt = f"¡Hola {user.first_name}! Por favor, escribe ahora tu {action_type} en un único mensaje."
                await update.message.reply_text(prompt)
                return TYPING_REPLY # Entrar al estado de espera de texto
            else:
                # Payload desconocido
                logger.warning(f"Payload desconocido '{payload}' recibido de {user.id}. Ignorando.")
                await update.message.reply_text("Parece que el enlace que has usado no es válido o ha expirado.")
                context.user_data.clear() # Limpiar por si acaso
                return ConversationHandler.END # Terminar cualquier posible conversación residual
        else:
            # /start simple en privado (sin payload)
            logger.info(f"/start simple (sin payload) de {user.id}. Enviando saludo genérico.")
            await update.message.reply_text(f"¡Hola {user.first_name}! Para enviar una consulta o sugerencia, por favor, usa los botones correspondientes en el grupo del Comité.")
            context.user_data.clear() # Limpiar por si acaso
            return ConversationHandler.END # Asegurarse de no estar en conversación

    # Si no es chat privado, no hacer nada relevante para la conversación
    elif chat:
        logger.info(f"/start ignorado en chat no privado ({chat.id}, tipo: {chat.type})")

    return None # No retornar estado si no es aplicable

# --- Handler para Recibir Texto (Consulta/Sugerencia) ---
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Recibe el texto de la consulta/sugerencia en chat privado durante la conversación.
    Valida (si es consulta), envía al grupo externo, confirma al usuario y finaliza la conversación.
    """
    user = update.effective_user
    message = update.message

    # Comprobaciones básicas
    if not user or not message or not message.text or chat.type != 'private':
        logger.warning(f"receive_text recibió un update inesperado o inválido. User: {user.id if user else '?'}")
        # No debería llegar aquí si los filtros del MessageHandler son correctos, pero por si acaso.
        return TYPING_REPLY # Mantener estado por si fue un error momentáneo

    user_text = message.text
    # CLAVE: Obtener Y ELIMINAR 'action_type' para procesar este mensaje específico.
    # Esto asegura que la conversación no continúe esperando más texto después.
    action_type = context.user_data.pop('action_type', None)

    # Si por alguna razón 'action_type' no está (ej. estado corrupto), terminar.
    if not action_type:
        logger.error(f"receive_text ejecutado para {user.id} pero 'action_type' no encontrado en user_data. Terminando conversación.")
        await update.message.reply_text("Ha ocurrido un error inesperado. Por favor, intenta iniciar de nuevo usando los botones del grupo.")
        return ConversationHandler.END

    logger.info(f"Procesando '{action_type}' de {user.id}. Texto: {user_text[:50]}...")

    # --- Validación específica para consultas ---
    found_forbidden_topic = None
    if action_type == 'consulta':
        text_lower = user_text.lower()
        # Mapa de palabras clave (en minúsculas) a nombre del tema para el mensaje de error
        forbidden_map = {
            "bolsa de horas": "bolsa de horas",
            "permiso": "permisos", # Incluir singular y plural si es necesario
            "permisos": "permisos",
            "incapacidad temporal": "incapacidad temporal / baja",
            "baja": "incapacidad temporal / baja", # Agrupar sinónimos
            "excedencia": "excedencias",
            "excedencias": "excedencias"
        }
        # Comprobar si alguna palabra clave está en el texto
        for keyword, topic_name in forbidden_map.items():
            # Usar word boundaries (\b) para evitar coincidencias parciales si se desea
            # if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            # O simplemente 'in' si coincidencias parciales son aceptables/deseadas
            if keyword in text_lower:
                found_forbidden_topic = topic_name
                break # Encontramos una, no necesitamos seguir buscando

        if found_forbidden_topic:
            logger.warning(f"Consulta de {user.id} rechazada. Contiene tema prohibido: '{found_forbidden_topic}'. Texto: {user_text[:50]}...")
            error_msg = (
                f"❌ Tu consulta sobre '{found_forbidden_topic}' no puede ser procesada a través de este bot.\n"
                "Por favor, revisa la información disponible en el grupo o la documentación oficial sobre este tema."
                # Podrías añadir un enlace a la documentación si existe:
                # "\nPuedes encontrar más información aquí: [Enlace]"
            )
            try:
                await update.message.reply_text(error_msg) # Informar al usuario del rechazo
            except Exception as e:
                logger.error(f"Error enviando mensaje de rechazo de consulta a {user.id}: {e}")
            # context.user_data.clear() # Ya se hizo pop, pero limpiar de nuevo no hace daño
            return ConversationHandler.END # CLAVE: Terminar la conversación tras rechazo

    # --- Envío al Grupo Externo (si no fue rechazada) ---
    # Esta parte solo se ejecuta si found_forbidden_topic es None (o si action_type no era 'consulta')
    target_chat_id = None
    target_thread_id = None

    if action_type == 'consulta':
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_CONSULTAS_EXTERNO
    elif action_type == 'sugerencia':
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_SUGERENCIAS_EXTERNO
    else:
        # Esto no debería ocurrir si 'action_type' solo puede ser 'consulta' o 'sugerencia'
        logger.error(f"Valor inesperado para 'action_type' ({action_type}) encontrado para {user.id}. No se puede determinar destino.")
        try:
            await update.message.reply_text("❌ Ha ocurrido un error interno inesperado. No se ha podido procesar tu mensaje.")
        except Exception: pass
        return ConversationHandler.END # Terminar por error interno

    # Comprobar si tenemos un destino válido antes de intentar enviar
    if target_chat_id and target_thread_id:
        # Formatear el mensaje a enviar al grupo externo
        user_info = user.full_name
        if user.username:
            user_info += f" (@{user.username})"
        # Usar Markdown para un poco de formato si se desea
        fwd_msg = f"ℹ️ **Nueva {action_type.capitalize()} de {user_info}** (ID: {user.id}):\n\n{user_text}"
        send_success = False
        try:
            await context.bot.send_message(
                chat_id=target_chat_id,
                message_thread_id=target_thread_id,
                text=fwd_msg,
                parse_mode=ParseMode.MARKDOWN # Asegurarse que el parse_mode coincide con el formato usado
            )
            logger.info(f"{action_type.capitalize()} de {user.id} enviada correctamente a Grupo {target_chat_id} (Tema: {target_thread_id})")
            send_success = True
        except TelegramError as e:
            logger.error(f"Error de Telegram API enviando {action_type} de {user.id} a G:{target_chat_id} T:{target_thread_id}: {e}", exc_info=False)
        except Exception as e:
            logger.error(f"Excepción inesperada enviando {action_type} de {user.id} a G:{target_chat_id} T:{target_thread_id}: {e}", exc_info=True)

        # Informar al usuario del resultado
        if send_success:
            try:
                # CLAVE: Confirmación al usuario
                await update.message.reply_text(f"✅ ¡Tu {action_type} ha sido enviada correctamente! Gracias.")
                logger.info(f"Mensaje de confirmación enviado a {user.id}")
            except Exception as e:
                logger.error(f"Error enviando mensaje de confirmación a {user.id} tras éxito de envío: {e}")
        else:
            try:
                await update.message.reply_text(f"❌ Hubo un problema al intentar enviar tu {action_type}. Por favor, contacta a un administrador si el problema persiste.")
            except Exception as e:
                logger.error(f"Error enviando mensaje de fallo de envío a {user.id}: {e}")

        # CLAVE: Terminar la conversación después de procesar (éxito o fallo de envío)
        return ConversationHandler.END

    else:
         # Si no se pudo determinar target_chat_id o target_thread_id (por el error interno anterior)
         logger.error(f"No se pudo determinar un destino válido para la {action_type} de {user.id}. No se envió.")
         # El mensaje de error ya se intentó enviar antes.
         return ConversationHandler.END # Terminar


# --- Handler para /cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ Cancela la conversación activa si la hay. """
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or chat.type != 'private':
      return ConversationHandler.END # Ignorar si no es privado

    logger.info(f"Usuario {user.id} ejecutó /cancel.")
    was_in_conversation = bool(context.user_data) # Comprobar si había datos guardados
    context.user_data.clear() # Limpiar datos de usuario para esta conversación

    if was_in_conversation:
        msg = 'Operación cancelada. Puedes empezar de nuevo usando los botones del grupo si lo deseas.'
    else:
        msg = 'No hay ninguna operación activa para cancelar.'

    try:
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Error enviando mensaje de cancelación a {user.id}: {e}")

    return ConversationHandler.END # CLAVE: Siempre termina la conversación

# --- Handler para Mensajes Inesperados en Privado ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Responde a mensajes de texto en privado que no forman parte de una conversación activa
    (por ejemplo, si el usuario escribe después de que la conversación haya terminado).
    """
    user = update.effective_user
    chat = update.effective_chat
    message = update.message

    # Asegurarse de que es un mensaje de texto en un chat privado y no un comando
    if not user or not chat or chat.type != 'private' or not message or not message.text or message.text.startswith('/'):
        return # Ignorar otros tipos de updates

    # CLAVE: Comprobar si, por alguna anomalía, todavía estamos "en conversación".
    # Si 'action_type' aún existe, significa que `receive_text` falló en limpiarlo o terminar,
    # o que este handler se disparó incorrectamente. Ignorar para evitar doble procesamiento.
    if 'action_type' in context.user_data:
        logger.debug(f"handle_unexpected_message: Ignorando mensaje de texto de {user.id} porque 'action_type' aún existe en user_data. El ConversationHandler debería manejarlo.")
        return

    logger.info(f"Mensaje de texto inesperado (fuera de conversación) recibido de {user.id}: {message.text[:50]}...")

    # Intentar guiar al usuario de vuelta a los botones del grupo Comité
    if not GRUPO_ID or GRUPO_ID >= 0 or TEMA_BOTON_CONSULTAS_COMITE <= 0 or TEMA_BOTON_SUGERENCIAS_COMITE <= 0:
        # Si falta configuración crítica para los enlaces, enviar un mensaje genérico.
        logger.warning(f"No se pueden generar enlaces a botones para {user.id} debido a configuración faltante/inválida (GRUPO_ID, Temas Botones).")
        try:
            await update.message.reply_text("Para enviar una consulta o sugerencia, por favor, utiliza los botones específicos en el grupo del Comité.")
        except Exception as e:
            logger.error(f"Error enviando mensaje genérico (sin enlaces) a {user.id} en handle_unexpected_message: {e}")
        return

    try:
        # Construir los enlaces directos a los mensajes de los botones en el grupo/tema
        # Nota: Los enlaces t.me/c/ID_CORTO/ID_TEMA funcionan si el bot es miembro del grupo.
        short_group_id = str(GRUPO_ID).replace("-100", "", 1) # Formato corto para enlaces t.me/c/...
        url_con = f"https://t.me/c/{short_group_id}/{TEMA_BOTON_CONSULTAS_COMITE}"
        url_sug = f"https://t.me/c/{short_group_id}/{TEMA_BOTON_SUGERENCIAS_COMITE}"

        texto = ("Hola de nuevo 👋. Si quieres enviar una nueva consulta o sugerencia, por favor, utiliza los botones correspondientes que encontrarás en los temas del grupo Comité:")
        kb = [
            [InlineKeyboardButton("Ir al botón de Consultas 🤔", url=url_con)],
            [InlineKeyboardButton("Ir al botón de Sugerencias ✨", url=url_sug)]
        ]
        # Añadir botón al grupo general si está configurado GROUP_LINK
        if GROUP_LINK:
             kb.append([InlineKeyboardButton("Ir al Grupo Comité 👥", url=GROUP_LINK)])

        markup = InlineKeyboardMarkup(kb)
        await update.message.reply_text(texto, reply_markup=markup)
        logger.info(f"Respuesta con enlaces a botones enviada a {user.id}")

    except Exception as e:
        logger.error(f"Error creando o enviando mensaje con enlaces a botones para {user.id} en handle_unexpected_message: {e}", exc_info=True)
        # Fallback a mensaje simple si falla la creación de botones/enlaces
        try:
            await update.message.reply_text("Para enviar una consulta o sugerencia, por favor, utiliza los botones específicos en el grupo del Comité.")
        except Exception as e_fallback:
             logger.error(f"Error enviando mensaje de fallback a {user.id} en handle_unexpected_message: {e_fallback}")


# --- Configuración y Ejecución Principal ---
def main() -> None:
    """ Configura y ejecuta el bot de Telegram. """
    if not validar_variables():
        logger.critical("--- BOT DETENIDO: ERRORES CRÍTICOS EN LA CONFIGURACIÓN ---")
        return

    logger.info("--- Configurando la aplicación del bot ---")
    application = Application.builder().token(TOKEN).build()

    # --- Configuración del ConversationHandler ---
    # Define el flujo de la conversación para consultas y sugerencias
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start, filters=filters.ChatType.PRIVATE)], # Inicia con /start en privado
        states={
            TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)] # En estado TYPING_REPLY, espera texto
        },
        fallbacks=[
            CommandHandler('cancel', cancel, filters=filters.ChatType.PRIVATE), # Comando para cancelar
            CommandHandler('start', start, filters=filters.ChatType.PRIVATE)    # Permitir reiniciar con /start incluso dentro
            # Podrías añadir un MessageHandler aquí como fallback si quieres capturar texto inesperado DENTRO de la conversación
            # pero dado que receive_text siempre retorna END, no debería ser necesario.
        ],
        allow_reentry=True, # Permite reiniciar la conversación con el entry_point
        per_user=True,      # El estado es por usuario
        per_chat=True,      # El estado es por chat (relevante para privado)
        name="consulta_sugerencia_conv", # Nombre opcional para debugging
        persistent=False    # El estado no se guarda si el bot se reinicia
    )

    # --- Registro de Handlers ---
    # Es importante el orden (grupos) para que los manejadores más específicos se ejecuten primero.
    # Grupo 0: El ConversationHandler tiene la máxima prioridad para manejar /start y el texto DURANTE la conversación.
    application.add_handler(conv_handler, group=0)

    # Grupo 1: Handlers específicos fuera de la conversación principal.
    # Comando para que un admin postee los botones (solo en privado).
    application.add_handler(CommandHandler("postbotones", post_buttons_command, filters=filters.ChatType.PRIVATE), group=1)

    # Grupo 2: Handler general para mensajes de texto inesperados en privado (cuando no hay conversación activa).
    # Este se ejecutará si el ConversationHandler (grupo 0) no manejó el mensaje.
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_unexpected_message), group=2)

    # --- Iniciar el Bot ---
    logger.info("--- Iniciando Polling del Bot ---")
    try:
        # Iniciar el bot para que escuche actualizaciones
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"--- ERROR CRÍTICO DURANTE EL POLLING ---: {e}", exc_info=True)
    finally:
        logger.info("--- Bot Detenido ---")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # Captura errores muy tempranos durante la inicialización antes del main loop
        logger.critical(f"Error fatal durante la inicialización del bot antes de entrar en main(): {e}", exc_info=True)
