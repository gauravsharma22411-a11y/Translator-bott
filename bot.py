BOT_TOKEN = "8782523144:AAGJ-xOKaUQiTpwI1g7zo-yi9dAur6yYYCM"

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

DB_FILE = "groups.db"


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

    cur.execute(
        "INSERT OR REPLACE INTO groups(chat_id,status) VALUES (?,?)",
        (chat_id, status)
    )

    conn.commit()
    conn.close()


def get_status(chat_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("SELECT status FROM groups WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    conn.close()

    return row[0] if row else "off"


# ================= LANGUAGE FILTERS ================= #

def is_english(text):
    text = text.lower()
    words = set(text.split())

    english_words = {
        "how", "are", "you", "what", "why", "hello",
        "good", "morning", "night", "bro", "thanks"
    }

    ascii_ratio = sum(c.isascii() for c in text) / max(len(text), 1)

    return ascii_ratio > 0.85 or len(words.intersection(english_words)) >= 2


def is_hinglish(text):
    words = text.lower().split()

    vocab = {
        "aap", "kaise", "ho", "tum", "kya", "hai", "nahi", "haan",
        "main", "mai", "mera", "ka", "ke", "ki", "aur", "acha",
        "theek", "kyun", "kyuki", "kab", "kahan", "kaun", "hoon"
    }

    return sum(1 for w in words if w in vocab) >= 2


# ================= COMMANDS ================= #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Translator Bot Ready\n\n"
        "/on - enable group translation\n"
        "/off - disable group translation\n\n"
        "💬 DM me text → instant translation"
    )


async def on_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Use /on inside a group")
        return

    set_status(chat.id, "on")
    await update.message.reply_text("✅ Auto Translation ON")


async def off_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Use /off inside a group")
        return

    set_status(chat.id, "off")
    await update.message.reply_text("❌ Auto Translation OFF")


# ================= CORE HANDLER ================= #

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message:
        return

    chat_type = update.effective_chat.type
    text = update.message.text

    if not text:
        return

    print("CHAT TYPE:", chat_type)
    print("TEXT:", text)

    # ---------- PRIVATE CHAT ---------- #
    if chat_type == "private":
        try:
            translated = GoogleTranslator(source="auto", target="en").translate(text)
            await update.message.reply_text(f"🌍 {translated}")
        except Exception as e:
            print("DM ERROR:", e)
        return

    # ---------- GROUP CHAT ---------- #
    status = get_status(update.effective_chat.id)

    print("GROUP STATUS:", status)

    if status != "on":
        return

    # FILTERS
    if is_english(text):
        return

    if is_hinglish(text):
        return

    if any("\u0900" <= c <= "\u097F" for c in text):
        return

    # TRANSLATE
    try:
        translated = GoogleTranslator(source="auto", target="en").translate(text)
        await update.message.reply_text(f"🌐 {translated}")
    except Exception as e:
        print("GROUP ERROR:", e)


# ================= MAIN ================= #

def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("on", on_cmd))
    app.add_handler(CommandHandler("off", off_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🚀 BOT RUNNING...")
    app.run_polling()


if __name__ == "__main__":
    main()
