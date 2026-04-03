import telebot
import requests
import time
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.background import BackgroundScheduler

# --- CONFIG ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
YOUR_CHAT_ID = '7494977999'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
sent_alerts = set()

def get_clean_data():
    """Fetches data from MMI Server with Browser Headers"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) MMI-Tracker-Bot/1.1',
            'Accept': 'application/json',
            'Referer': 'https://lms.mersamedia.org/'
        }
        response = requests.get(API_URL, headers=headers, timeout=25)
        if response.status_code != 200: return None
        raw_text = response.text.strip()
        if not raw_text.startswith('{'):
            start_index = raw_text.find('{')
            if start_index != -1: raw_text = raw_text[start_index:]
        return json.loads(raw_text)
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

def format_detailed_report(task, title="📊 MMI TASK DETAIL"):
    """Formats the specific data for a selected assignment"""
    stats = task.get('statistics', {})
    subs = task.get('submissions', {})
    
    # Categorizing Trainees
    on_time = subs.get('submitted_on_time', [])
    late = subs.get('late_submitted', [])
    missing = subs.get('not_submitted', [])

    late_text = "\n".join([f"• {t['trainee_name']} (LATE)" for t in late[:10]])
    missing_text = "\n".join([f"• {t['trainee_name']}" for t in missing[:15]])

    report = (
        f"*{title}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 *Task:* {task.get('title')}\n"
        f"⏳ *Deadline:* {task.get('time_info')}\n\n"
        f"✅ On-Time: *{len(on_time)}*\n"
        f"📥 Late: *{len(late)}*\n"
        f"❌ Missing: *{len(missing)}*\n"
        f"📈 Rate: *{stats.get('submission_rate', 0)}%*\n\n"
        f"🚩 *LATE SUBMISSIONS:*\n{late_text if late_text else 'None'}\n\n"
        f"🚫 *NOT SUBMITTED:*\n{missing_text if missing_text else 'All Clear!'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Updated: `{time.strftime('%H:%M:%S')}`"
    )
    return report

# --- COMMANDS & CALLBACKS ---

@bot.message_handler(commands=['start', 'status', 'menu'])
def show_menu(message):
    data = get_clean_data()
    if not data or not data.get('assignments'):
        bot.send_message(message.chat.id, "⚠️ API unavailable or no assignments found.")
        return

    markup = InlineKeyboardMarkup()
    # Get most recent 6 assignments
    recent_tasks = data['assignments'][:6]

    for task in recent_tasks:
        # We use the index or title as callback data
        btn_text = f"📝 {task.get('title')[:30]}..."
        callback_data = f"task_{task.get('id', task.get('title'))}"
        markup.add(InlineKeyboardButton(btn_text, callback_data=callback_data))

    bot.send_message(message.chat.id, "🔍 *Select an assignment to track:*", 
                     parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('task_'))
def handle_task_selection(call):
    task_id = call.data.replace('task_', '')
    data = get_clean_data()
    
    selected_task = next((t for t in data['assignments'] if str(t.get('id', t.get('title'))) == task_id), None)

    if selected_task:
        text = format_detailed_report(selected_task)
        # Add a back button
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Back to List", callback_data="back_to_menu"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                             parse_mode='Markdown', reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "Task not found.")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call):
    # Simply re-trigger the menu logic
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_menu(call.message)

# --- AUTOMATIC SCHEDULER ---

def auto_check():
    data = get_clean_data()
    if not data or not data.get('assignments'): return

    for task in data['assignments']:
        t_id = task.get('id', task.get('title'))
        diff = task.get('time_difference_minutes', 0)
        
        # 4h, 3h, 1h, and +1m precision
        checks = {"4H LEFT": -240, "3H LEFT": -180, "1H LEFT": -60, "EXPIRED": 1}

        for label, minutes in checks.items():
            key = f"{t_id}_{label}"
            if key not in sent_alerts and minutes <= diff <= (minutes + 2):
                title = f"⏰ {label} ALERT" if label != "EXPIRED" else "🚨 DEADLINE PASSED"
                text = format_detailed_report(task, title=title)
                bot.send_message(YOUR_CHAT_ID, text, parse_mode='Markdown')
                sent_alerts.add(key)

scheduler = BackgroundScheduler()
scheduler.add_job(auto_check, 'interval', minutes=1)
scheduler.start()

if __name__ == "__main__":
    print("🚀 MMI Tracker v1.1 Interactive Mode is ONLINE...")
    bot.infinity_polling()
