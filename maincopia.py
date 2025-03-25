from flask import Flask
from threading import Thread
import logging
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

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = "7586734778:AAGB_F2I6KjErkNH6M8WZO9dzEdVwmo970c"
GRUPO_ID = -1002261336942
TEMA_ID = 124
URL_TEMA = f"https://t.me/c/{str(GRUPO_ID)[4:]}/{TEMA_ID}"
GROUP_LINK = "https://t.me/+NnCfkbQ0o2kzZTJk"  # Enlace público del grupo
BOT_USERNAME = "ComitePolobot"

PERMISOS = {
    "hospitalizacion": {
        "nombre": "🏥 Hospitalización/Reposo",
        "info": """📋 **Hospitalización/Intervención/Reposo:**
- Duración: 2 días naturales
- Documentación: Certificado médico"""
    },
    "fallecimiento_1_2": {
        "nombre": "⚰️ Fallecimiento 1º y 2º grado",
        "info": """📋 **Fallecimiento 1º y 2º grado:**
- Duración: Varios días (especificar)
- Documentación: Certificado de defunción y parentesco"""
    },
    "fallecimiento_3": {
        "nombre": "⚰️ Fallecimiento 3º grado",
        "info": """📋 **Fallecimiento 3º grado:**
- Duración: Varios días (especificar)
- Documentación: Certificado de defunción y parentesco"""
    },
    "matrimonio": {
        "nombre": "💍 Matrimonio",
        "info": """📋 **Matrimonio:**
- Duración: 15 días
- Documentación: Certificado de matrimonio"""
    },
    "lactancia": {
        "nombre": "🤱 Lactancia",
        "info": """📋 **Lactancia:**
- Duración: 1 hora diaria
- Documentación: Certificado de nacimiento del hijo"""
    },
    "maternidad_paternidad": {
        "nombre": "🤰 Maternidad y Paternidad",
        "info": """📋 **Maternidad/Paternidad:**
- Duración: Varias semanas
- Documentación: Certificado de nacimiento o informe médico"""
    },
    "nacimiento": {
        "nombre": "👶 Nacimiento",
        "info": """📋 **Nacimiento:**
- Duración: Varios días
- Documentación: Certificado de nacimiento"""
    },
    "asuntos_propios": {
        "nombre": "❓ Asuntos Propios",
        "info": """📋 **Asuntos Propios:**
- Duración: Días establecidos por convenio
- Documentación: Solicitud"""
    },
    "mudanza": {
        "nombre": "🚚 Mudanza",
        "info": """📋 **Mudanza:**
- Duración: 1 día
- Documentación: Justificante de cambio de domicilio"""
    },
    "formacion_academica": {
        "nombre": "🎓 Formación Académica",
        "info": """📋 **Formación Académica:**
- Duración: Tiempo necesario para exámenes
- Documentación: Justificante de matrícula o examen"""
    },
}

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot activo!"

# -------------------------------------------------------------------
# Función auxiliar para enviar el mensaje con opciones después de mostrar información de un tema
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
# En el grupo se envía un mensaje inicial con dos botones: "Iniciar conversación" y "Menú privado"
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
# Comando /inicio en chat privado: Publica el mensaje en el tema "informacion" del grupo con dos botones: "Registro" y "Inicio".
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

# -------------------------------------------------------------------
# Manejador para el botón "Registro"
async def registro_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        try:
            await query.answer()
        except Exception as e:
            if "Query is too old" in str(e):
                logger.warning("Callback query expired.")
            else:
                raise
        user_id = query.from_user.id
        if not context.user_data.get(f"bienvenido_{user_id}"):
            bienvenida = ("¡Bienvenido! Gracias por registrarte.\n\n"
                          "A continuación, te mostramos el menú con las opciones disponibles:")
            await context.bot.send_message(chat_id=user_id, text=bienvenida)
            context.user_data[f"bienvenido_{user_id}"] = True
        teclado_menu = InlineKeyboardMarkup([
            [InlineKeyboardButton("Permisos", callback_data="menu_permisos")],
            [InlineKeyboardButton("Bolsa de horas", callback_data="menu_bolsa")],
            [InlineKeyboardButton("Excedencias", callback_data="menu_excedencias")],
            [InlineKeyboardButton("Otras consultas", callback_data="menu_otras")],
            [InlineKeyboardButton("Volver", callback_data="volver_inicio")]
        ])
        await context.bot.send_message(chat_id=user_id, text="Elige una opción:", reply_markup=teclado_menu)
    except Exception as e:
        logger.error(f"Error en registro_click_handler: {e}", exc_info=True)
        await context.bot.send_message(chat_id=query.from_user.id, text="⚠️ Hubo un problema. Inténtalo de nuevo.")

# -------------------------------------------------------------------
# Manejador para el botón "Inicio"
async def inicio_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        try:
            await query.answer()
        except Exception as e:
            if "Query is too old" in str(e):
                logger.warning("Callback query expired.")
            else:
                raise
        user_id = query.from_user.id
        if context.user_data.get(f"bienvenido_{user_id}"):
            teclado_menu = InlineKeyboardMarkup([
                [InlineKeyboardButton("Permisos", callback_data="menu_permisos")],
                [InlineKeyboardButton("Bolsa de horas", callback_data="menu_bolsa")],
                [InlineKeyboardButton("Excedencias", callback_data="menu_excedencias")],
                [InlineKeyboardButton("Otras consultas", callback_data="menu_otras")],
                [InlineKeyboardButton("Volver", callback_data="volver_inicio")]
            ])
            await context.bot.send_message(chat_id=user_id, text="Elige una opción:", reply_markup=teclado_menu)
        else:
            await context.bot.send_message(chat_id=user_id, text="Por favor, pulsa el botón Registro para comenzar.")
    except Exception as e:
        logger.error(f"Error en inicio_click_handler: {e}", exc_info=True)
        try:
            await query.edit_message_text("⚠️ Hubo un problema al procesar tu solicitud.")
        except Exception:
            pass

# -------------------------------------------------------------------
# Manejador para el botón "Volver" en el menú privado (Regresa al mensaje original de /inicio)
async def volver_inicio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        if "Query is too old" in str(e):
            logger.warning("Callback query expired.")
        else:
            logger.error(f"Error al contestar callback: {e}", exc_info=True)
    user_id = query.from_user.id
    texto = ("Si es la primera vez que entras presiona el botón Registro, "
             "si ya lo has hecho antes presiona el botón Inicio.")
    teclado = InlineKeyboardMarkup([
        [InlineKeyboardButton("Registro", callback_data="registro_click"),
         InlineKeyboardButton("Inicio", callback_data="inicio_click")]
    ])
    await context.bot.send_message(chat_id=user_id, text=texto, reply_markup=teclado)

# -------------------------------------------------------------------
# Comando /start en chat privado (para otros fines)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if not context.user_data.get(f"bienvenido_{user_id}"):
        bienvenida = ("¡Bienvenido! Gracias por iniciar conversación.\n\n"
                      "A continuación, te mostramos el menú con las opciones disponibles:")
        await context.bot.send_message(chat_id=chat_id, text=bienvenida)
        context.user_data[f"bienvenido_{user_id}"] = True
    teclado_menu = InlineKeyboardMarkup([
        [InlineKeyboardButton("Permisos", callback_data="menu_permisos")],
        [InlineKeyboardButton("Bolsa de horas", callback_data="menu_bolsa")],
        [InlineKeyboardButton("Excedencias", callback_data="menu_excedencias")],
        [InlineKeyboardButton("Otras consultas", callback_data="menu_otras")],
        [InlineKeyboardButton("Volver al menú principal", url=GROUP_LINK)]
    ])
    await context.bot.send_message(chat_id=chat_id, text="Elige una opción:", reply_markup=teclado_menu)

# -------------------------------------------------------------------
# Comando /documentacion en chat privado: Publica el mensaje en el tema DOCUMENTACIÓN del grupo.
async def documentacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    enlace_calendario = "https://ejemplo.com/calendario_laboral_2025.pdf"
    enlace_convenio = "https://ejemplo.com/convenio.pdf"
    enlace_tablas = "https://ejemplo.com/tablas_salariales_2025.pdf"
    botones = [
        [InlineKeyboardButton("Calendario laboral 2025", url=enlace_calendario)],
        [InlineKeyboardButton("Convenio", url=enlace_convenio)],
        [InlineKeyboardButton("Tablas salariales 2025", url=enlace_tablas)]
    ]
    teclado = InlineKeyboardMarkup(botones)
    try:
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            message_thread_id=TEMA_ID,
            text="¿Qué documento quieres consultar?",
            reply_markup=teclado
        )
        await context.bot.send_message(chat_id=chat_id, text="El mensaje ha sido enviado al tema DOCUMENTACIÓN del grupo.")
    except Exception as e:
        logger.error(f"Error al enviar el comando /documentacion: {e}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Hubo un problema al enviar la documentación. Inténtalo de nuevo.")

# -------------------------------------------------------------------
# Manejador del menú privado en chat individual
async def manejar_menu_privado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        if "Query is too old" in str(e):
            logger.warning("Callback query expired.")
        else:
            logger.error(f"Error al contestar callback: {e}", exc_info=True)
    chat_id = update.effective_chat.id
    if query.data == "menu_permisos":
        botones = [[InlineKeyboardButton(permiso['nombre'], callback_data=f"perm_{key}")]
                   for key, permiso in PERMISOS.items()]
        botones.append([InlineKeyboardButton("Volver", callback_data="menu_private")])
        teclado = InlineKeyboardMarkup(botones)
        await context.bot.send_message(chat_id=chat_id, text="Selecciona un permiso:", reply_markup=teclado)
    elif query.data.startswith("perm_"):
        key = query.data[len("perm_"):]
        permiso = PERMISOS.get(key)
        if permiso:
            text = f"{permiso['nombre']}:\n{permiso['info']}"
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
            teclado = InlineKeyboardMarkup([
                [InlineKeyboardButton("Ver otros permisos", callback_data="menu_permisos"),
                 InlineKeyboardButton("Volver al menú principal", callback_data="menu_private")]
            ])
            await context.bot.send_message(chat_id=chat_id, text="Elige una opción:", reply_markup=teclado)
    elif query.data == "menu_bolsa":
        await context.bot.send_message(chat_id=chat_id, text="🕒 *Bolsa de horas:*\n\nInformación sobre la bolsa de horas.", parse_mode="Markdown")
        await enviar_mensaje_opciones(chat_id, excluir="menu_bolsa", context=context)
    elif query.data == "menu_excedencias":
        await context.bot.send_message(chat_id=chat_id, text="⏳ *Excedencias:*\n\nInformación sobre excedencias.", parse_mode="Markdown")
        await enviar_mensaje_opciones(chat_id, excluir="menu_excedencias", context=context)
    elif query.data == "menu_private":
        teclado_menu = InlineKeyboardMarkup([
            [InlineKeyboardButton("Permisos", callback_data="menu_permisos")],
            [InlineKeyboardButton("Bolsa de horas", callback_data="menu_bolsa")],
            [InlineKeyboardButton("Excedencias", callback_data="menu_excedencias")],
            [InlineKeyboardButton("Volver al menú principal", url=GROUP_LINK)]
        ])
        await context.bot.send_message(chat_id=chat_id, text="Elige una opción:", reply_markup=teclado_menu)
    else:
        await query.edit_message_text("Opción no válida.")

# -------------------------------------------------------------------
# Manejador para otros botones no reconocidos
async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        logger.warning(f"Callback data no reconocido: {query.data}")
        await context.bot.send_message(chat_id=GRUPO_ID, message_thread_id=TEMA_ID, text="⚠️ Opción no válida. Por favor, usa el menú principal.")
    except Exception as e:
        logger.error(f"Error al manejar botón: {e}", exc_info=True)
        try:
            await context.bot.send_message(chat_id=GRUPO_ID, message_thread_id=TEMA_ID, text="⚠️ Hubo un problema al procesar tu solicitud. Por favor, inténtalo de nuevo.")
        except Exception as e2:
            logger.error(f"Error al enviar mensaje de error al grupo: {e2}", exc_info=True)

# -------------------------------------------------------------------
# Manejo de actualizaciones de miembros en el chat
async def manejar_miembros_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.chat_member:
        new_member = update.chat_member.new_chat_member
        if new_member.status == ChatMember.MEMBER and not context.user_data.get(f"bienvenido_{new_member.user.id}"):
            mensaje_bienvenida = f"¡Hola {new_member.user.first_name}!, te damos la bienvenida al bot del Comité de Manipulados Polo. Elige lo que quieres hacer:"
            teclado = InlineKeyboardMarkup([
                [InlineKeyboardButton("Menú privado", url=f"https://t.me/{BOT_USERNAME}?start=menu")]
            ])
            try:
                await context.bot.send_message(chat_id=new_member.user.id, text=mensaje_bienvenida, reply_markup=teclado)
                context.user_data[f"bienvenido_{new_member.user.id}"] = True
            except Exception as e:
                logger.error(f"No se pudo dar la bienvenida a {new_member.user.id}: {e}", exc_info=True)

# -------------------------------------------------------------------
# Manejo de errores
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, httpx.ReadError):
        logger.error(f"Error de conexión con Telegram: {context.error}", exc_info=True)
    elif hasattr(context.error, 'message') and "Forbidden" in str(context.error):
        logger.error(f"Error de permiso: {context.error}", exc_info=True)
    else:
        logger.error(f"Excepción al procesar una actualización: {context.error}", exc_info=True)
    try:
        if update and hasattr(update, 'effective_chat') and update.effective_chat:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Ocurrió un error inesperado. Los desarrolladores han sido notificados.")
    except Exception as e3:
        logger.error(f"Error al enviar mensaje de error al chat del usuario: {e3}", exc_info=True)

# -------------------------------------------------------------------
# Función para ejecutar el bot
def run_bot():
    try:
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("inicio", inicio))
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("documentacion", documentacion))
        application.add_handler(CallbackQueryHandler(registro_click_handler, pattern="^registro_click$"))
        application.add_handler(CallbackQueryHandler(inicio_click_handler, pattern="^inicio_click$"))
        application.add_handler(CallbackQueryHandler(manejar_menu_privado, pattern="^(menu_|perm_)"))
        application.add_handler(CallbackQueryHandler(manejar_botones))
        application.add_handler(ChatMemberHandler(manejar_miembros_chat, ChatMemberHandler.CHAT_MEMBER))
        application.add_error_handler(error_handler)
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Error crítico al iniciar el bot: {e}", exc_info=True)

if __name__ == "__main__":
    Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8080}).start()
    run_bot()
