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
    # Validar que los IDs de temas sean números positivos
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
    # CORRECTO: Usar callback_data para iniciar la acción en el bot
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
     # CORRECTO: Usar callback_data para iniciar la acción en el bot
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
    # Idealmente, verificar si el usuario es admin del bot o del grupo
    # if update.effective_user.id not in ADMIN_USER_IDS:
    #     await update.message.reply_text("No tienes permiso para usar este comando.")
    #     return

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
    # Idealmente, verificar si el usuario es admin
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
            parse_mode=ParseMode.MARKDOWN # O usa HTML si prefieres
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
    data = query.data # "iniciar_consulta" o "iniciar_sugerencia"

    # Siempre responde al callback para quitar el "loading" del botón
    await query.answer()

    context.user_data.clear() # Limpia datos de conversaciones anteriores

    try:
        if data == "iniciar_consulta":
            context.user_data['action_type'] = "consulta"
            prompt = (
                "Hola 👋 Por favor, escribe ahora tu *consulta* en un único mensaje.\n\n"
                "Recibirás una respuesta tan pronto como sea posible.\n"
                "_Recuerda que solo los miembros del comité verán tu mensaje._"
            )
        elif data == "iniciar_sugerencia":
            context.user_data['action_type'] = "sugerencia"
            prompt = (
                "Hola 👋 Por favor, escribe ahora tu *sugerencia* en un único mensaje.\n\n"
                "_Recuerda que solo los miembros del comité verán tu mensaje._"
            )
        else:
            # Esto no debería pasar si el pattern del handler es correcto
            logger.warning(f"CallbackQuery con data inesperado recibido: {data}")
            await context.bot.send_message(chat_id=user.id, text="Acción no reconocida.")
            return ConversationHandler.END

        # Intenta enviar el mensaje de inicio al usuario en privado
        await context.bot.send_message(chat_id=user.id, text=prompt, parse_mode=ParseMode.MARKDOWN)
        return TYPING_REPLY # Pasa al estado donde se espera el mensaje del usuario

    except TelegramError as e:
        # Error común: El usuario no ha iniciado una conversación con el bot todavía.
        if "bot can't initiate conversation with a user" in str(e) or "chat not found" in str(e):
            logger.info(f"Usuario {user.id} ({user.full_name}) intentó usar el bot sin iniciarlo.")
            # Informa al usuario (como notificación emergente en el botón)
            await query.answer(
                text="⚠️ Necesitas iniciar el chat conmigo primero. Búscame (@{context.bot.username}) y pulsa 'Iniciar', luego vuelve a pulsar este botón.",
                show_alert=True # Muestra el mensaje como una alerta más persistente
            )
            # Opcionalmente, envía un mensaje al grupo/tema para guiar mejor
            # try:
            #     await query.message.reply_text(
            #         f" Oye {user.mention_markdown()}, parece que aún no has iniciado una conversación privada conmigo."
            #         f" Por favor, búscame ([@{context.bot.username}](https://t.me/{context.bot.username})) y pulsa 'Iniciar',"
            #         f" luego vuelve a presionar el botón de '{'Consulta' if data=='iniciar_consulta' else 'Sugerencia'}'.",
            #         parse_mode=ParseMode.MARKDOWN
            #     )
            # except Exception as group_msg_error:
            #     logger.error(f"No se pudo enviar mensaje guía al grupo/tema: {group_msg_error}")

        else:
            # Otro error de Telegram
            logger.error(f"Error de Telegram al intentar iniciar conversación con {user.id}: {e}", exc_info=True)
            await query.answer("❌ Ocurrió un error al procesar tu solicitud.", show_alert=True)

        context.user_data.clear() # Limpia por si acaso
        return ConversationHandler.END # Termina la conversación si no se pudo iniciar

    except Exception as e:
        logger.error(f"Excepción inesperada en callback_iniciar para {user.id}: {e}", exc_info=True)
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
        # Ignorar /start en grupos
        return ConversationHandler.END

    logger.info(f"/start recibido de {user.id} ({user.full_name}) con args: {args}")
    context.user_data.clear() # Limpia estado previo

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
            return TYPING_REPLY
        elif payload == "iniciar_sugerencia":
            context.user_data['action_type'] = "sugerencia"
            prompt = (
                "Hola de nuevo 👋 Parece que hiciste clic en un enlace para iniciar una sugerencia.\n\n"
                "Por favor, escribe ahora tu *sugerencia* en un único mensaje.\n"
                "_Solo los miembros del comité verán tu mensaje._"
            )
            await update.message.reply_text(prompt, parse_mode=ParseMode.MARKDOWN)
            return TYPING_REPLY
        else:
            # Payload desconocido
            await update.message.reply_text(
                "Hola 👋. El enlace que has usado no es válido o ha expirado.\n"
                "Si quieres enviar una consulta o sugerencia, por favor, usa los botones correspondientes en el grupo del Comité."
            )
            return ConversationHandler.END
    else:
        # /start sin payload
        await update.message.reply_text(
            "Hola 👋 Soy el bot asistente del Comité.\n"
            "Para enviar una *consulta* o *sugerencia* de forma privada, por favor, utiliza los botones 🙋‍♂️ o 💡 en los temas correspondientes del grupo del Comité."
            # Puedes añadir aquí un enlace al grupo si es público o si tienes el enlace de invitación
            # "[Ir al Grupo del Comité](TU_ENLACE_AL_GRUPO)"
            , parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

# --- Handler para recibir el texto del usuario (dentro de la conversación) ---
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el mensaje de consulta/sugerencia del usuario y lo reenvía."""
    user = update.effective_user
    message = update.message
    chat = update.effective_chat

    # Comprobaciones básicas
    if not message or not message.text:
        logger.warning(f"Mensaje vacío o sin texto recibido de {user.id} en estado TYPING_REPLY.")
        await update.message.reply_text("No he recibido un mensaje válido. Por favor, inténtalo de nuevo o usa /cancel.")
        # Podríamos mantener el estado o cancelarlo. Cancelar es más seguro.
        context.user_data.clear()
        return ConversationHandler.END

    user_text = message.text.strip()
    action_type = context.user_data.pop('action_type', None) # Obtiene y elimina action_type

    # Si no hay action_type, algo fue mal (quizás un reinicio del bot?)
    if not action_type:
        logger.warning(f"receive_text llamado para {user.id} pero sin 'action_type' en user_data.")
        await handle_unexpected_message(update, context) # Usa el manejador de mensajes inesperados
        return ConversationHandler.END

    # Validar longitud mínima
    MIN_LENGTH = 15
    if len(user_text) < MIN_LENGTH:
        logger.info(f"{action_type.capitalize()} de {user.id} demasiado corta ({len(user_text)} caracteres).")
        error_text = (
            f"⚠️ Tu {action_type} parece demasiado corta (mínimo {MIN_LENGTH} caracteres).\n"
            f"El mensaje *no* ha sido enviado.\n\n"
            f"Si fue un error, por favor, inicia el proceso de nuevo desde el botón en el grupo del Comité."
            # Opcional: Añadir botón para reintentar aquí mismo? Podría complicar el flujo.
        )
        await update.message.reply_text(error_text)
        context.user_data.clear() # Limpia para evitar estados inconsistentes
        return ConversationHandler.END

    # Determinar a dónde enviar el mensaje
    if action_type == "consulta":
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_ID_CONSULTAS_EXTERNO
        action_emoji = "🙋‍♂️"
    elif action_type == "sugerencia":
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_ID_SUGERENCIAS_EXTERNO
        action_emoji = "💡"
    else:
        # Esto no debería ocurrir si la lógica es correcta
        logger.error(f"Action type desconocido '{action_type}' en receive_text para user {user.id}.")
        await update.message.reply_text("❌ Hubo un error interno inesperado. Por favor, contacta a un administrador.")
        context.user_data.clear()
        return ConversationHandler.END

    # Construir el mensaje a reenviar
    user_mention = user.mention_markdown_v2() if user.username else user.full_name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!') # Escapado manual básico para MarkdownV2 si no hay username
    fwd_msg_header = f"{action_emoji} *Nueva {action_type.capitalize()} de {user_mention}* `(ID: {user.id})`:\n{'-'*20}\n"
    fwd_msg_body = user_text
    # Escapar caracteres especiales de MarkdownV2 en el cuerpo del mensaje del usuario
    escaped_body = fwd_msg_body.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
    fwd_msg = fwd_msg_header + escaped_body

    logger.info(f"Preparado para enviar {action_type} de {user.id} a G:{target_chat_id}, T:{target_thread_id}")

    try:
        # Enviar mensaje al grupo/tema externo
        await context.bot.send_message(
            chat_id=target_chat_id,
            message_thread_id=target_thread_id,
            text=fwd_msg,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        logger.info(f"✅ {action_type.capitalize()} de {user.id} enviada correctamente.")
        # Confirmar al usuario
        await update.message.reply_text(f"✅ ¡Tu {action_type} ha sido enviada correctamente! Gracias por tu aportación.")

    except TelegramError as e:
        logger.error(f"Error de Telegram API enviando {action_type} de {user.id} a G:{target_chat_id} T:{target_thread_id}: {e}", exc_info=True)
        # Informar al usuario del fallo
        await update.message.reply_text(f"❌ Hubo un problema técnico al enviar tu {action_type}. Por favor, inténtalo de nuevo más tarde o contacta a un administrador si el problema persiste.")
    except Exception as e:
        logger.error(f"Excepción inesperada enviando {action_type} de {user.id}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ocurrió un error inesperado al procesar tu {action_type}. Por favor, contacta a un administrador.")

    # Limpiar y finalizar la conversación
    context.user_data.clear()
    return ConversationHandler.END

# --- Handler para mensajes fuera de flujo (en chat privado) ---
async def handle_unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja mensajes de texto enviados al bot en privado fuera de una conversación activa."""
    user = update.effective_user
    chat = update.effective_chat

    # Asegurarse que es un chat privado y no un comando
    if chat.type != 'private' or not update.message or not update.message.text or update.message.text.startswith('/'):
        return # Ignorar otros casos

    logger.info(f"Mensaje inesperado recibido de {user.id} en chat privado: '{update.message.text[:50]}...'")
    await update.message.reply_text(
        "Hola 👋 Recibí tu mensaje, pero no estoy esperando una consulta o sugerencia en este momento.\n\n"
        "Si quieres enviar una, por favor, ve al grupo del Comité y utiliza los botones 🙋‍♂️ (Consulta) o 💡 (Sugerencia) en los temas correspondientes.\n\n"
        "También puedes usar /start para ver las opciones o /cancel si crees que estás en medio de una acción."
        # De nuevo, enlace al grupo opcional si es relevante/posible
        # "[Ir al Grupo del Comité](TU_ENLACE_AL_GRUPO)"
        , parse_mode=ParseMode.MARKDOWN
    )

# --- Comando para cancelar la conversación actual ---
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Permite al usuario cancelar la operación actual (consulta/sugerencia)."""
    user = update.effective_user
    logger.info(f"Usuario {user.id} ({user.full_name}) ejecutó /cancel.")
    if not context.user_data:
         await update.message.reply_text("No hay ninguna operación activa que cancelar.")
         return ConversationHandler.END # Aunque no estuviera en la conversación, asegurarse que termina

    await update.message.reply_text("Operación cancelada. Puedes empezar de nuevo cuando quieras usando los botones del grupo.")
    context.user_data.clear()
    return ConversationHandler.END

# --- Función Principal ---
def main() -> None:
    """Inicia el bot."""
    if not validar_variables():
        logger.critical("--- BOT DETENIDO: Errores críticos en la configuración ---")
        return

    # Configura la aplicación del bot
    application = ApplicationBuilder().token(TOKEN).build()

    # --- Define el manejador de conversación ---
    conv_handler = ConversationHandler(
        entry_points=[
            # Punto de entrada principal: botones de callback en el grupo
            CallbackQueryHandler(callback_iniciar, pattern="^iniciar_(consulta|sugerencia)$"),
            # Punto de entrada secundario: comando /start (con o sin deep link)
            CommandHandler('start', start_handler, filters=filters.ChatType.PRIVATE)
        ],
        states={
            # Estado: Esperando el texto de la consulta/sugerencia
            TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)]
        },
        fallbacks=[
            # Comandos para salir/cancelar la conversación
            CommandHandler('cancel', cancel_command, filters=filters.ChatType.PRIVATE),
            # Si envían /start de nuevo en medio, reinicia
            CommandHandler('start', start_handler, filters=filters.ChatType.PRIVATE),
            # Captura otros comandos inesperados durante la conversación
            MessageHandler(filters.COMMAND & filters.ChatType.PRIVATE, handle_unexpected_message) # O un mensaje específico de error
        ],
        allow_reentry=True, # Permite reiniciar la conversación con un punto de entrada
        per_user=True,      # Mantiene estados separados por usuario
        per_chat=True,      # Asegura que funcione en el chat privado correcto
        name="consulta_sugerencia_conv",
        # persistent=False # No necesitas persistencia si user_data se limpia bien
    )

    # --- Añade los Handlers a la aplicación ---
    # 1. El manejador de conversación (el más importante)
    application.add_handler(conv_handler)

    # 2. Comandos de administración (ejecutables en privado)
    application.add_handler(CommandHandler("postpaneles", post_panels_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("documentacion", documentacion_command, filters=filters.ChatType.PRIVATE))

    # 3. Manejador para mensajes de texto inesperados (fuera de conversación, en privado)
    #    Asegúrate que se ejecute DESPUÉS de conv_handler para no interferir
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_unexpected_message), group=1)

    # --- Inicia el Bot ---
    logger.info("--- Iniciando Polling del Bot ---")
    try:
        # Corre el bot hasta que se presione Ctrl+C
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"--- ERROR CRÍTICO DURANTE EL POLLING ---: {e}", exc_info=True)
    finally:
        logger.info("--- Bot Detenido ---")

if __name__ == '__main__':
    main()
