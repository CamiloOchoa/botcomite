from flask import Flask
from threading import Thread
import logging
import os
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ChatMemberHandler
)

# ======================================
# CONFIGURACIÓN INICIAL Y VALIDACIONES
# ======================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

try:
    # Validar y cargar variables de entorno
    TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
    GRUPO_ID = int(os.environ["GROUP_ID"].strip())
    TEMA_ID = int(os.environ.get("TOPIC_ID", "1"))
    BOT_USERNAME = os.environ["BOT_USERNAME"].strip().lstrip('@')
    GROUP_LINK = os.environ["GROUP_LINK"].strip()
    
    # Validaciones adicionales
    if ":" not in TOKEN:
        raise ValueError("Formato de token inválido")
    if GRUPO_ID >= 0:
        raise ValueError("GROUP_ID debe ser negativo")
    if not GROUP_LINK.startswith("https://t.me/"):
        raise ValueError("Enlace de grupo inválido")

except (KeyError, ValueError) as e:
    logger.critical(f"❌ Error de configuración: {str(e)}")
    exit(1)

# Configuración derivada
URL_TEMA = f"https://t.me/c/{str(abs(GRUPO_ID))[3:]}/{TEMA_ID}"

# ======================================
# CONFIGURACIÓN DE FLASK
# ======================================
app = Flask(__name__)

@app.route('/')
def health_check():
    return "🟢 Bot operativo", 200

# ======================================
# HANDLERS DE TELEGRAM (CORREGIDOS)
# ======================================
PERMISOS = {
    "hospitalizacion": {
        "nombre": "🏥 Hospitalización/Reposo",
        "info": """📋 **Hospitalización/Intervención/Reposo:**
- Duración: 2 días naturales
- Documentación: Certificado médico"""
    }
}

async def enviar_menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        teclado = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Iniciar chat", url=f"https://t.me/{BOT_USERNAME}?start")],
            [InlineKeyboardButton("📲 Menú privado", url=f"https://t.me/{BOT_USERNAME}?start=menu")]
        ])
        
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_ID,
            text="¡Bienvenido! Selecciona una opción:",
            reply_markup=teclado
        )
    except Exception as e:
        logger.error(f"Error en menú principal: {str(e)}")

async def manejar_permisos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        permiso = PERMISOS.get("hospitalizacion")
        if permiso:
            await query.edit_message_text(
                text=f"**{permiso['nombre']}**\n\n{permiso['info']}",
                parse_mode="Markdown"
            )
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="¿Necesitas más información?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📚 Ver más permisos", callback_data="menu_permisos")],
                    [InlineKeyboardButton("🏠 Menú principal", callback_data="menu_principal")]
                ])  # Paréntesis corregido aquí
            )
    except Exception as e:
        logger.error(f"Error manejando permisos: {str(e)}")

# ======================================
# CONFIGURACIÓN DEL BOT
# ======================================
def configurar_bot():
    application = Application.builder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("inicio", enviar_menu_principal))
    application.add_handler(CallbackQueryHandler(manejar_permisos, pattern="^perm_"))
    
    return application

# ======================================
# EJECUCIÓN PRINCIPAL
# ======================================
if __name__ == "__main__":
    try:
        # Iniciar bot
        bot_app = configurar_bot()
        bot_thread = Thread(target=bot_app.run_polling, daemon=True)
        bot_thread.start()
        logger.info("🤖 Bot iniciado correctamente")
        
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
