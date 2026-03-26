import os
import asyncio
import yt_dlp
import glob
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ✅ CONFIG
USERS_FILE = "users.txt"
ADMIN_ID = 7805477004

# -------- USER SYSTEM --------
def load_users():
    if not os.path.exists(USERS_FILE):
        return set()
    with open(USERS_FILE, "r") as f:
        return set(f.read().splitlines())

def save_user(user_id):
    users = load_users()
    if str(user_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")

# -------- PROGRESS BAR --------
def progress_bar(percent):
    filled = int(percent / 5)
    return "█" * filled + "░" * (20 - filled)

# -------- DOWNLOAD --------
async def download_with_progress(url, message):
    loop = asyncio.get_event_loop()
    progress_data = {"percent": 0}

    def hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                progress_data["percent"] = downloaded / total * 100

    ydl_opts = {
        'format': 'mp4',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True,
        'progress_hooks': [hook],
        'noplaylist': True,
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
                await message.edit_text(f"📥 Downloading...\n\n[{bar}] {percent:.1f}%")
            except:
                pass
            last = int(percent)
        await asyncio.sleep(1)

    files = glob.glob("*.mp4")
    return files[0] if files else None

# -------- MAIN HANDLER --------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    save_user(user_id)

    # 🔴 BROADCAST MODE
    if context.user_data.get("broadcast"):
        users = load_users()
        success = 0

        for user in users:
            try:
                await context.bot.copy_message(
                    chat_id=int(user),
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )
                success += 1
            except:
                pass

        await update.message.reply_text(f"✅ Post delivered to {success} users")
        context.user_data["broadcast"] = False
        return

    # 🔹 DOWNLOAD
    url = update.message.text

    if "instagram.com" not in url:
        await update.message.reply_text("❌ Send Instagram Reel link")
        return

    msg = await update.message.reply_text("⏳ Starting...")

    try:
        file_path = await download_with_progress(url, msg)
        await msg.edit_text("📤 Uploading...")

        if file_path:
            await update.message.reply_video(video=open(file_path, 'rb'))
            os.remove(file_path)
        else:
            await update.message.reply_text("❌ Download failed")

    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")

# -------- ADMIN COMMANDS --------
# -------- ADMIN COMMANDS --------
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    users = load_users()
    await update.message.reply_text(f"👥 Total Users: {len(users)}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    context.user_data["broadcast"] = True
    await update.message.reply_text("📢 Send the post to broadcast")

# -------- APP --------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("users", users_command))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))

print("Bot running...")
app.run_polling()
