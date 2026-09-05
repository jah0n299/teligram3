import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        return


def start_health_server():
    port = int(os.getenv("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


MENU = ReplyKeyboardMarkup(
    [
        ["📋 Menyu", "ℹ️ Ma'lumot"],
        ["📞 Aloqa", "❓ Yordam"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Kerakli bo'limni tanlang:",
        reply_markup=MENU,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answers = {
        "📋 Menyu": "📋 Menyu bo'limi.",
        "ℹ️ Ma'lumot": "ℹ️ Bu Telegram bot Python tilida yaratilgan.",
        "📞 Aloqa": "📞 Telefon: +998903544777\nTelegram: @jah0n_299",
        "❓ Yordam": "❓ Savolingizni yozing, yordam beramiz.",
    }

    answer = answers.get(
        update.message.text,
        "Iltimos, menyudan birini tanlang.",
    )
    await update.message.reply_text(answer, reply_markup=MENU)


def main():
    threading.Thread(target=start_health_server, daemon=True).start()

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("Bot ishga tushdi...")
    application.run_polling()


if __name__ == "__main__":
    main()