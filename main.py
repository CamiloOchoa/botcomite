import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    ConversationHandler, # Sigue siendo necesario para el flujo después del /start
    MessageHandler,
    filters,
    ContextTypes, # Usar ContextTypes para type hinting
)
from telegram.constants import ParseMode

# Configuración del logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Estado para la conversación
TYPING_REPLY = 0

# --- IDs y Variables Globales ---
TOKEN = None
GRUPO_ID = None
BOT_USERNAME = None # Necesitaremos el username del bot
GROUP_LINK = None

# IDs de Temas en el GRUPO DEL COMITÉ (GRUPO_ID)
TEMA_BOTON_CONSULTAS_COMITE = 272  # <- REEMPLAZA
TEMA_BOTON_SUGERENCIAS_COMITE = 273 # <- REEMPLAZA

# IDs de Temas en el GRUPO EXTERNO (GRUPO_EXTERNO_ID)
TEMA_CONSULTAS_EXTERNO = 69
TEMA_SUGERENCIAS_EXTERNO = 71
GRUPO_EXTERNO_ID = -1002433074372

# --- Validación de Variables de Entorno ---
def validar_variables():
    global TOKEN, GRUPO_ID, BOT_USERNAME, GROUP_LINK
    try:
        TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
        if not TOKEN or ":" not in TOKEN:
            raise ValueError("Formato de token inválido")

        grupo_id_raw = os.environ["GROUP_ID"].strip()
        grupo_id_limpio = re.sub(r"[^-\d]", "", grupo_id_raw)
        GRUPO_ID = int(grupo_id_limpio)
        if not (GRUPO_ID < -100000000000):
             logger.warning(f"El GROUP_ID ({GRUPO_ID}) parece inusual, pero se continuará.")

        # BOT_USERNAME es crucial ahora
        BOT_USERNAME = os.environ["BOT_USERNAME"].strip().lstrip('@')
        if not BOT_USERNAME:
            raise ValueError("BOT_USERNAME vacío y es necesario para los botones URL")

        GROUP_LINK = os.environ.get("GROUP_LINK", "").strip() # Hacer opcional
        if GROUP_LINK and not GROUP_LINK.startswith("https://t.me/"):
            logger.warning("Enlace de grupo (GROUP_LINK) inválido.")

        logger.info(f"GRUPO_ID (Comité): {GRUPO_ID}")
        logger.info(f"TEMA_BOTON_CONSULTAS_COMITE: {TEMA_BOTON_CONSULTAS_COMITE}")
        logger.info(f"TEMA_BOTON_SUGERENCIAS_COMITE: {TEMA_BOTON_SUGERENCIAS_COMITE}")
        logger.info(f"GRUPO_EXTERNO_ID: {GRUPO_EXTERNO_ID}")
        logger.info(f"TEMA_CONSULTAS_EXTERNO: {TEMA_CONSULTAS_EXTERNO}")
        logger.info(f"TEMA_SUGERENCIAS_EXTERNO: {TEMA_SUGERENCIAS_EXTERNO}")
        logger.info(f"BOT_USERNAME: @{BOT_USERNAME}")

        logger.info("✅ Variables validadas correctamente")
        return True
    except KeyError as e:
        logger.critical(f"❌ Error de configuración: Falta la variable de entorno {str(e)}")
        return False
    except ValueError as e:
         logger.critical(f"❌ Error de configuración: {str(e)}")
         return False
    except Exception as e:
        logger.critical(f"❌ Error de configuración inesperado: {str(e)}")
        return False

# --- Funciones del Bot ---

async def post_initial_buttons(context: CallbackContext) -> None:
    """
    Envía (o reenvía) los mensajes iniciales con botones URL a los temas del comité.
    Separado de start para poder llamarlo periódicamente si se desea.
    """
    if not BOT_USERNAME:
        logger.error("No se puede enviar botones URL sin BOT_USERNAME configurado.")
        return

    # 1. Mensaje para Consultas
    mensaje_consulta = "Pulsa aquí para enviar una consulta al grupo externo."
    # Crear URL con parámetro start
    url_consulta = f"https://t.me/{BOT_USERNAME}?start=iniciar_consulta"
    keyboard_consulta = [[InlineKeyboardButton("Iniciar Consulta 🙋‍♂️", url=url_consulta)]]
    reply_markup_consulta = InlineKeyboardMarkup(keyboard_consulta)

    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_BOTON_CONSULTAS_COMITE,
            text=mensaje_consulta,
            reply_markup=reply_markup_consulta
        )
        logger.info(f"Mensaje botón URL 'Consulta' enviado a GRUPO_ID: {GRUPO_ID}, TEMA: {TEMA_BOTON_CONSULTAS_COMITE}")
    except Exception as e:
         logger.error(f"Error enviando mensaje botón URL 'Consulta' al tema {TEMA_BOTON_CONSULTAS_COMITE}: {e}")

    # 2. Mensaje para Sugerencias
    mensaje_sugerencia = "Pulsa aquí si tienes una sugerencia para el grupo externo."
    # Crear URL con parámetro start
    url_sugerencia = f"https://t.me/{BOT_USERNAME}?start=iniciar_sugerencia"
    keyboard_sugerencia = [[InlineKeyboardButton("Iniciar Sugerencia 💡", url=url_sugerencia)]]
    reply_markup_sugerencia = InlineKeyboardMarkup(keyboard_sugerencia)

    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_BOTON_SUGERENCIAS_COMITE,
            text=mensaje_sugerencia,
            reply_markup=reply_markup_sugerencia
        )
        logger.info(f"Mensaje botón URL 'Sugerencia' enviado a GRUPO_ID: {GRUPO_ID}, TEMA: {TEMA_BOTON_SUGERENCIAS_COMITE}")
    except Exception as e:
         logger.error(f"Error enviando mensaje botón URL 'Sugerencia' al tema {TEMA_BOTON_SUGERENCIAS_COMITE}: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """
    Manejador del comando /start.
    - Si se ejecuta en privado CON un parámetro válido (payload), inicia la conversación.
    - Si se ejecuta en privado SIN parámetro, da un mensaje de bienvenida.
    - Si se ejecuta en un grupo (o es llamado por un admin para postear),
      llama a post_initial_buttons.
    """
    user = update.effective_user
    chat = update.effective_chat
    args = context.args # Argumentos pasados con /start (ej: ['iniciar_consulta'])

    logger.info(f"Comando /start recibido de {user.id} ({user.full_name}) en chat {chat.id} ({chat.type}). Args: {args}")

    # --- Caso 1: /start con payload en chat PRIVADO (viene del botón URL) ---
    if chat.type == "private" and args:
        payload = args[0]
        action_type = None
        if payload == "iniciar_consulta":
            action_type = "consulta"
        elif payload == "iniciar_sugerencia":
            action_type = "sugerencia"

        if action_type:
            logger.info(f"Payload '{payload}' detectado para usuario {user.id}. Iniciando flujo de {action_type}.")
            context.user_data['action_type'] = action_type
            prompt_message = f"¡Hola {user.first_name}! Has iniciado el proceso para enviar una {action_type}. Por favor, escribe tu mensaje ahora."
            await update.message.reply_text(prompt_message)
            return TYPING_REPLY # Entrar al estado de espera de la conversación
        else:
            logger.warning(f"Payload desconocido '{payload}' recibido de {user.id}.")
            await update.message.reply_text("Parece que has usado un enlace inválido. Si querías enviar algo, por favor, vuelve al grupo y usa el botón correcto.")
            return ConversationHandler.END # No iniciar conversación

    # --- Caso 2: /start sin payload en chat PRIVADO ---
    elif chat.type == "private":
        logger.info(f"Comando /start simple recibido en privado de {user.id}.")
        await update.message.reply_text(f"¡Hola {user.first_name}! Soy el bot del comité. Puedes interactuar conmigo usando los botones en el grupo.")
        # Podrías añadir más info aquí si quieres
        return ConversationHandler.END # No iniciar conversación aquí

    # --- Caso 3: /start en un GRUPO o CANAL (potencialmente para postear botones) ---
    # Podrías añadir una comprobación de si el usuario es admin aquí si quieres restringir
    # quién puede hacer que el bot postee los botones con /start en el grupo
    elif chat.type in ["group", "supergroup"]:
         logger.info(f"/start recibido en grupo {chat.id}. Intentando (re)postear botones iniciales.")
         # Comentado para evitar que cualquiera postee. Descomentar si se quiere esta funcionalidad.
         # await post_initial_buttons(context)
         # await update.message.reply_text("He (re)publicado los botones de inicio en los temas correspondientes.")
         return None # No es parte de la conversación principal

    return ConversationHandler.END # Caso por defecto, no hacer nada conversacional


async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Recibe el texto en privado, lo envía al grupo/tema externo apropiado.
    Confirma en privado. (Esta función apenas necesita cambios)
    """
    user = update.effective_user
    user_text = update.message.text
    action_type = context.user_data.get('action_type')

    # Misma lógica que antes
    if not action_type:
        logger.warning(f"receive_text llamado sin action_type en user_data para {user.id}.")
        await update.message.reply_text("Algo salió mal, no recuerdo qué estabas enviando. Por favor, vuelve al grupo del comité y pulsa el botón apropiado de nuevo.")
        return ConversationHandler.END

    logger.info(f"Texto recibido de {user.id} para '{action_type}': {user_text[:50]}...")

    # Determinar destino EXTERNO
    if action_type == 'consulta':
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_CONSULTAS_EXTERNO
    elif action_type == 'sugerencia':
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_SUGERENCIAS_EXTERNO
    else:
        logger.error(f"Tipo de acción desconocido '{action_type}' en receive_text para {user.id}")
        await update.message.reply_text("Error interno. Tipo de acción desconocida.")
        context.user_data.clear()
        return ConversationHandler.END

    # Formatear mensaje para el grupo externo
    user_info = f"{user.full_name}" + (f" (@{user.username})" if user.username else "") + f" (ID: {user.id})"
    forward_message = f"ℹ️ **Nueva {action_type.capitalize()} de {user_info}**:\n\n" \
                      f"{user_text}"

    try:
        # Enviar al grupo/tema EXTERNO
        await context.bot.send_message(
            chat_id=target_chat_id,
            message_thread_id=target_thread_id,
            text=forward_message,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"{action_type.capitalize()} de {user.id} enviada a chat EXTERNO {target_chat_id} (tema {target_thread_id})")
        # Confirmar al usuario EN PRIVADO
        await update.message.reply_text(f"✅ ¡Tu {action_type} ha sido enviada correctamente al grupo externo!")
        logger.info(f"Confirmación enviada en privado a {user.id}")

    except Exception as e:
        logger.error(f"Error enviando la {action_type} de {user.id} al grupo externo: {e}")
        await update.message.reply_text(f"❌ Hubo un error al enviar tu {action_type}. Por favor, contacta a un administrador o inténtalo de nuevo más tarde.")

    finally:
        context.user_data.clear()
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación privada."""
    user = update.effective_user
    logger.info(f"Usuario {user.id} ({user.full_name}) canceló la conversación privada.")
    await update.message.reply_text('Operación cancelada.')
    context.user_data.clear()
    return ConversationHandler.END

# --- Configuración y Ejecución ---
def main() -> None:
    """Inicia el bot."""
    if not validar_variables():
       logger.critical("Deteniendo el bot debido a errores de configuración.")
       return

    application = Application.builder().token(TOKEN).build()

    # --- Conversation Handler ---
    # Ahora la conversación empieza con /start en privado y con payload
    conv_handler = ConversationHandler(
        entry_points=[
            # El CommandHandler para /start ahora es el punto de entrada
            # Filtramos para que solo entre en la conversación si start() devuelve TYPING_REPLY
            CommandHandler('start', start, filters=filters.ChatType.PRIVATE) # Asegurarse que solo responde a /start en privado aquí
        ],
        states={
            # Espera un mensaje de texto EN PRIVADO
            TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)],
        },
        fallbacks=[
            # Permite cancelar EN PRIVADO con /cancel
            CommandHandler('cancel', cancel, filters=filters.ChatType.PRIVATE),
            # Podrías añadir un fallback para /start aquí si el usuario lo usa a mitad de conversación
            CommandHandler('start', start, filters=filters.ChatType.PRIVATE)
        ],
        per_user=True, # La conversación sigue al usuario
        per_chat=True, # Y ocurre en el chat privado
    )

    # Añadir handlers
    application.add_handler(conv_handler) # El ConversationHandler maneja el /start relevante

    # Añadir un handler para /start en grupos (opcional, para postear botones)
    # Este se ejecutará si el conv_handler no lo captura (porque está en grupo o sin payload)
    # application.add_handler(CommandHandler("start", start, filters=filters.ChatType.GROUP | filters.ChatType.SUPERGROUP))

    # (MUY RECOMENDADO) Llamar a post_initial_buttons una vez al iniciar el bot
    # Para asegurarse de que los botones estén presentes o se actualicen al reiniciar
    # Usamos job_queue para ejecutarlo después de que el bot esté listo
    application.job_queue.run_once(post_initial_buttons, 5) # Ejecutar 5 segundos después de iniciar

    logger.info("Iniciando polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot detenido.")

if __name__ == '__main__':
    main()
