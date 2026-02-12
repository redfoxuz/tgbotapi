import os
import sqlite3
import threading
from datetime import datetime
from flask import Flask, request, jsonify
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ============================
# ENV VARIABLES (Renderdan keladi)
# ============================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("BASE_URL")  # Masalan: https://saddam-api.onrender.com

DB_NAME = "data.db"

# ============================
# FLASK API
# ============================

app = Flask(__name__)

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

@app.route("/saddam-api/students", methods=["POST"])
def add_student():
    data = request.json

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO students (region, age, salary, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        data.get("region"),
        data.get("age"),
        data.get("salary"),
        datetime.now()
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "saved in saddam-api"})


@app.route("/saddam-api/students", methods=["GET"])
def get_students():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT region, age, salary, created_at FROM students")
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "region": row[0],
            "age": row[1],
            "salary": row[2],
            "created_at": row[3]
        })

    return jsonify(result)


@app.route("/saddam-api/reset", methods=["POST"])
def reset_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students")
    conn.commit()
    conn.close()

    return jsonify({"status": "saddam-api database cleared"})


# ============================
# TELEGRAM BOT
# ============================

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Viloyatingizni yozing:")

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

        requests.post(
            f"{BASE_URL}/saddam-api/students",
            json=user_data[user_id]
        )

        await update.message.reply_text("Ma'lumot saqlandi ✅")
        user_data[user_id] = {}

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    requests.post(f"{BASE_URL}/saddam-api/reset")
    await update.message.reply_text("Baza tozalandi 🗑")


# ============================
# START TELEGRAM BOT AUTOMATICALLY
# ============================

def start_bot():
    bot = ApplicationBuilder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("clear", clear))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    bot.run_polling()

# Flask yuklanganda bot ham start bo‘ladi
threading.Thread(target=start_bot).start()



# ============================
# RUN BOTH
# ============================

if __name__ == "__main__":
    app.run()


