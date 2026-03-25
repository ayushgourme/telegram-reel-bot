import os
import asyncio
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

import os
BOT_TOKEN = os.getenv("BOT_TOKEN")

def progress_bar(percent):
    filled = int(percent / 5)
    return "█" * filled + "░" * (20 - filled)

async def download_with_progress(url, message):
    loop = asyncio.get_event_loop()
    progress_data = {"percent": 0}

    def hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)

            if total:
                percent = downloaded / total * 100
                progress_data["percent"] = percent

    ydl_opts = {
        'format': 'mp4',
        'outtmpl': 'video.%(ext)s',
        'quiet': True,
        'progress_hooks': [hook],
        'noplaylist': True,
        'concurrent_fragment_downloads': 5,
    }

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    task = loop.run_in_executor(None, run)

    last = 0

    while not task.done():
        percent = progress_data["percent"]

        if int(percent) != last:
            bar = progress_bar(percent)

            try:
                await message.edit_text(
                    f"📥 Downloading...\n\n[{bar}] {percent:.1f}%"
                )
            except:
                pass

            last = int(percent)

        await asyncio.sleep(1)

    return "video.mp4"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text

    if "instagram.com" not in url:
        await update.message.reply_text("❌ Send Instagram Reel link")
        return

    msg = await update.message.reply_text("⏳ Starting...")

    try:
        file_path = await download_with_progress(url, msg)

        await msg.edit_text("📤 Uploading...")

        await update.message.reply_video(video=open(file_path, 'rb'))

        os.remove(file_path)

    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running...")
app.run_polling()