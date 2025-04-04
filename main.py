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

# --- Estado para la Conversación ---
TYPING_REPLY = 0

# --- IDs y Variables Globales ---
# Grupo del Comité (interno) para botones y mensajes de documentación
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

# --- Callback Handler para Iniciar Conversación ---
async def callback_iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja el callback cuando se pulsa 'Iniciar consulta' o 'Iniciar sugerencia' desde el comando /postforo.
    Inicia la conversación asignando el 'action_type' y mostrando el mensaje de bienvenida.
    """
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "iniciar_consulta":
        context.user_data.clear()
        context.user_data['action_type'] = "consulta"
        prompt = (
            "Si no has encontrado la información que buscas en las secciones del grupo (permisos, bolsa de horas, excedencias, etc...), "
            "envíanos un mensaje. Recuerda que estas consultas son privadas y solo pueden verlas los miembros del comité. "
            "La consulta debe ser enviada en un solo mensaje."
        )
        await query.message.reply_text(prompt)
    elif data == "iniciar_sugerencia":
        context.user_data.clear()
        context.user_data['action_type'] = "sugerencia"
        prompt = (
            "Pulsa el botón si tienes alguna sugerencia para mejorar el grupo o el funcionamiento del comité. "
            "Recuerda que estas sugerencias son privadas y solo pueden verlas los miembros del comité. "
            "La sugerencia debe ser enviada en un solo mensaje."
        )
        await query.message.reply_text(prompt)
    else:
        await query.message.reply_text("Acción no reconocida.")

# --- Comando para Enviar Mensajes a los Temas Internos (Post Foros) ---
async def foro_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Envía dos mensajes:
    1. Al tema interno de consultas con el siguiente mensaje y botón:
       "Si no has encontrado la información que buscas en las secciones del grupo (permisos, bolsa de horas, excedencias, etc...),
       pulsa el siguiente botón y envíanos un mensaje.
       - Recuerda que estas consultas son privadas y solo pueden verlas los miembros del comité.
       - La consulta debe ser enviada en un solo mensaje."
       Botón: "Iniciar consulta" (callback_data="iniciar_consulta").
    2. Al tema interno de sugerencias con el siguiente mensaje y botón:
       "Pulsa el botón si tienes alguna sugerencia para mejorar el grupo o el funcionamiento del comité.
       - Recuerda que estas sugerencias son privadas y solo pueden verlas los miembros del comité.
       - La sugerencia debe ser enviada en un solo mensaje."
       Botón: "Iniciar sugerencia" (callback_data="iniciar_sugerencia").
    """
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
                "Inicia una nueva sugerencia presion
