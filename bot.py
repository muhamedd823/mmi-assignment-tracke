import telebot
import requests
import time
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.background import BackgroundScheduler

# --- CONFIG ---
# Using your verified NEW Token
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
YOUR_CHAT_ID = '7494977999'

# Your MMI API Endpoint with Secret Key
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def get_clean_data():
    """Fetches data using Browser Headers to bypass SiteGround Firewall"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Referer': 'https://lms.mersamedia.org/'
        }
        response = requests.get(API_URL, headers=headers, timeout=25)
        
        print(f"\n--- [ {time.strftime('%H:%M:%S')} ] API CHECK ---")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            return None

        raw_text = response.text.strip()
        
        # Clean JSON if there's hidden HTML/BOM characters
        if not raw_text.startswith('{'):
            start_index = raw_text.find('{')
            if start_index != -1:
                raw_text = raw_text[start_index:]
        
        return json.loads(raw_text)
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def format_assignment(task):
    """Creates a professional M&E report layout"""
    stats = task.get('statistics', {})
    not_sub = task.get('submissions', {}).get('not_submitted', [])
    
    # List top 12 missing trainees
    names_list = "\n".join([f"• {t['trainee_name']}" for t in not_sub[:12]])
    
    msg = (
        f"📊 *MMI TRAINEE TRACKER*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 *Task:* {task.get('title', 'N/A')}\n"
        f"⏳ *Time:* {task.get('time_info', 'N/A')}\n\n"
        f"✅ Submitted: *{stats.get('submitted_count', 0)}*\n"
        f"❌ Missing: *{stats.get('not_submitted_count', 0)}*\n"
        f"📈 Rate: *{stats.get('submission_rate', 0)}%*\n\n"
        f"🚩 *Pending Trainees:* \n{names_list if names_list else '🎉 All Clear!'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Last Updated: `{time.strftime('%H:%M:%S')}`"
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh"))
    return msg, markup

# --- COMMAND HANDLERS ---

@bot.message_handler(commands=['start', 'status'])
def manual_report(message):
    bot.send_chat_action(message.chat.id, 'typing')
    data = get_clean_data()
    
    if data and data.get('assignments'):
        for task in data['assignments']:
            text, markup = format_assignment(task)
            bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "⚠️ API Error. Could not fetch MMI data. Check server logs.")

@bot.callback_query_handler(func=lambda call: call.data == "refresh")
def refresh_callback(call):
    data = get_clean_data()
    if data and data.get('assignments'):
        task = data['assignments'][0] 
        text, markup = format_assignment(task)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                                 parse_mode='Markdown', reply_markup=markup)
            bot.answer_callback_query(call.id, "Refreshed!")
        except Exception:
            bot.answer_callback_query(call.id, "No changes detected.")

# --- AUTOMATION ---

def auto_check():
    """Checks for deadlines every 10 mins and alerts your Chat ID"""
    data = get_clean_data()
    if data and data.get('assignments'):
        for task in data['assignments']:
            # Alerting logic based on time difference (approx 4 hours before)
            diff = task.get('time_difference_minutes', 0)
            if -250 <= diff <= -230:
                text, markup = format_assignment(task)
                bot.send_message(YOUR_CHAT_ID, "⚠️ *DEADLINE ALERT*\n" + text, 
                                 parse_mode='Markdown', reply_markup=markup)

# Scheduler Setup
scheduler = BackgroundScheduler()
scheduler.add_job(auto_check, 'interval', minutes=10)
scheduler.start()

# --- RUN BOT ---
if __name__ == "__main__":
    print(f"🚀 MMI Tracking System is ONLINE (Polling)...")
    print(f"Targeting Chat ID: {YOUR_CHAT_ID}")
    
    # Use infinity_polling to handle network flickers
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
