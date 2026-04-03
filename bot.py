import telebot
import requests
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SETTINGS ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def fetch_data(chat_id=None):
    """Fetches data with a User-Agent to prevent 403 Forbidden errors."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        r = requests.get(API_URL, headers=headers, timeout=15)
        if r.status_code != 200:
            if chat_id: bot.send_message(chat_id, f"❌ Server Error: {r.status_code}")
            return None
        return r.json()
    except Exception as e:
        if chat_id: bot.send_message(chat_id, f"❌ Connection Error: {str(e)[:50]}")
        return None

@bot.message_handler(commands=['start', 'menu'])
def show_menu(message):
    data = fetch_data(message.chat.id)
    if not data or 'assignments' not in data:
        return # Error message sent by fetch_data

    markup = InlineKeyboardMarkup()
    for task in data['assignments']:
        t_id = task.get('assignment_id')
        title = task.get('title', 'Assignment')
        # Limit title to 30 chars for buttons
        btn_label = f"📝 {title[:30]}..."
        markup.add(InlineKeyboardButton(btn_label, callback_data=f"view_{t_id}"))

    bot.send_message(
        message.chat.id, 
        "🔔 *MMI Assignment Tracker*\nSelect a task to see missing trainees:", 
        reply_markup=markup, 
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith('view_'))
def show_details(c):
    try:
        # Extract ID and convert to int for exact matching
        target_id = int(c.data.split('_')[1])
    except:
        return bot.answer_callback_query(c.id, "Invalid ID.")

    data = fetch_data(c.message.chat.id)
    if not data: return

    # Find the specific task
    task = next((t for t in data['assignments'] if t['assignment_id'] == target_id), None)

    if task:
        stats = task['statistics']
        not_sub = task['submissions']['not_submitted']
        
        # Build the missing names list
        names_list = "\n".join([f"• {x['trainee_name']}" for x in not_sub]) if not_sub else "✅ Everyone has submitted!"
        
        report = (
            f"📊 *{task['title']}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕒 {task['time_info']}\n"
            f"📥 Submitted: *{stats['submitted_count']}*\n"
            f"❌ Missing: *{stats['not_submitted_count']}*\n"
            f"📈 Rate: *{round(float(stats['submission_rate']), 1)}%*\n\n"
            f"🚫 *NOT SUBMITTED:* \n{names_list}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="back"))
        bot.edit_message_text(report, c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=markup)
    else:
        bot.answer_callback_query(c.id, "Assignment not found.")

@bot.callback_query_handler(func=lambda c: c.data == "back")
def go_back(c):
    bot.delete_message(c.message.chat.id, c.message.message_id)
    show_menu(c.message)

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
