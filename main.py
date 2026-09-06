import asyncio
import os
import re
import tempfile
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import yt_dlp
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.error import Forbidden, TelegramError


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(49 * 1024 * 1024)))
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}
YOUTUBE_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


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
        "Salom! YouTube havolasini yuboring. Men undan audio yoki video tayyorlayman.",
        reply_markup=MENU,
    )


def is_public_youtube_url(value: str) -> bool:
    if not YOUTUBE_URL_PATTERN.match(value):
        return False
    parsed = urlparse(value)
    return parsed.hostname is not None and parsed.hostname.lower() in YOUTUBE_HOSTS


def download_media(url: str, media_type: str, directory: str) -> Path:
    if media_type == "audio":
        options = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(directory, "%(title)s.%(ext)s"),
            "noplaylist": True,
            "restrictfilenames": True,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ],
        }
    else:
        options = {
            "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "merge_output_format": "mp4",
            "outtmpl": os.path.join(directory, "%(title)s.%(ext)s"),
            "noplaylist": True,
            "restrictfilenames": True,
        }

    with yt_dlp.YoutubeDL(options) as downloader:
        downloader.download([url])

    files = [
        path
        for path in Path(directory).iterdir()
        if path.is_file() and not path.name.endswith((".part", ".ytdl"))
    ]
    if len(files) != 1:
        raise RuntimeError("Yuklangan faylni aniqlab bo'lmadi.")
    return files[0]


async def download_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    url = context.user_data.pop("youtube_url", None)
    media_type = query.data
    if not url or media_type not in {"audio", "video"}:
        await query.edit_message_text("Havola eskirgan. YouTube havolasini qayta yuboring.")
        return

    await query.edit_message_text("Yuklanmoqda, biroz kuting...")
    try:
        with tempfile.TemporaryDirectory(prefix="youtube_") as directory:
            file_path = await asyncio.to_thread(
                download_media, url, media_type, directory
            )
            if file_path.stat().st_size > MAX_FILE_SIZE:
                await query.message.reply_text(
                    "Fayl Telegram limitidan katta. Boshqa, qisqaroq video tanlang."
                )
                return

            with file_path.open("rb") as media_file:
                if media_type == "audio":
                    await query.message.reply_audio(
                        audio=media_file, filename=file_path.name
                    )
                else:
                    await query.message.reply_video(
                        video=media_file, filename=file_path.name, supports_streaming=True
                    )
    except (yt_dlp.utils.DownloadError, OSError, RuntimeError, TelegramError) as error:
        print(f"YouTube yuklash xatosi: {error!r}")
        await query.message.reply_text(
            "Yuklab bo'lmadi. Havola ochiq va to'g'ri ekanini tekshiring."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if is_public_youtube_url(text):
        context.user_data["youtube_url"] = text
        await update.message.reply_text(
            "Qaysi format kerak?",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🎵 Audio", callback_data="audio"),
                        InlineKeyboardButton("🎬 Video", callback_data="video"),
                    ]
                ]
            ),
        )
        return

    answers = {
        "📋 Menyu": "📋 Menyu bo'limi.",
        "ℹ️ Ma'lumot": "ℹ️ Bu Telegram bot Python tilida yaratilgan.",
        "📞 Aloqa": "📞 Telefon: +998903544777\nTelegram: @jah0n_299",
        "❓ Yordam": "❓ Savolingizni yozing, yordam beramiz.",
    }

    answer = answers.get(
        text,
        "YouTube havolasini yuboring yoki menyudan birini tanlang.",
    )
    await update.message.reply_text(answer, reply_markup=MENU)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error

    if isinstance(error, Forbidden):
        print("Foydalanuvchi botni bloklagan yoki chatga kirish yopilgan.")
        return

    print(f"Kutilmagan xato: {error!r}")


def main():
    threading.Thread(target=start_health_server, daemon=True).start()

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(download_choice, pattern="^(audio|video)$"))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    application.add_error_handler(error_handler)

    print("Bot ishga tushdi...")
    application.run_polling()


if __name__ == "__main__":
    main()
