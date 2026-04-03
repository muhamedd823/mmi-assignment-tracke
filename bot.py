import telebot
import requests
import time
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.background import BackgroundScheduler

# --- CONFIG ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
YOUR_CHAT_ID = '7494977999' # Your Telegram ID
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
sent_alerts = set()

def get_clean_data():
    """Fetches MMI data with the required Security Key"""
    try:
        headers = {
            'User-Agent': 'MMI-Monitoring-System/2.0',
            'Accept': 'application/json'
        }
        # The key is already in the API_URL string
        response = requests.get(API_URL, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Server Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Fetch Error: {e}")
        return None

def format_detailed_report(task, title="📊 MMI TASK DETAIL"):
    """Logic to display On-Time, Late, and Missing trainees"""
    stats = task.get('statistics', {})
    subs = task.get('submissions', {})
    
    late = subs.get('late_submitted', [])
    missing = subs.get('not_submitted', [])

    # Format the names for the message
    late_list = "\n".join([f"• {t['trainee_name']}" for t in late[:15]])
    missing_list = "\n".join([f"• {t['trainee_name']}" for t in missing[:15]])

    return (
        f"*{title}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 *Task:* {task.get('title')}\n"
        f"⏳ *Status:* {task.get('time_info')}\n\n"
        f"✅ On-Time: *{stats.get('on_time_count', 0)}*\n"
        f"📥 Late: *{stats.get('late_count', 0)}*\n"
        f"❌ Missing: *{stats.get('not_submitted_count', 0)}*\n"
        f"📈 Rate: *{stats.get('submission_rate', 0)}%*\n\n"
        f"🚩 *LATE SUBMISSIONS:*\n{late_list if late_list else '_None_'}\n\n"
        f"🚫 *NOT SUBMITTED:*\n{missing_list if missing_list else '_All Clear!_'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Updated: `{time.strftime('%H:%M:%S')}`"
    )

# --- TELEGRAM HANDLERS ---

@bot.message_handler(commands=['start', 'menu', 'status'])
def send_menu(message):
    data = get_clean_data()
    if not data:
        bot.send_message(message.chat.id, "❌ Error: Could not connect to MMI API.")
        return

    markup = InlineKeyboardMarkup()
    # List the 6 most recent assignments
    for task in data['assignments'][:6]:
        btn_text = f"📋 {task.get('title')[:35]}"
        # Store the task ID in the button
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"tid_{task.get('id')}"))

    bot.send_message(message.chat.id, "🔍 *MMI Assignment Tracker*\nSelect a task to see full details:", 
                     parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('tid_'))
def handle_selection(call):
    task_id = call.data.replace('tid_', '')
    data = get_clean_data()
    
    # Find the specific task in the list
    task = next((t for t in data['assignments'] if str(t.get('id')) == task_id), None)

    if task:
        text = format_detailed_report(task)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                             parse_mode='Markdown', reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "Task data not found.")

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_menu(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_menu(call.message)

# --- AUTOMATION LOGIC ---

def run_scheduler():
    data = get_clean_data()
    if not data: return

    for task in data['assignments']:
        t_id = task.get('id')
        diff = task.get('time_difference_minutes', 0)
        
        # Exact windows for 4h, 3h, 1h, and Deadline Passed
        alerts = {"4H LEFT": -240, "3H LEFT": -180, "1H LEFT": -60, "EXPIRED": 1}

        for label, target in alerts.items():
            key = f"{t_id}_{label}"
            if key not in sent_alerts and target <= diff <= (target + 2):
                title = f"🚨 {label} ALERT"
                text = format_detailed_report(task, title=title)
                bot.send_message(YOUR_CHAT_ID, text, parse_mode='Markdown')
                sent_alerts.add(key)

scheduler = BackgroundScheduler()
scheduler.add_job(run_scheduler, 'interval', minutes=1)
scheduler.start()

if __name__ == "__main__":
    print("🚀 MMI Tracking Bot is now ONLINE...")
    bot.infinity_polling()
