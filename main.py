import os
import re
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# Configuración del logging (puedes editar el nivel o el formato si lo deseas)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# VALIDACIÓN DE VARIABLES DE ENTORNO
def validar_variables():
    try:
        # Token del bot
        global TOKEN
        TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
        if not TOKEN or ":" not in TOKEN:
            raise ValueError("Formato de token inválido")

        # ID del grupo común donde se publicarán consultas y sugerencias
        global GRUPO_COMUN
        grupo_comun_raw = os.environ["GRUPO_COMUN"].strip()
        grupo_comun_limpio = re.sub(r"[^-\d]", "", grupo_comun_raw)
        GRUPO_COMUN = int(grupo_comun_limpio.split("=")[-1]) if "=" in grupo_comun_limpio else int(grupo_comun_limpio)
        if not (-1009999999999 < GRUPO_COMUN < -1000000000000):
            raise ValueError("ID de grupo común inválido")

        # ID del tema para consultas
        global TEMA_CONSULTAS
        tema_consultas_raw = os.environ["TEMA_CONSULTAS"].strip()
        tema_consultas_limpio = re.sub(r"[^0-9]", "", tema_consultas_raw)
        TEMA_CONSULTAS = int(tema_consultas_limpio)
        if TEMA_CONSULTAS <= 0:
            raise ValueError("ID de tema de consultas inválido")

        # ID del tema para sugerencias
        global TEMA_SUGERENCIAS
        tema_sugerencias_raw = os.environ["TEMA_SUGERENCIAS"].strip()
        tema_sugerencias_limpio = re.sub(r"[^0-9]", "", tema_sugerencias_raw)
        TEMA_SUGERENCIAS = int(tema_sugerencias_limpio)
        if TEMA_SUGERENCIAS <= 0:
            raise ValueError("ID de tema de sugerencias inválido")

        # Nombre del bot (sin @) - puedes editar si es necesario
        global BOT_USERNAME
        BOT_USERNAME = os.environ["BOT_USERNAME"].strip().lstrip('@')
        if not BOT_USERNAME:
            raise ValueError("BOT_USERNAME vacío")

        # Enlace del grupo principal (puedes editar si deseas cambiarlo)
        global GROUP_LINK
        GROUP_LINK = os.environ["GROUP_LINK"].strip()
        if not GROUP_LINK.startswith("https://t.me/"):
            raise ValueError("Enlace de grupo inválido")

        logger.info("✅ Variables validadas correctamente")
        return True

    except Exception as e:
        logger.critical(f"❌ Error de configuración: {str(e)}")
        return False

if not validar_variables():
    exit(1)

# Diccionario para rastrear el tipo de mensaje (consulta o sugerencia) de cada usuario.
# Puedes modificar este mecanismo de almacenamiento si lo deseas.
user_context = {}

# Comando /start para mostrar los botones
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Teclado inline con dos opciones: Consulta y Sugerencia
    teclado = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Enviar Consulta", callback_data="consulta")],
        [InlineKeyboardButton("💡 Enviar Sugerencia", callback_data="sugerencia")]
    ])
    await update.message.reply_text("Selecciona una opción:", reply_markup=teclado)

# Función para recibir mensajes privados de los usuarios
async def recibir_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    # Si el usuario no ha seleccionado una opción previamente, se le indica cómo proceder.
    if user_id not in user_context:
        await update.message.reply_text("Usa el botón adecuado para enviar consultas o sugerencias. Las respuestas solo serán vistas por los miembros del comité.")
        return

    # Se obtiene el tipo de mensaje (consulta o sugerencia) y se elimina del contexto
    tipo = user_context.pop(user_id)
    # Se define el tema de destino según el tipo, dentro del grupo común
    mensaje_thread_id = TEMA_CONSULTAS if tipo == "consulta" else TEMA_SUGERENCIAS
    # Mensaje formateado que se enviará al grupo en el tema correspondiente
    mensaje = f"📥 *Nueva {tipo} de @{update.message.from_user.username}:*\n{text}"
    await context.bot.send_message(chat_id=GRUPO_COMUN, message_thread_id=mensaje_thread_id, text=mensaje, parse_mode="Markdown")
    await update.message.reply_text("✅ Tu mensaje ha sido enviado.")

# Función para manejar la selección del botón (consulta o sugerencia)
async def manejar_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Se guarda el tipo de mensaje en el diccionario
    user_context[query.from_user.id] = query.data
    # Se envía un mensaje privado solicitando al usuario que escriba su consulta o sugerencia
    await context.bot.send_message(chat_id=query.from_user.id, text=f"✍️ Escribe tu {query.data} y envíamela.")

# Función principal que inicializa y ejecuta el bot
async def main():
    application = Application.builder().token(TOKEN).build()
    # Handler para el comando /start
    application.add_handler(CommandHandler("start", start))
    # Handler para los botones de consulta y sugerencia
    application.add_handler(CallbackQueryHandler(manejar_query, pattern="^(consulta|sugerencia)$"))
    # Handler para los mensajes de texto enviados en privado
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_mensaje))
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

