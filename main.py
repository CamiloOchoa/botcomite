import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode

# Configuración del logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Estados para la conversación
SELECTING_ACTION, TYPING_REPLY = range(2) # SELECTING_ACTION no se usa realmente aquí, pero mantenemos la estructura

# Variables globales
TOKEN = None
GRUPO_ID = None # Grupo del Comité
BOT_USERNAME = None
GROUP_LINK = None

# IDs de los temas y grupos
TEMA_CONSULTAS_SUGERENCIAS = 272  # Tema en GRUPO_ID donde van los botones (¡Este mensaje NO se editará!)
TEMA_CONSULTAS_EXTERNO = 69  # Tema de consultas en GRUPO_EXTERNO_ID
TEMA_SUGERENCIAS_EXTERNO = 71  # Tema de sugerencias en GRUPO_EXTERNO_ID
GRUPO_EXTERNO_ID = -1002433074372  # ID del grupo externo

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

        BOT_USERNAME = os.environ["BOT_USERNAME"].strip().lstrip('@')
        if not BOT_USERNAME:
            raise ValueError("BOT_USERNAME vacío")

        GROUP_LINK = os.environ["GROUP_LINK"].strip()
        if not GROUP_LINK.startswith("https://t.me/"):
            raise ValueError("Enlace de grupo inválido")

        logger.info(f"GRUPO_ID (Comité): {GRUPO_ID}")
        logger.info(f"TEMA_CONSULTAS_SUGERENCIAS (Comité): {TEMA_CONSULTAS_SUGERENCIAS}")
        logger.info(f"GRUPO_EXTERNO_ID: {GRUPO_EXTERNO_ID}")
        logger.info(f"TEMA_CONSULTAS_EXTERNO: {TEMA_CONSULTAS_EXTERNO}")
        logger.info(f"TEMA_SUGERENCIAS_EXTERNO: {TEMA_SUGERENCIAS_EXTERNO}")

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

async def start(update: Update, context: CallbackContext) -> None:
    """
    Manejador del comando /start.
    Envía el mensaje con botones al grupo/tema del comité.
    Este mensaje NO se modificará posteriormente.
    """
    user = update.effective_user
    logger.info(f"Comando /start recibido de {user.id} ({user.full_name})")

    mensaje = "Si necesitas mandar una consulta sobre algun tema no resuelto en el grupo(permisos, excedencias,etc..), presiona el botón Consulta.\n Por otro lado, si quieres hacer alguna sugerencia para mejorar el grupo, presiona el botón sugerencia"
    keyboard = [
        [InlineKeyboardButton("Consulta 🙋‍♂️", callback_data='consulta')],
        [InlineKeyboardButton("Sugerencia 💡", callback_data='sugerencia')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_CONSULTAS_SUGERENCIAS,
            text=mensaje,
            reply_markup=reply_markup
        )
        logger.info(f"Mensaje inicial con botones enviado a GRUPO_ID: {GRUPO_ID}, TEMA: {TEMA_CONSULTAS_SUGERENCIAS}")
    except Exception as e:
         logger.error(f"Error enviando mensaje inicial al grupo del comité: {e}")


async def button_callback(update: Update, context: CallbackContext) -> int:
    """
    Manejador para los botones inline. Inicia la conversación privada.
    NO edita el mensaje original en el grupo del comité.
    """
    query = update.callback_query
    user = query.from_user
    action_type = query.data # 'consulta' o 'sugerencia'

    # Siempre responder al callback para quitar el "loading" del botón
    await query.answer()

    logger.info(f"Botón '{action_type}' presionado por {user.id} ({user.full_name}) en chat {query.message.chat_id}. Iniciando conversación privada.")

    # Guardar qué acción se seleccionó para usarla al recibir la respuesta
    context.user_data['action_type'] = action_type
    # Ya NO necesitamos guardar el ID del mensaje original

    prompt_message = f"Has seleccionado '{action_type}'. Por favor, escribe tu mensaje ahora. Envíalo como un mensaje normal en este chat."

    try:
        # Envía el mensaje de solicitud al usuario EN PRIVADO
        await context.bot.send_message(chat_id=user.id, text=prompt_message)
        logger.info(f"Solicitud de texto enviada en privado a {user.id} para '{action_type}'")
        # Pasa al estado donde esperamos la respuesta del usuario
        return TYPING_REPLY
    except Exception as e:
        logger.error(f"Error en button_callback al enviar mensaje privado a {user.id}: {e}")
        # Informar al usuario del error si es posible (ya que no podemos editar el original)
        try:
             await context.bot.send_message(chat_id=user.id, text="Hubo un error al iniciar el proceso. Por favor, intenta pulsar el botón de nuevo o contacta a un administrador.")
        except Exception as inner_e:
            logger.error(f"Error adicional notificando error en button_callback a {user.id}: {inner_e}")
        # Terminar la conversación si hay error al iniciarla
        context.user_data.clear()
        return ConversationHandler.END


async def receive_text(update: Update, context: CallbackContext) -> int:
    """
    Recibe el texto de la consulta/sugerencia del usuario en el chat privado.
    Lo envía al grupo/tema externo correspondiente.
    Confirma al usuario en privado.
    NO edita el mensaje original en el grupo del comité.
    """
    user = update.effective_user
    user_text = update.message.text
    action_type = context.user_data.get('action_type')

    if not action_type:
        logger.warning(f"receive_text llamado sin action_type en user_data para {user.id}. Posiblemente la conversación expiró o hubo un error.")
        await update.message.reply_text("Algo salió mal, no recuerdo qué estabas enviando. Por favor, vuelve al grupo del comité y pulsa el botón de nuevo.")
        return ConversationHandler.END

    logger.info(f"Texto recibido de {user.id} para '{action_type}': {user_text[:50]}...")

    # Determinar destino
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
        # Enviar al grupo/tema externo
        await context.bot.send_message(
            chat_id=target_chat_id,
            message_thread_id=target_thread_id,
            text=forward_message,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"{action_type.capitalize()} de {user.id} enviada a chat {target_chat_id} (tema {target_thread_id})")

        # Confirmar al usuario EN PRIVADO
        await update.message.reply_text(f"✅ ¡Tu {action_type} ha sido enviada correctamente al grupo correspondiente!")
        logger.info(f"Confirmación enviada en privado a {user.id}")

        # --- YA NO SE EDITA EL MENSAJE ORIGINAL ---

    except Exception as e:
        logger.error(f"Error enviando la {action_type} de {user.id} al grupo externo: {e}")
        # Informar al usuario del error EN PRIVADO
        await update.message.reply_text(f"❌ Hubo un error al enviar tu {action_type}. Por favor, contacta a un administrador o inténtalo de nuevo más tarde.")

    finally:
        # Limpiar datos de usuario y terminar conversación
        context.user_data.clear()
        return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext) -> int:
    """
    Cancela la operación actual (en la conversación privada).
    NO necesita restaurar el mensaje original.
    """
    user = update.effective_user
    logger.info(f"Usuario {user.id} ({user.full_name}) canceló la conversación privada.")

    await update.message.reply_text('Operación cancelada. Puedes volver al grupo del comité si quieres iniciar de nuevo.')

    # --- YA NO SE RESTAURA EL MENSAJE ORIGINAL ---

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
    conv_handler = ConversationHandler(
        entry_points=[
            # Se activa SOLO con los botones del mensaje enviado por /start
            CallbackQueryHandler(button_callback, pattern='^(consulta|sugerencia)$')
            ],
        states={
            # Espera un mensaje de texto EN PRIVADO después de pulsar un botón
            TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)],
        },
        fallbacks=[
            # Permite cancelar EN PRIVADO
            CommandHandler('cancel', cancel, filters=filters.ChatType.PRIVATE)
            ],
        # Configuración para que la conversación ocurra por usuario y no por chat
        # (importante porque el entry point está en un grupo pero el state está en privado)
        per_user=True,
        per_chat=False, # La conversación sigue al usuario, no al chat donde empezó
        # Opcional: Timeout para la conversación privada
        # conversation_timeout=60*10 # 10 minutos para responder en privado
    )

    # Añadir handlers
    application.add_handler(CommandHandler("start", start)) # Comando inicial
    application.add_handler(conv_handler) # Manejador de la conversación

    logger.info("Iniciando polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot detenido.")

if __name__ == '__main__':
    main()
