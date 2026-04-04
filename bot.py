import os
import time
import telebot
from flask import Flask
from threading import Thread

# 1. Initialize Flask for Render (Tricks Render into staying alive)
app = Flask('')

@app.route('/')
def home():
    return "MMI Assignment Tracker is running!"

def run_web_server():
    # Render automatically provides a 'PORT' environment variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. Initialize Telegram Bot
# Ensure your Token is set in Render's Environment Variables
BOT_TOKEN = os.environ.get("8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s") 
bot = telebot.TeleBot(BOT_TOKEN)

# --- YOUR DATABASE LOGIC (Example) ---
def get_db_connection():
    # Replace this with your actual DB connection logic (psycopg2, sqlite, etc.)
    # Example: conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    # For now, we simulate a failure to match your error log
    raise Exception("Database connection failed.") 

# 3. Bot Handlers
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Welcome to MMI Assignment Tracker!")

@bot.message_handler(commands=['active'])
def show_active_assignments(message):
    try:
        # Try your database operation
        # connection = get_db_connection()
        # ... logic to fetch assignments ...
        bot.send_message(message.chat.id, "Searching for active assignments...")
        
        # Simulate your logic
        raise Exception("DB Connection Error") 

    except Exception as e:
        print(f"Error in show_active_assignments: {e}")
        # FIX: Use send_message instead of reply_to to avoid 400 Error
        bot.send_message(message.chat.id, "❌ Database connection failed. Please check Render logs.")

# 4. Main Execution Block
if __name__ == "__main__":
    # Start the Flask web server in a background thread
    print("Starting Keep-Alive Server...")
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

    # Small delay to let old instances on Render shut down (Fixes 409 Conflict)
    print("Waiting for old instances to clear...")
    time.sleep(5)

    print("Bot is now polling...")
    while True:
        try:
            # infinity_polling handles network flickers automatically
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(15) # Wait before restarting if a crash occurs
