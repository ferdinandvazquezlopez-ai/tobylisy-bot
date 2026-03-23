from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import yt_dlp
import os

TOKEN = "8096709051:AAGviaUIPV2icQYUjZIl9y53gMPrZGdSkyY"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    if "instagram.com" in text or "tiktok.com" in text:
        ydl_opts = {
            "outtmpl": "video.%(ext)s",
            "format": "mp4/best"
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=True)
                filename = ydl.prepare_filename(info)

            with open(filename, "rb") as f:
                await update.message.reply_video(video=f)
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
app.run_polling()
