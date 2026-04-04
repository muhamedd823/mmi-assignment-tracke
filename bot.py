import os
import time
import telebot
from flask import Flask
from threading import Thread

# 1. THE TOKEN
# I am putting your token here directly as requested.
# If you ever make your GitHub repo "Public", anyone can steal this!
BOT_TOKEN = "8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s"

# 2. FLASK SERVER (Required for Render Free Tier)
app = Flask('')

@app.route('/')
def home():
    return "MMI Assignment Tracker is Online!"

def run_web_server():
    # Render provides the PORT variable; we use 10000 as a default
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 3. INITIALIZE BOT
bot = telebot.TeleBot(BOT_TOKEN)

# 4. BOT COMMANDS
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 Hello! MMI Assignment Tracker is active.\n\n"
        "Available commands:\n"
        "/active - Show active assignments\n"
        "/status - Check bot connection"
    )
    bot.send_message(message.chat.id, welcome_text)

@bot.message_handler(commands=['status'])
def check_status(message):
    bot.send_message(message.chat.id, "✅ Bot is running smoothly on Render!")

@bot.message_handler(commands=['active'])
def show_active_assignments(message):
    # This is where your database/scraping logic goes
    try:
        # For now, a placeholder message to prove it works
        bot.send_message(message.chat.id, "📂 Fetching active assignments from the database...")
        
        # Example: if you have a database connection error:
        # bot.send_message(message.chat.id, "❌ Database connection failed.")
    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(message.chat.id, "⚠️ An error occurred while fetching data.")

# 5. MAIN EXECUTION
if __name__ == "__main__":
    # Start Flask in a separate thread so it doesn't block the bot
    print("Starting Flask web server...")
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

    # Small delay to prevent '409 Conflict' during Render redeploys
    print("Waiting 5 seconds for old instances to clear...")
    time.sleep(5)

    print("Bot is now polling...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(15) # Wait before restarting
