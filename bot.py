#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Telegram con almacenamiento local en CSV y botones.
Diseñado para funcionar en Termux.
Formato de cuentas: email:pass
"""

import os
import csv
import random
import datetime
import re
from telegram import (
    ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, Update
)
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, CallbackContext
)

# ---------- CONFIGURACIÓN ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
SERVICES = ["disney", "netflix", "spotify", "hbo", "paramount", "starplus"]

VALID_PASSWORDS = {"kaiorsama", "escobar"}
SESSIONS = {}

TOKEN = "8209038816:AAFD6k0wVXX2os1GITLGa2rUUrvZgVvbZHA"  # ← reemplaza con tu token real
# -----------------------------------

# ---------- INICIALIZACIÓN ----------
def setup_directories_and_files():
    """Crea las carpetas y archivos necesarios automáticamente."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    for service in SERVICES:
        csv_path = os.path.join(DATA_DIR, f"{service}.csv")
        used_path = os.path.join(DATA_DIR, f"{service}_used.csv")
        if not os.path.exists(csv_path):
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["account", "added_by", "added_at"])
        if not os.path.exists(used_path):
            with open(used_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["account", "added_by", "dispensed_at"])

    log_file = os.path.join(LOG_DIR, "dispensed.log")
    if not os.path.exists(log_file):
        open(log_file, "w", encoding="utf-8").close()

setup_directories_and_files()
# -----------------------------------


# ---------- FUNCIONES CSV ----------
def get_csv_path(service):
    return os.path.join(DATA_DIR, f"{service.lower()}.csv")

def get_used_csv_path(service):
    return os.path.join(DATA_DIR, f"{service.lower()}_used.csv")

def append_row(path, row):
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)

def add_account_to_service(service, account, added_by):
    append_row(get_csv_path(service), [account.strip(), added_by, datetime.datetime.utcnow().isoformat()])

def read_service_rows(service):
    path = get_csv_path(service)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.reader(f))[1:]  # ignora encabezado

def write_service_rows(service, rows):
    path = get_csv_path(service)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["account", "added_by", "added_at"])
        writer.writerows(rows)

def pick_and_remove_random(service):
    rows = read_service_rows(service)
    if not rows:
        return None
    idx = random.randrange(len(rows))
    picked = rows.pop(idx)
    write_service_rows(service, rows)
    append_row(get_used_csv_path(service), [picked[0], picked[1], datetime.datetime.utcnow().isoformat()])
    return picked
# -----------------------------------


# ---------- AUTENTICACIÓN ----------
def is_authenticated(uid):
    return uid in SESSIONS

def require_auth(func):
    def wrapper(update: Update, context: CallbackContext):
        uid = update.effective_user.id
        if not is_authenticated(uid):
            update.message.reply_text("🔒 Debes iniciar sesión con /login <contraseña>.")
            return
        return func(update, context)
    return wrapper
# -----------------------------------


# ---------- INTERFAZ ----------
def start(update: Update, context: CallbackContext):
    text = (
        "🤖 *Bot operativo.*\n\n"
        "Primero inicia sesión con:\n"
        "`/login <contraseña>`\n\n"
        "Luego usa `/menu` para abrir el panel con botones."
    )
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

def login(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        update.message.reply_text("Uso: /login <contraseña>")
        return
    pwd = context.args[0].strip()
    uid = update.effective_user.id
    user = update.effective_user.username or update.effective_user.first_name
    if pwd in VALID_PASSWORDS:
        SESSIONS[uid] = {"user": user, "pwd": pwd, "logged_at": datetime.datetime.utcnow().isoformat()}
        update.message.reply_text(
            f"✅ Autenticado como *{user}*.\nUsa /menu para abrir el panel.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        update.message.reply_text("❌ Contraseña incorrecta.")

@require_auth
def menu(update: Update, context: CallbackContext):
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

# ---------- CALLBACKS ----------
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    uid = query.from_user.id

    if not is_authenticated(uid):
        query.edit_message_text("🔒 Debes iniciar sesión con /login <contraseña>.")
        return

    data = query.data

    if data == "listar":
        files = [f[:-4] for f in os.listdir(DATA_DIR) if f.endswith(".csv") and not f.endswith("_used.csv")]
        text = "📂 *Servicios disponibles:*\n" + "\n".join(files)
        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

    elif data == "agregar":
        query.edit_message_text("📤 Usa el comando:\n`/agregar <servicio> email:pass`", parse_mode=ParseMode.MARKDOWN)

    elif data == "get":
        files = [f[:-4] for f in os.listdir(DATA_DIR) if f.endswith(".csv") and not f.endswith("_used.csv")]
        keyboard = [[InlineKeyboardButton(s, callback_data=f"get_{s}")] for s in files]
        query.edit_message_text("Selecciona un servicio:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("get_"):
        service = data.split("_", 1)[1]
        picked = pick_and_remove_random(service)
        if picked is None:
            query.edit_message_text(f"❌ No hay cuentas disponibles para *{service}*.", parse_mode=ParseMode.MARKDOWN)
            return
        account = picked[0]
        query.edit_message_text(f"🎁 Cuenta de *{service}*:\n`{account}`", parse_mode=ParseMode.MARKDOWN)

    elif data == "contar":
        text = "📦 *Cuentas disponibles:*\n"
        for s in SERVICES:
            count = len(read_service_rows(s))
            text += f"- {s}: {count}\n"
        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

    elif data == "logout":
        if uid in SESSIONS:
            del SESSIONS[uid]
            query.edit_message_text("🔓 Sesión cerrada correctamente.")
        else:
            query.edit_message_text("No estabas autenticado.")
# -----------------------------------


# ---------- COMANDOS ----------
@require_auth
def agregar(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        update.message.reply_text("Uso: /agregar <servicio> email:pass")
        return
    service = context.args[0].lower()
    if service not in SERVICES:
        update.message.reply_text(f"❌ Servicio desconocido: {service}")
        return
    account = " ".join(context.args[1:]).strip()

    # Validar formato "email:pass" (acepta sin @ pero con :)
    if ":" not in account:
        update.message.reply_text("⚠️ Formato inválido. Usa: email:pass")
        return
    if " " in account:
        update.message.reply_text("⚠️ No uses espacios. Formato: email:pass")
        return

    added_by = SESSIONS[update.effective_user.id]["user"]
    add_account_to_service(service, account, added_by)
    total = len(read_service_rows(service))
    update.message.reply_text(f"✅ Cuenta agregada a *{service}*.\nTotal ahora: {total}", parse_mode=ParseMode.MARKDOWN)
# -----------------------------------


# ---------- MAIN ----------
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("login", login))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("agregar", agregar))
    dp.add_handler(CallbackQueryHandler(button_handler))

    updater.start_polling()
    print("🤖 Bot corriendo con formato email:pass y autogeneración de archivos...")
    updater.idle()

if __name__ == "__main__":
    main()