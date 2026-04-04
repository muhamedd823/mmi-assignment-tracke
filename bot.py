import os
import time
import telebot
from flask import Flask
from threading import Thread
from curl_cffi import requests as cur_requests

# 1. CONFIGURATION
# It's better to keep these in Render Environment Variables, but I've put them here as requested.
BOT_TOKEN = "8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s"
API_URL = "https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# 2. KEEP-ALIVE SERVER FOR RENDER
@app.route('/')
def home():
    return "MMI Assignment Tracker is Online!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 3. DATA FETCHING LOGIC (Bypasses SiteGround 403)
def fetch_mmi_data():
    try:
        # We use curl_cffi to impersonate a real browser (Chrome)
        # SiteGround blocks standard Python 'requests'
        response = cur_requests.get(
            API_URL, 
            impersonate="chrome", 
            timeout=15
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Error: Status {response.status_code}")
            return None
    except Exception as e:
        print(f"Fetch Error: {e}")
        return None

# 4. BOT HANDLERS
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "📊 **MMI Assignment Tracker**\n\n"
        "Use /active to see current assignment statistics.\n"
        "Use /status to check connection."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['active'])
def show_active_assignments(message):
    bot.send_message(message.chat.id, "📂 Fetching data from MMI LMS...")
    
    data = fetch_mmi_data()
    
    if not data:
        bot.send_message(message.chat.id, "❌ Error: Could not connect to the MMI API. Check logs.")
        return

    # Check if data is a list of assignments
    if isinstance(data, list) and len(data) > 0:
        report = "📋 **Active Assignments Summary:**\n\n"
        for item in data:
            # Matches your PHP API structure (Title, Submitted, Missing, Rate)
            title = item.get('title', 'Unknown')
            submitted = item.get('submitted_count', 0)
            missing = item.get('missing_count', 0)
            rate = item.get('submission_rate', '0%')
            
            report += f"🔹 *{title}*\n"
            report += f"✅ Submitted: {submitted} | ❌ Missing: {missing}\n"
            report += f"📈 Rate: {rate}\n\n"
        
        bot.send_message(message.chat.id, report, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "ℹ️ No active assignments found at this time.")

# 5. MAIN EXECUTION
if __name__ == "__main__":
    # Start Keep-Alive Thread
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

    # Prevent 409 Conflict on Render
    time.sleep(5)

    print("Bot is now polling...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(15)
