import asyncio
import requests
import threading
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ================== CONFIG ==================
BOT_TOKEN = "8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s"
API_URL = "https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
# ===========================================

# ... (keep all your helper functions: fetch_data, format_time_ago, etc.) ...

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... your existing code ...

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... your existing code ...

def main():
    print("🚀 Starting Assignment Tracking Bot on Render...")
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # This is the key: run_polling is blocking and handles the event loop itself
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Keep-alive thread for Render free tier (this is fine)
    def keep_alive():
        while True:
            print(f"[{time.strftime('%H:%M:%S')}] Bot keep-alive ping...")
            time.sleep(240)  # every 4 minutes

    threading.Thread(target=keep_alive, daemon=True).start()

    main()   # ← No asyncio.run() here
