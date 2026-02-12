import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# =====================
# ENV
# =====================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("BASE_URL")

DB_NAME = "data.db"

app = Flask(__name__)

# =====================
# DATABASE
# =====================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT,
            age INTEGER,
            salary REAL,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# =====================
# API ROUTES
# =====================

@app.route("/")
def home():
    return "SADDAM API IS RUNNING 🚀"

@app.route("/saddam-api/students", methods=["GET"])
def get_students():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT region, age, salary, created_at FROM students")
    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "region": r[0],
            "age": r[1],
            "salary": r[2],
            "created_at": r[3]
        }
        for r in rows
    ])

@app.route("/saddam-api/reset", methods=["POST"])
def reset_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students")
    conn.commit()
    conn.close()
    return jsonify({"status": "database cleared"})

# =====================
# TELEGRAM BOT (WEBHOOK)
# =====================

bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Viloyatingizni yozing:")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students")
    conn.commit()
    conn.close()
    await update.message.reply_text("Baza tozalandi 🗑")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    text = update.message.text

    if user_id not in user_data:
        user_data[user_id] = {}

    if "region" not in user_data[user_id]:
        user_data[user_id]["region"] = text
        await update.message.reply_text("Yoshingizni yozing:")
    elif "age" not in user_data[user_id]:
        user_data[user_id]["age"] = int(text)
        await update.message.reply_text("Oyligingizni yozing:")
    else:
        user_data[user_id]["salary"] = float(text)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO students (region, age, salary, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            user_data[user_id]["region"],
            user_data[user_id]["age"],
            user_data[user_id]["salary"],
            datetime.now()
        ))
        conn.commit()
        conn.close()

        await update.message.reply_text("Ma'lumot saqlandi ✅")
        user_data[user_id] = {}

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("clear", clear))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def telegram_webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return "ok"

# =====================
# WEBHOOK SETTER
# =====================

@app.route("/setwebhook")
async def set_webhook():
    await bot_app.initialize()
    await bot_app.bot.set_webhook(f"{BASE_URL}/{BOT_TOKEN}")
    return "Webhook set successfully ✅"
