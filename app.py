import os
import sqlite3
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

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
            gender TEXT,
            age INTEGER,
            salary INTEGER,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# =====================
# TELEGRAM BOT SETUP
# =====================

bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
user_data = {}

# 🔥 STABLE EVENT LOOP
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(bot_app.initialize())

# =====================
# DATA LISTS
# =====================

REGIONS = [
    "Toshkent", "Toshkent viloyati", "Samarqand", "Buxoro",
    "Andijon", "Farg‘ona", "Namangan", "Qashqadaryo",
    "Surxondaryo", "Xorazm", "Jizzax", "Sirdaryo"
]

GENDERS = ["O‘g‘il bola", "Qiz bola"]

AGES = [str(i) for i in range(15, 51)]

SALARY_VALUES = list(range(5, 21))  # 5 mln → 20 mln
SALARIES = [f"{i} mln" for i in SALARY_VALUES]

# =====================
# BOT COMMANDS
# =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user_data[user_id] = {}

    keyboard = [[KeyboardButton(r)] for r in REGIONS]

    await update.message.reply_text(
        "Assalomu alaykum!\n\nViloyatingizni tanlang:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )


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

    # 1️⃣ REGION
    if "region" not in user_data[user_id]:
        if text not in REGIONS:
            return
        user_data[user_id]["region"] = text

        keyboard = [[KeyboardButton(g)] for g in GENDERS]
        await update.message.reply_text(
            "Jinsingizni tanlang:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    # 2️⃣ GENDER
    if "gender" not in user_data[user_id]:
        if text not in GENDERS:
            return
        user_data[user_id]["gender"] = text

        keyboard = [AGES[i:i+6] for i in range(0, len(AGES), 6)]
        await update.message.reply_text(
            "Yoshingizni tanlang:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    # 3️⃣ AGE
    if "age" not in user_data[user_id]:
        if text not in AGES:
            return
        user_data[user_id]["age"] = int(text)

        keyboard = [SALARIES[i:i+4] for i in range(0, len(SALARIES), 4)]
        await update.message.reply_text(
            "Oyligingizni tanlang:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    # 4️⃣ SALARY
    if "salary" not in user_data[user_id]:
        if text not in SALARIES:
            return

        salary_number = int(text.split()[0])
        salary_int = salary_number * 1_000_000

        user_data[user_id]["salary"] = salary_int

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO students (region, gender, age, salary, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_data[user_id]["region"],
            user_data[user_id]["gender"],
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
    cursor.execute("SELECT region, gender, age, salary, created_at FROM students")
    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "region": r[0],
            "gender": r[1],
            "age": r[2],
            "salary": r[3],
            "created_at": r[4]
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
# WEBHOOK
# =====================

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)
    loop.run_until_complete(bot_app.process_update(update))
    return "ok"

@app.route("/setwebhook")
def set_webhook():
    loop.run_until_complete(
        bot_app.bot.set_webhook(f"{BASE_URL}/{BOT_TOKEN}")
    )
    return "Webhook set successfully ✅"

