import os
import time
import telebot
from flask import Flask
from threading import Thread
from curl_cffi import requests as cur_requests

# --- CONFIGURATION ---
BOT_TOKEN = "8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s"
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

# --- THE FIX: ADVANCED FETCHING ---
def fetch_mmi_data():
    try:
        # Mimicking a real Chrome browser on Windows 10
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://lms.mersamedia.org/",
            "X-Requested-With": "XMLHttpRequest" # Some firewalls require this for API calls
        }
        
        # We use impersonate="chrome110" and verify=False to bypass SSL handshake blocks
        response = cur_requests.get(
            API_URL, 
            headers=headers,
            impersonate="chrome110", 
            timeout=25,
            verify=False 
        )
        
        if response.status_code == 200:
            return response.json(), 200
        else:
            return None, response.status_code
            
    except Exception as e:
        print(f"Connection Exception: {e}")
        return None, "Connection Error"

# --- BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "📊 **MMI Assignment Tracker Ready.**\nUse /active to pull data.")

@bot.message_handler(commands=['active'])
def show_active_assignments(message):
    status_msg = bot.send_message(message.chat.id, "🔄 Connecting to MMI LMS...")
    
    data, status_code = fetch_mmi_data()
    
    if status_code != 200:
        bot.edit_message_text(f"❌ Error: API returned Status {status_code}.\n(If 403, SiteGround is blocking Render's IP.)", 
                              message.chat.id, status_msg.message_id)
        return

    if data and isinstance(data, list):
        report = "📋 **Latest Assignment Stats**\n\n"
        for item in data:
            title = item.get('title', 'Assignment')
            sub = item.get('submitted_count', 0)
            miss = item.get('not_submitted_count', 0) # Fixed key name from your PHP
            rate = item.get('submission_rate', '0%')
            
            report += f"📝 *{title}*\n✅ {sub} | ❌ {miss} | 📈 {rate}\n\n"
        
        bot.edit_message_text(report, message.chat.id, status_msg.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("⚠️ API connected but returned no data.", message.chat.id, status_msg.message_id)

# --- MAIN RUNNER ---
if __name__ == "__main__":
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()
    time.sleep(2)
    bot.infinity_polling()
