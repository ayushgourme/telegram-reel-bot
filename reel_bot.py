import os
import asyncio
import yt_dlp
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

# 🔴 PUT YOUR TELEGRAM USER ID HERE
ADMIN_ID = 7805477004  # replace with your ID

USER_FILE = "users.json"

# ---------------- USER SYSTEM ----------------
def load_users():
    try:
        with open(USER_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(list(users), f)

# ---------------- PROGRESS BAR ----------------
def progress_bar(percent):
    filled = int(percent / 5)
    return "█" * filled + "░" * (20 - filled)

# ---------------- DOWNLOAD ----------------
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

# ---------------- MAIN HANDLER ----------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # 🔹 Save user
    users = load_users()
    users.add(user_id)
    save_users(users)

    # 🔴 BROADCAST MODE
    if context.user_data.get("broadcast"):
        users = load_users()
        success = 0

        for user in users:
            try:
                await context.bot.copy_message(
                    chat_id=user,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )
                success += 1
            except:
                pass

        await update.message.reply_text(f"✅ Post delivered to {success} users")
        context.user_data["broadcast"] = False
        return

    # 🔹 NORMAL DOWNLOAD
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

# ---------------- ADMIN COMMANDS ----------------
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    users = load_users()
    await update.message.reply_text(f"👥 Total Users: {len(users)}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    context.user_data["broadcast"] = True
    await update.message.reply_text("📢 Send the post to broadcast (text/photo/video/etc.)")

# ---------------- APP ----------------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("users", users_command))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

print("Bot running...")
app.run_polling()
