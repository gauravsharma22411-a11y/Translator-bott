import os
import time
import sqlite3
from deep_translator import GoogleTranslator

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG ================= #

BOT_TOKEN = os.getenv("8782523144:AAGJ-xOKaUQiTpwI1g7zo-yi9dAur6yYYCM")

DB_FILE = "groups.db"

# ================= SAFETY CHECK ================= #

if not BOT_TOKEN:
    print("❌ BOT_TOKEN is missing in environment variables")

# ================= DATABASE ================= #

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            status TEXT DEFAULT 'off'
        )
    """)
    conn.commit()
    conn.close()

def set_status(chat_id, status):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO groups VALUES (?,?)", (chat_id, status))
    conn.commit()
    conn.close()

def get_status(chat_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT status FROM groups WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else "off"

# ================= ANTI-SPAM ================= #

last_msg_time = {}

def is_spam(user_id):
    now = time.time()
    if user_id in last_msg_time:
        if now - last_msg_time[user_id] < 2:
            return True
    last_msg_time[user_id] = now
    return False

# ================= LANGUAGE FILTER ================= #

def should_translate(text: str) -> bool:
    text_low = text.lower()

    hinglish_words = {
        "aap", "kaise", "ho", "kya", "hai", "nahi", "haan",
        "main", "mai", "tum", "mera", "acha", "theek", "kyun"
    }

    words = set(text_low.split())

    # skip Hinglish
    if len(words.intersection(hinglish_words)) >= 2:
        return False

    # skip Hindi script
    if any("\u0900" <= c <= "\u097F" for c in text):
        return False

    # skip normal English
    ascii_ratio = sum(c.isascii() for c in text) / max(len(text), 1)
    if ascii_ratio > 0.85:
        return False

    return True

# ================= COMMANDS ================= #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Translator Bot Active\n\n"
        "/on - enable translation in group\n"
        "/off - disable translation\n\n"
        "💬 DM me for instant translation"
    )

async def on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_status(update.effective_chat.id, "on")
    await update.message.reply_text("✅ Translation ENABLED")

async def off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_status(update.effective_chat.id, "off")
    await update.message.reply_text("❌ Translation DISABLED")

# ================= CORE HANDLER ================= #

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    text = update.message.text
    if not text:
        return

    chat_type = update.effective_chat.type

    # ================= DM ================= #
    if chat_type == "private":
        try:
            translated = GoogleTranslator(source="auto", target="en").translate(text)
            await update.message.reply_text(translated)
        except Exception as e:
            print("DM ERROR:", e)
        return

    # ================= GROUP ================= #
    if get_status(update.effective_chat.id) != "on":
        return

    if is_spam(update.effective_user.id):
        return

    if not should_translate(text):
        return

    try:
        translated = GoogleTranslator(source="auto", target="en").translate(text)
        await update.message.reply_text(translated)
    except Exception as e:
        print("GROUP ERROR:", e)

# ================= MAIN ================= #

def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("on", on))
    app.add_handler(CommandHandler("off", off))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
