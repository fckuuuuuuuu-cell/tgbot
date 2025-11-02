#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Telegram optimizado para iSH (iOS)
Almacenamiento local en CSV con autenticación
"""

import os
import csv
import random
import datetime
import logging
from telegram import (
    ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, Update
)
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, CallbackContext
)

# ---------- CONFIGURACIÓN ----------
# Configurar logging para iSH
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Directorios para iSH
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
SERVICES = ["disney", "netflix", "spotify", "hbo", "paramount", "starplus"]

VALID_PASSWORDS = {"kaiorsama", "escobar"}
SESSIONS = {}

# Token del bot - REEMPLAZA CON TU TOKEN REAL
TOKEN = "8209038816:AAFD6k0wVXX2os1GITLGa2rUUrvZgVvbZHA"
# -----------------------------------

# ---------- INICIALIZACIÓN ----------
def setup_directories_and_files():
    """Crea carpetas y archivos necesarios para iSH"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)
        
        for service in SERVICES:
            csv_path = os.path.join(DATA_DIR, f"{service}.csv")
            used_path = os.path.join(DATA_DIR, f"{service}_used.csv")
            
            # Crear archivo principal si no existe
            if not os.path.exists(csv_path):
                with open(csv_path, "w", encoding="utf-8") as f:
                    f.write("account,added_by,added_at\n")
            
            # Crear archivo de usadas si no existe
            if not os.path.exists(used_path):
                with open(used_path, "w", encoding="utf-8") as f:
                    f.write("account,added_by,dispensed_at\n")
        
        # Crear archivo de log
        log_file = os.path.join(LOG_DIR, "dispensed.log")
        if not os.path.exists(log_file):
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("")
                
        logger.info("Directorios y archivos inicializados correctamente")
        
    except Exception as e:
        logger.error(f"Error en inicialización: {e}")

setup_directories_and_files()
# -----------------------------------

# ---------- FUNCIONES CSV OPTIMIZADAS ----------
def get_csv_path(service):
    return os.path.join(DATA_DIR, f"{service.lower()}.csv")

def get_used_csv_path(service):
    return os.path.join(DATA_DIR, f"{service.lower()}_used.csv")

def append_row(path, row):
    """Añade una fila al CSV de forma segura para iSH"""
    try:
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
        return True
    except Exception as e:
        logger.error(f"Error append_row: {e}")
        return False

def add_account_to_service(service, account, added_by):
    """Añade cuenta a un servicio"""
    timestamp = datetime.datetime.utcnow().isoformat()
    return append_row(get_csv_path(service), [account.strip(), added_by, timestamp])

def read_service_rows(service):
    """Lee filas de un servicio (ignora encabezado)"""
    path = get_csv_path(service)
    if not os.path.exists(path):
        return []
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
            return rows[1:] if len(rows) > 1 else []  # Ignora encabezado
    except Exception as e:
        logger.error(f"Error read_service_rows: {e}")
        return []

def write_service_rows(service, rows):
    """Escribe filas en un servicio"""
    path = get_csv_path(service)
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["account", "added_by", "added_at"])
            writer.writerows(rows)
        return True
    except Exception as e:
        logger.error(f"Error write_service_rows: {e}")
        return False

def pick_and_remove_random(service):
    """Selecciona y elimina una cuenta aleatoria"""
    rows = read_service_rows(service)
    if not rows:
        return None
    
    try:
        idx = random.randrange(len(rows))
        picked = rows.pop(idx)
        
        if write_service_rows(service, rows):
            # Registrar en archivo de usadas
            timestamp = datetime.datetime.utcnow().isoformat()
            append_row(get_used_csv_path(service), [picked[0], picked[1], timestamp])
            return picked
        return None
    except Exception as e:
        logger.error(f"Error pick_and_remove_random: {e}")
        return None
# -----------------------------------

# ---------- AUTENTICACIÓN ----------
def is_authenticated(uid):
    return uid in SESSIONS

def require_auth(func):
    def wrapper(update: Update, context: CallbackContext):
        uid = update.effective_user.id
        if not is_authenticated(uid):
            update.message.reply_text("🔒 Debes iniciar sesión con /login <contraseña>")
            return
        return func(update, context)
    return wrapper
# -----------------------------------

# ---------- COMANDOS PRINCIPALES ----------
def start(update: Update, context: CallbackContext):
    """Comando de inicio"""
    text = (
        "🤖 *Bot operativo en iSH*\n\n"
        "Primero inicia sesión:\n"
        "`/login <contraseña>`\n\n"
        "Luego usa `/menu` para el panel con botones."
    )
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

def login(update: Update, context: CallbackContext):
    """Comando de login"""
    if len(context.args) != 1:
        update.message.reply_text("Uso: /login <contraseña>")
        return
    
    pwd = context.args[0].strip()
    uid = update.effective_user.id
    user = update.effective_user.username or update.effective_user.first_name
    
    if pwd in VALID_PASSWORDS:
        SESSIONS[uid] = {
            "user": user, 
            "pwd": pwd, 
            "logged_at": datetime.datetime.utcnow().isoformat()
        }
        update.message.reply_text(
            f"✅ Autenticado como *{user}*\nUsa /menu para el panel.",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"Usuario autenticado: {user} (ID: {uid})")
    else:
        update.message.reply_text("❌ Contraseña incorrecta")
        logger.warning(f"Intento de login fallido: {user} (ID: {uid})")

@require_auth
def menu(update: Update, context: CallbackContext):
    """Muestra el menú principal con botones"""
    keyboard = [
        [InlineKeyboardButton("🧾 Listar servicios", callback_data="listar")],
        [InlineKeyboardButton("➕ Agregar cuenta", callback_data="agregar")],
        [InlineKeyboardButton("🎁 Obtener cuenta", callback_data="get")],
        [InlineKeyboardButton("🔢 Contar cuentas", callback_data="contar")],
        [InlineKeyboardButton("🔓 Cerrar sesión", callback_data="logout")]
    ]
    update.message.reply_text(
        "📋 *Panel principal:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

@require_auth
def agregar(update: Update, context: CallbackContext):
    """Agrega una cuenta a un servicio"""
    if len(context.args) < 2:
        update.message.reply_text("Uso: /agregar <servicio> email:pass")
        return
    
    service = context.args[0].lower()
    if service not in SERVICES:
        update.message.reply_text(f"❌ Servicio desconocido: {service}")
        return
    
    account = " ".join(context.args[1:]).strip()

    # Validar formato básico
    if ":" not in account:
        update.message.reply_text("⚠️ Formato inválido. Usa: email:pass")
        return
    
    if " " in account.split(":")[1]:  # No espacios en la contraseña
        update.message.reply_text("⚠️ No uses espacios en la contraseña")
        return

    added_by = SESSIONS[update.effective_user.id]["user"]
    if add_account_to_service(service, account, added_by):
        total = len(read_service_rows(service))
        update.message.reply_text(
            f"✅ Cuenta agregada a *{service}*\nTotal: {total}", 
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"Cuenta agregada a {service} por {added_by}")
    else:
        update.message.reply_text("❌ Error al agregar la cuenta")

# ---------- MANEJADOR DE BOTONES ----------
def button_handler(update: Update, context: CallbackContext):
    """Maneja todos los callbacks de los botones"""
    query = update.callback_query
    query.answer()
    uid = query.from_user.id

    if not is_authenticated(uid):
        query.edit_message_text("🔒 Sesión expirada. Usa /login")
        return

    data = query.data
    user_info = SESSIONS[uid]

    try:
        if data == "listar":
            files = [f[:-4] for f in os.listdir(DATA_DIR) 
                    if f.endswith(".csv") and not f.endswith("_used.csv")]
            text = "📂 *Servicios disponibles:*\n" + "\n".join(f"• {f}" for f in files)
            query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

        elif data == "agregar":
            query.edit_message_text(
                "📤 Usa el comando:\n`/agregar <servicio> email:pass`", 
                parse_mode=ParseMode.MARKDOWN
            )

        elif data == "get":
            files = [f[:-4] for f in os.listdir(DATA_DIR) 
                    if f.endswith(".csv") and not f.endswith("_used.csv")]
            if not files:
                query.edit_message_text("❌ No hay servicios disponibles")
                return
                
            keyboard = [[InlineKeyboardButton(s, callback_data=f"get_{s}")] for s in files]
            query.edit_message_text(
                "🎁 Selecciona un servicio:", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data.startswith("get_"):
            service = data.split("_", 1)[1]
            picked = pick_and_remove_random(service)
            
            if picked is None:
                query.edit_message_text(
                    f"❌ No hay cuentas para *{service}*", 
                    parse_mode=ParseMode.MARKDOWN
                )
                return
                
            account = picked[0]
            query.edit_message_text(
                f"🎁 Cuenta de *{service}*:\n`{account}`", 
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Cuenta dispensada de {service} para {user_info['user']}")

        elif data == "contar":
            text = "📦 *Cuentas disponibles:*\n"
            for service in SERVICES:
                count = len(read_service_rows(service))
                text += f"• {service}: {count}\n"
            query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

        elif data == "logout":
            del SESSIONS[uid]
            query.edit_message_text("🔓 Sesión cerrada correctamente")
            logger.info(f"Usuario {user_info['user']} cerró sesión")

    except Exception as e:
        logger.error(f"Error en button_handler: {e}")
        query.edit_message_text("❌ Error interno del bot")

# ---------- FUNCIÓN PRINCIPAL ----------
def main():
    """Función principal optimizada para iSH"""
    try:
        logger.info("Iniciando bot para iSH...")
        
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher

        # Handlers
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("login", login))
        dp.add_handler(CommandHandler("menu", menu))
        dp.add_handler(CommandHandler("agregar", agregar))
        dp.add_handler(CallbackQueryHandler(button_handler))

        # Iniciar bot
        updater.start_polling()
        logger.info("🤖 Bot iniciado correctamente en iSH")
        
        # Mantener el bot corriendo
        updater.idle()
        
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
