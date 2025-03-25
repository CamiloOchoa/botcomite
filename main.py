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
    ChatMemberHandler,
    MessageHandler,
    filters
)

# Configuración desde variables de entorno
TOKEN = os.getenv("TELEGRAM_TOKEN")
GRUPO_ID = int(os.getenv("GROUP_ID"))
TEMA_ID = int(os.getenv("TOPIC_ID"))
BOT_USERNAME = os.getenv("BOT_USERNAME")
GROUP_LINK = os.getenv("GROUP_LINK")
URL_TEMA = f"https://t.me/c/{str(GRUPO_ID)[4:]}/{TEMA_ID}" if GRUPO_ID else ""

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

PERMISOS = {
    "hospitalizacion": {
        "nombre": "🏥 Hospitalización/Reposo",
        "info": """📋 **Hospitalización/Intervención/Reposo:**
- Duración: 2 días naturales
- Documentación: Certificado médico"""
    },
    # ... (mantener el resto de permisos igual)
}

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot activo y funcionando!"

# -------------------------------------------------------------------
async def enviar_mensaje_opciones(chat_id: int, excluir: str, context: ContextTypes.DEFAULT_TYPE):
    botones = []
    if excluir != "menu_permisos":
        botones.append(InlineKeyboardButton("Permisos", callback_data="menu_permisos"))
    if excluir != "menu_bolsa":
        botones.append(InlineKeyboardButton("Bolsa de horas", callback_data="menu_bolsa"))
    if excluir != "menu_excedencias":
        botones.append(InlineKeyboardButton("Excedencias", callback_data="menu_excedencias"))
    botones.append(InlineKeyboardButton("Volver al menú principal", callback_data="menu_private"))
    teclado = InlineKeyboardMarkup([botones])
    await context.bot.send_message(
        chat_id=chat_id,
        text="Espero que te haya sido de utilidad, ¿Quieres información sobre otro tema?",
        reply_markup=teclado
    )

# -------------------------------------------------------------------
async def enviar_menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        teclado = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Iniciar conversación", url=f"https://t.me/{BOT_USERNAME}?start")],
            [InlineKeyboardButton("Menú privado", url=f"https://t.me/{BOT_USERNAME}?start=menu")]
        ])
        mensaje_texto = "Si es la primera vez, inicia un chat privado con nosotros:"
        
        if context.bot_data.get("mensaje_tema"):
            mensaje_id = context.bot_data["mensaje_tema"]
            await context.bot.edit_message_text(
                chat_id=GRUPO_ID,
                message_id=mensaje_id,
                text=mensaje_texto,
                reply_markup=teclado,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            mensaje = await context.bot.send_message(
                chat_id=GRUPO_ID,
                message_thread_id=TEMA_ID,
                text=mensaje_texto,
                reply_markup=teclado,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            context.bot_data["mensaje_tema"] = mensaje.message_id
            
    except Exception as e:
        logger.error(f"Error al enviar/editar el menú principal: {e}", exc_info=True)
        try:
            await context.bot.send_message(
                chat_id=GRUPO_ID,
                message_thread_id=TEMA_ID,
                text="⚠️ Hubo un problema al mostrar el menú. Por favor, usa /inicio de nuevo."
            )
        except Exception as e2:
            logger.error(f"Error al enviar mensaje de error al grupo: {e2}", exc_info=True)

# -------------------------------------------------------------------
# Resto de handlers con indentación corregida
# -------------------------------------------------------------------

async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = ("Si es la primera vez que entras presiona el botón Registro, "
             "si ya lo has hecho antes presiona el botón Inicio.")
    teclado = InlineKeyboardMarkup([
        [InlineKeyboardButton("Registro", callback_data="registro_click"),
         InlineKeyboardButton("Inicio", callback_data="inicio_click")]
    ])
    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_ID,
            text=texto,
            reply_markup=teclado,
            parse_mode="Markdown"
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="El mensaje de inicio ha sido publicado en el tema 'informacion' del grupo."
        )
    except Exception as e:
        logger.error(f"Error al enviar el comando /inicio: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Hubo un problema al enviar el mensaje. Inténtalo de nuevo."
        )

# ... (continuar con el resto de handlers manteniendo la indentación)

# ======================
# CONFIGURACIÓN FINAL
# ======================

def configurar_handlers(application):
    application.add_handler(CommandHandler("inicio", inicio))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("documentacion", documentacion))
    application.add_handler(CallbackQueryHandler(registro_click_handler, pattern="^registro_click$"))
    application.add_handler(CallbackQueryHandler(inicio_click_handler, pattern="^inicio_click$"))
    application.add_handler(CallbackQueryHandler(manejar_menu_privado, pattern="^(menu_|perm_)"))
    application.add_handler(CallbackQueryHandler(manejar_botones))
    application.add_handler(ChatMemberHandler(manejar_miembros_chat, ChatMemberHandler.CHAT_MEMBER))
    application.add_error_handler(error_handler)

def run_bot():
    try:
        application = Application.builder().token(TOKEN).build()
        configurar_handlers(application)
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logger.critical(f"Error crítico: {str(e)}", exc_info=True)

if __name__ == "__main__":
    if os.getenv("ENV") == "production":
        from gunicorn.app.base import BaseApplication

        class FlaskApp(BaseApplication):
            def __init__(self, app, options=None):
                self.application = app
                self.options = options or {}
                super().__init__()

            def load_config(self):
                for key, value in self.options.items():
                    self.cfg.set(key, value)

            def load(self):
                return self.application

        bot_thread = Thread(target=run_bot, daemon=True)
        bot_thread.start()

        options = {
            'bind': '0.0.0.0:8080',
            'workers': 4,
            'timeout': 120
        }
        FlaskApp(app, options).run()
    else:
        Thread(target=run_bot, daemon=True).start()
        app.run(host='0.0.0.0', port=8080, debug=False)
