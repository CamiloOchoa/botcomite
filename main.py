from flask import Flask
import logging
import os
import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)
from threading import Thread

# ======================================
# CONFIGURACIÓN INICIAL
# ======================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ======================================
# VALIDACIÓN DE VARIABLES DE ENTORNO
# ======================================
def validar_variables():
    try:
        # Telegram Token
        global TOKEN
        TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
        if not TOKEN or ":" not in TOKEN:
            raise ValueError("Formato de token inválido")

        # Group ID
        global GRUPO_ID
        grupo_id_raw = os.environ["GROUP_ID"].strip()
        grupo_id_limpio = re.sub(r"[^-\d]", "", grupo_id_raw)
        GRUPO_ID = int(grupo_id_limpio.split("=")[-1]) if "=" in grupo_id_limpio else int(grupo_id_limpio)
        
        if not (-1009999999999 < GRUPO_ID < -1000000000000):
            raise ValueError("ID de grupo inválido")

        # Bot Username
        global BOT_USERNAME
        BOT_USERNAME = os.environ["BOT_USERNAME"].strip().lstrip('@')
        if not BOT_USERNAME:
            raise ValueError("BOT_USERNAME vacío")

        # Group Link
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

# ======================================
# CONFIGURACIÓN DE FLASK (EN HILO SEPARADO)
# ======================================
app = Flask(__name__)

@app.route('/')
def health_check():
    return "🟢 Bot operativo", 200

def ejecutar_flask():
    app.run(host='0.0.0.0', port=8080, use_reloader=False)

# ======================================
# HANDLERS DE TELEGRAM (CORREGIDOS)
# ======================================
PERMISOS = {
    "hospitalizacion": {
        "nombre": "🏥 Hospitalización/Reposo",
        "info": """📋 **Hospitalización/Intervención/Reposo:
- Duración: 2 días naturales
- Documentación: Certificado médico"""
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        teclado = InlineKeyboardMarkup([
            [InlineKeyboardButton("Ver permisos", callback_data="menu_permisos")],
            [InlineKeyboardButton("Unirse al grupo", url=GROUP_LINK)]
        ])
        
        await update.message.reply_text(
            "¡Bienvenido al bot del Comité! Elige una opción:",
            reply_markup=teclado
        )
    except Exception as e:
        logger.error(f"Error en comando start: {str(e)}")

async def manejar_permisos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        permiso = PERMISOS["hospitalizacion"]
        await query.edit_message_text(
            text=f"**{permiso['nombre']}**\n\n{permiso['info']}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Volver al inicio", callback_data="menu_inicio")]
            ])
        )
    except Exception as e:
        logger.error(f"Error manejando permisos: {str(e)}")

# ======================================
# CONFIGURACIÓN DEL BOT (SOLUCIÓN DEFINITIVA)
# ======================================
async def main():
    application = Application.builder().token(TOKEN).build()
    
    # Registro de handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(manejar_permisos, pattern="^menu_"))
    
    # Inicialización manual para evitar conflictos de hilos
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Mantener el bot activo
    while True:
        await asyncio.sleep(3600)

# ======================================
# EJECUCIÓN PRINCIPAL (ESTRUCTURA CORRECTA)
# ======================================
if __name__ == "__main__":
    # Iniciar Flask en hilo separado
    flask_thread = Thread(target=ejecutar_flask, daemon=True)
    flask_thread.start()
    
    # Iniciar bot de Telegram en el hilo principal con asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Apagando bot...")
    except Exception as e:
        logger.critical(f"Error crítico: {str(e)}")
        exit(1)
