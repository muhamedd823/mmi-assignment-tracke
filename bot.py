import os
import time
import telebot
from flask import Flask
from threading import Thread
from curl_cffi import requests as cur_requests

# --- CONFIGURATION ---
# Replace this with a new token if you revoked the old one
BOT_TOKEN = "8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s"
# Ensure there are no spaces in this URL
API_URL = "https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# --- RENDER KEEP-ALIVE ---
@app.route('/')
def home():
    return "MMI Assignment Tracker is Online!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- DATA FETCHING (SITEGROUND BYPASS) ---
def fetch_mmi_data():
    try:
        # These headers make Render look exactly like a real Chrome Browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://lms.mersamedia.org/",
            "Connection": "keep-alive"
        }
        
        # impersonate="chrome120" mimics the TLS fingerprint to bypass WAF/Firewalls
        response = cur_requests.get(
            API_URL, 
            headers=headers,
            impersonate="chrome120", 
            timeout=30
        )
        
        print(f"DEBUG: Status Code {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Error: {response.status_code} - {response.text[:100]}")
            return None
            
    except Exception as e:
        print(f"Connection Exception: {e}")
        return None

# --- BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "📊 **MMI Assignment Tracker**\n\n"
        "Click /active to get the latest trainee submission stats.\n"
        "Click /status to check if the server is healthy."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def check_status(message):
    bot.send_message(message.chat.id, "✅ Bot is connected and monitoring the LMS.")

@bot.message_handler(commands=['active'])
def show_active_assignments(message):
    msg = bot.send_message(message.chat.id, "📂 Connecting to LMS Database...")
    
    data = fetch_mmi_data()
    
    if not data:
        bot.edit_message_text("❌ Connection failed. SiteGround might be blocking Render. Check logs.", 
                              message.chat.id, msg.message_id)
        return

    if isinstance(data, list) and len(data) > 0:
        report = "📋 **MMI Assignment Report**\n\n"
        for item in data:
            title = item.get('title', 'Unknown Assignment')
            sub = item.get('submitted_count', 0)
            miss = item.get('missing_count', 0)
            rate = item.get('submission_rate', '0%')
            
            report += f"📝 *{title}*\n"
            report += f"✅ Submissions: {sub}\n"
            report += f"❌ Missing: {miss}\n"
            report += f"📊 Completion: {rate}\n"
            report += "--- --- --- ---\n"
        
        bot.edit_message_text(report, message.chat.id, msg.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("ℹ️ No active assignments found or API returned empty.", 
                              message.chat.id, msg.message_id)

# --- MAIN RUNNER ---
if __name__ == "__main__":
    # Start Flask server
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

    # Give Render time to cycle instances
    time.sleep(5)

    print("Bot is now polling...")
    while True:
        try:
            bot.infinity_polling(timeout=25, long_polling_timeout=25)
        except Exception as e:
            print(f"Polling Crash: {e}")
            time.sleep(10)
