import telebot
from curl_cffi import requests # Use this instead of standard requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SETTINGS ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def fetch_data(chat_id=None):
    """
    Impersonates Chrome's encryption (TLS) signature to bypass SiteGround 403.
    """
    try:
        r = requests.get(API_URL, impersonate="chrome", timeout=25)
        
        if r.status_code == 200:
            return r.json()
        else:
            if chat_id: bot.send_message(chat_id, f"❌ SiteGround Blocked us (Status {r.status_code})")
            return None
    except Exception as e:
        if chat_id: bot.send_message(chat_id, f"⚠️ Connection Error: {str(e)[:50]}")
        return None

@bot.message_handler(commands=['start', 'menu'])
def show_menu(message):
    data = fetch_data(message.chat.id)
    if not data or 'assignments' not in data:
        return 

    markup = InlineKeyboardMarkup()
    for task in data['assignments']:
        t_id = task.get('assignment_id')
        title = task.get('title', 'Assignment')
        markup.add(InlineKeyboardButton(f"📝 {title[:30]}", callback_data=f"v_{t_id}"))

    bot.send_message(message.chat.id, "✅ *MMI Tracking System Online*\nSelect an assignment:", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith('v_'))
def handle_details(c):
    target_id = int(c.data.split('_')[1])
    data = fetch_data(c.message.chat.id)
    if not data: return

    task = next((t for t in data['assignments'] if t['assignment_id'] == target_id), None)

    if task:
        stats = task['statistics']
        subs = task.get('submissions', {})
        
        # Extract the three lists
        on_time = subs.get('on_time', [])
        late = subs.get('late', [])
        not_sub = subs.get('not_submitted', [])

        # Format the lists into readable strings
        on_time_text = "\n".join([f"• {x['trainee_name']}" for x in on_time]) if on_time else "None"
        late_text = "\n".join([f"• {x['trainee_name']}" for x in late]) if late else "None"
        not_sub_text = "\n".join([f"• {x['trainee_name']}" for x in not_sub]) if not_sub else "None 🎉"
        
        # Construct the comprehensive report
        report = (
            f"📊 *{task['title']}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕒 {task['time_info']}\n"
            f"📈 Rate: *{round(float(stats.get('submission_rate', 0)), 1)}%* ({stats['submitted_count']} Submitted, {stats['not_submitted_count']} Missing)\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ *ON TIME ({len(on_time)}):*\n{on_time_text}\n\n"
            f"⚠️ *LATE ({len(late)}):*\n{late_text}\n\n"
            f"🚫 *NOT SUBMITTED ({len(not_sub)}):*\n{not_sub_text}"
        )
        
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="back"))
        bot.edit_message_text(report, c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "back")
def back(c):
    bot.delete_message(c.message.chat.id, c.message.message_id)
    show_menu(c.message)

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
