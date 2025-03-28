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
TYPING_REPLY = 0 # Solo necesitamos un estado después del botón

# --- IDs y Variables Globales ---
TOKEN = None
GRUPO_ID = None # Grupo del Comité
BOT_USERNAME = None
GROUP_LINK = None # Enlace al grupo del comité (si se usa)

# IDs de Temas en el GRUPO DEL COMITÉ (GRUPO_ID)
# !! IMPORTANTE: Debes obtener los IDs correctos para estos temas !!
TEMA_BOTON_CONSULTAS_COMITE = 272  # <- REEMPLAZA con el ID del tema donde irá el botón "Consulta"
TEMA_BOTON_SUGERENCIAS_COMITE = 291 # <- REEMPLAZA con el ID del tema donde irá el botón "Sugerencia"

# IDs de Temas en el GRUPO EXTERNO (GRUPO_EXTERNO_ID)
TEMA_CONSULTAS_EXTERNO = 69
TEMA_SUGERENCIAS_EXTERNO = 71
GRUPO_EXTERNO_ID = -1002433074372

# --- Validación de Variables de Entorno ---
def validar_variables():
    global TOKEN, GRUPO_ID, BOT_USERNAME, GROUP_LINK
    try:
        TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
        # ... (resto de validaciones iguales) ...
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
            # Cambiado a warning ya que no se usa activamente
            logger.warning("Enlace de grupo (GROUP_LINK) inválido o no configurado.")
            # raise ValueError("Enlace de grupo inválido") # Descomentar si es obligatorio

        logger.info(f"GRUPO_ID (Comité): {GRUPO_ID}")
        logger.info(f"TEMA_BOTON_CONSULTAS_COMITE: {TEMA_BOTON_CONSULTAS_COMITE}") # Log nuevo ID
        logger.info(f"TEMA_BOTON_SUGERENCIAS_COMITE: {TEMA_BOTON_SUGERENCIAS_COMITE}") # Log nuevo ID
        logger.info(f"GRUPO_EXTERNO_ID: {GRUPO_EXTERNO_ID}")
        logger.info(f"TEMA_CONSULTAS_EXTERNO: {TEMA_CONSULTAS_EXTERNO}")
        logger.info(f"TEMA_SUGERENCIAS_EXTERNO: {TEMA_SUGERENCIAS_EXTERNO}")

        logger.info("✅ Variables validadas correctamente")
        return True
    # ... (resto de manejo de errores igual) ...
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
    Envía DOS mensajes separados con UN botón cada uno a temas específicos
    del grupo del comité.
    """
    user = update.effective_user
    logger.info(f"Comando /start recibido de {user.id} ({user.full_name})")

    # 1. Mensaje para Consultas
    mensaje_consulta = "¿Alguien necesita enviar una consulta al grupo externo?"
    keyboard_consulta = [[InlineKeyboardButton("Iniciar Consulta 🙋‍♂️", callback_data='consulta')]]
    reply_markup_consulta = InlineKeyboardMarkup(keyboard_consulta)

    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_BOTON_CONSULTAS_COMITE, # Tema específico para consultas
            text=mensaje_consulta,
            reply_markup=reply_markup_consulta
        )
        logger.info(f"Mensaje botón 'Consulta' enviado a GRUPO_ID: {GRUPO_ID}, TEMA: {TEMA_BOTON_CONSULTAS_COMITE}")
    except Exception as e:
         logger.error(f"Error enviando mensaje botón 'Consulta' al tema {TEMA_BOTON_CONSULTAS_COMITE}: {e}")

    # 2. Mensaje para Sugerencias
    mensaje_sugerencia = "¿Alguien tiene una sugerencia para el grupo externo?"
    keyboard_sugerencia = [[InlineKeyboardButton("Iniciar Sugerencia 💡", callback_data='sugerencia')]]
    reply_markup_sugerencia = InlineKeyboardMarkup(keyboard_sugerencia)

    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_BOTON_SUGERENCIAS_COMITE, # Tema específico para sugerencias
            text=mensaje_sugerencia,
            reply_markup=reply_markup_sugerencia
        )
        logger.info(f"Mensaje botón 'Sugerencia' enviado a GRUPO_ID: {GRUPO_ID}, TEMA: {TEMA_BOTON_SUGERENCIAS_COMITE}")
    except Exception as e:
         logger.error(f"Error enviando mensaje botón 'Sugerencia' al tema {TEMA_BOTON_SUGERENCIAS_COMITE}: {e}")


async def button_callback(update: Update, context: CallbackContext) -> int:
    """
    Manejador para AMBOS botones inline ('consulta' o 'sugerencia').
    Inicia la conversación privada. No edita nada en el grupo.
    """
    query = update.callback_query
    user = query.from_user
    action_type = query.data # 'consulta' o 'sugerencia'

    await query.answer() # Responde al callback inmediatamente

    logger.info(f"Botón '{action_type}' presionado por {user.id} ({user.full_name}) en chat {query.message.chat_id} (tema {query.message.message_thread_id}). Iniciando conversación privada.")

    # Guardar la acción seleccionada
    context.user_data['action_type'] = action_type

    prompt_message = f"Has seleccionado '{action_type}'. Por favor, escribe tu mensaje ahora en este chat."

    try:
        # Enviar solicitud al usuario en privado
        await context.bot.send_message(chat_id=user.id, text=prompt_message)
        logger.info(f"Solicitud de texto enviada en privado a {user.id} para '{action_type}'")
        return TYPING_REPLY # Pasar al estado de espera de texto
    except Exception as e:
        logger.error(f"Error en button_callback al enviar mensaje privado a {user.id}: {e}")
        try:
             # Informar error en privado
             await context.bot.send_message(chat_id=user.id, text="Hubo un error al iniciar el proceso. Por favor, intenta pulsar el botón de nuevo o contacta a un administrador.")
        except Exception as inner_e:
            logger.error(f"Error adicional notificando error en button_callback a {user.id}: {inner_e}")
        context.user_data.clear()
        return ConversationHandler.END # Terminar si falla


async def receive_text(update: Update, context: CallbackContext) -> int:
    """
    Recibe el texto en privado, lo envía al grupo/tema externo apropiado.
    Confirma en privado.
    """
    user = update.effective_user
    user_text = update.message.text
    action_type = context.user_data.get('action_type')

    if not action_type:
        logger.warning(f"receive_text llamado sin action_type en user_data para {user.id}.")
        await update.message.reply_text("Algo salió mal, no recuerdo qué estabas enviando. Por favor, vuelve al grupo del comité y pulsa el botón apropiado de nuevo.")
        return ConversationHandler.END

    logger.info(f"Texto recibido de {user.id} para '{action_type}': {user_text[:50]}...")

    # Determinar destino EXTERNO basado en la acción guardada
    if action_type == 'consulta':
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_CONSULTAS_EXTERNO
    elif action_type == 'sugerencia':
        target_chat_id = GRUPO_EXTERNO_ID
        target_thread_id = TEMA_SUGERENCIAS_EXTERNO
    else:
        # Esto no debería ocurrir si los callback_data son correctos
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
        # Informar al usuario del error EN PRIVADO
        await update.message.reply_text(f"❌ Hubo un error al enviar tu {action_type}. Por favor, contacta a un administrador o inténtalo de nuevo más tarde.")

    finally:
        # Limpiar datos y terminar conversación
        context.user_data.clear()
        return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancela la operación actual en la conversación privada."""
    user = update.effective_user
    logger.info(f"Usuario {user.id} ({user.full_name}) canceló la conversación privada.")
    await update.message.reply_text('Operación cancelada. Puedes volver al grupo del comité si quieres iniciar de nuevo.')
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
            # Se activa con CUALQUIERA de los dos botones
            CallbackQueryHandler(button_callback, pattern='^(consulta|sugerencia)$')
            ],
        states={
            # Espera un mensaje de texto EN PRIVADO
            TYPING_REPLY: [MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, receive_text)],
        },
        fallbacks=[
            # Permite cancelar EN PRIVADO
            CommandHandler('cancel', cancel, filters=filters.ChatType.PRIVATE)
            ],
        per_user=True,
        per_chat=False,
        # conversation_timeout=60*10 # Opcional: Timeout
    )

    # Añadir handlers
    application.add_handler(CommandHandler("start", start)) # Comando inicial
    application.add_handler(conv_handler) # Manejador de la conversación

    logger.info("Iniciando polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot detenido.")

if __name__ == '__main__':
    main()
