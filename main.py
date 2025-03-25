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
# VALIDACIÓN DE VARIABLES DE ENTORNO (CORREGIDA)
# ======================================
def validar_variables():
    try:
        # Telegram Token
        global TOKEN
        TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
        if not TOKEN or ":" not in TOKEN:
            raise ValueError("Formato de token inválido")

        # Group ID (Corrección crítica)
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
# CONFIGURACIÓN DE FLASK
# ======================================
app = Flask(__name__)

@app.route('/')
def health_check():
    return "🟢 Bot operativo", 200

# ======================================
# HANDLERS DE TELEGRAM (ERROR DE SINTAXIS CORREGIDO)
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
            ])  # Paréntesis corregido aquí
        )
    except Exception as e:
        logger.error(f"Error manejando permisos: {str(e)}")

# ======================================
# CONFIGURACIÓN DEL BOT (ACTUALIZADA)
# ======================================
def iniciar_bot():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(manejar_permisos, pattern="^menu_"))
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application.run_polling()

# ======================================
# EJECUCIÓN PRINCIPAL (ESTABLE)
# ======================================
if __name__ == "__main__":
    try:
        # Iniciar bot en hilo separado
        bot_thread = Thread(target=iniciar_bot, daemon=True)
        bot_thread.start()
        logger.info("🤖 Bot de Telegram iniciado correctamente")
        
        # Iniciar servidor web
        if os.environ.get("RAILWAY_ENVIRONMENT") == "production":
            from gunicorn.app.base import BaseApplication
            
            class GunicornApp(BaseApplication):
                def __init__(self, app, options=None):
                    self.application = app
                    self.options = options or {}
                    super().__init__()
                
                def load_config(self):
                    for key, value in self.options.items():
                        self.cfg.set(key, value)
                
                def load(self):
                    return self.application
            
            GunicornApp(app, {'bind': '0.0.0.0:8080', 'workers': 2}).run()
        else:
            app.run(host='0.0.0.0', port=8080)
            
    except Exception as e:
        logger.critical(f"Error crítico: {str(e)}")
        exit(1)
