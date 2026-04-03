import telebot
import requests
import time
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

# --- CONFIG ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
YOUR_CHAT_ID = '7494977999'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Track sent alerts to avoid spamming the same hour
# alert_key format: "taskID_label"
sent_alerts = set()

def get_clean_data():
    """Fetches data using Browser Headers to bypass security filters"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) MMI-Tracker-Bot/1.0',
            'Accept': 'application/json',
            'Referer': 'https://lms.mersamedia.org/'
        }
        response = requests.get(API_URL, headers=headers, timeout=25)
        if response.status_code != 200:
            return None
        
        raw_text = response.text.strip()
        if not raw_text.startswith('{'):
            start_index = raw_text.find('{')
            if start_index != -1:
                raw_text = raw_text[start_index:]
        
        return json.loads(raw_text)
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

def format_report(task, title_prefix="📊 MMI REPORT"):
    """Standard report formatter for On-Time alerts"""
    stats = task.get('statistics', {})
    not_sub = task.get('submissions', {}).get('not_submitted', [])
    names_list = "\n".join([f"• {t['trainee_name']}" for t in not_sub[:15]])
    
    msg = (
        f"*{title_prefix}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 *Task:* {task.get('title')}\n"
        f"⏳ *Time Info:* {task.get('time_info')}\n\n"
        f"✅ Submitted: *{stats.get('submitted_count', 0)}*\n"
        f"❌ Missing: *{stats.get('not_submitted_count', 0)}*\n"
        f"📈 Rate: *{stats.get('submission_rate', 0)}%*\n\n"
        f"🚩 *Pending Trainees:* \n{names_list if names_list else '🎉 All Clear!'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Updated: `{time.strftime('%H:%M:%S')}`"
    )
    return msg

def format_late_report(task):
    """Detailed report triggered 1 minute after deadline"""
    subs = task.get('submissions', {})
    # Note: Your PHP API should ideally provide 'late_submitted' array
    late_list = "\n".join([f"• {t['trainee_name']}" for t in subs.get('late_submitted', [])])
    missing_list = "\n".join([f"• {t['trainee_name']}" for t in subs.get('not_submitted', [])])
    
    msg = (
        f"🚨 *DEADLINE EXPIRED (FINAL REPORT)*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 *Task:* {task.get('title')}\n\n"
        f"📥 *Late Submissions:*\n{late_list if late_list else 'None Recorded'}\n\n"
        f"❌ *Final Non-Submissions:*\n{missing_list if missing_list else 'Everyone Submitted!'}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return msg

# --- SCHEDULER LOGIC ---

def auto_check():
    """Checked every 1 minute for precision timing"""
    print(f"Running auto-check at {time.strftime('%H:%M:%S')}...")
    data = get_clean_data()
    if not data or not data.get('assignments'):
        return

    for task in data['assignments']:
        task_id = task.get('id', task.get('title'))
        diff = task.get('time_difference_minutes', 0)
        
        # Mapping labels to target minutes
        # Negative = before deadline, Positive = after deadline
        thresholds = {
            "4 HOURS LEFT": -240,
            "3 HOURS LEFT": -180,
            "1 HOUR LEFT": -60,
            "DEADLINE PASSED": 1  # 1 minute after
        }

        for label, minutes in thresholds.items():
            alert_key = f"{task_id}_{label}"
            
            # Check if we are in the window (current diff is within 2 mins of target)
            if alert_key not in sent_alerts and minutes <= diff <= (minutes + 2):
                
                if label == "DEADLINE PASSED":
                    report_text = format_late_report(task)
                else:
                    report_text = format_report(task, title_prefix=f"⏰ {label}")
                
                bot.send_message(YOUR_CHAT_ID, report_text, parse_mode='Markdown')
                sent_alerts.add(alert_key)

# --- COMMANDS ---

@bot.message_handler(commands=['start', 'status'])
def manual_check(message):
    data = get_clean_data()
    if data and data.get('assignments'):
        for task in data['assignments']:
            text = format_report(task)
            bot.send_message(message.chat.id, text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "⚠️ API unavailable.")

# --- INITIALIZE ---

scheduler = BackgroundScheduler()
scheduler.add_job(auto_check, 'interval', minutes=1)
scheduler.start()

if __name__ == "__main__":
    print("🚀 MMI Tracker High-Precision System is ONLINE...")
    bot.infinity_polling()
