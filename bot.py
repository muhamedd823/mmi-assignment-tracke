import telebot
from curl_cffi import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SETTINGS ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def fetch_data(chat_id=None):
    """
    Uses curl_cffi to impersonate Chrome. 
    This is the only way to bypass SiteGround's 403 protection.
    """
    try:
        # We use a real browser User-Agent to be extra safe
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }
        r = requests.get(API_URL, impersonate="chrome", headers=headers, timeout=25)
        
        if r.status_code == 200:
            return r.json()
        else:
            if chat_id: 
                bot.send_message(chat_id, f"❌ SiteGround Blocked Render (Status {r.status_code})")
            return None
    except Exception as e:
        if chat_id: 
            bot.send_message(chat_id, f"⚠️ Connection Error: {str(e)[:50]}")
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
        # Limit title length for the button
        markup.add(InlineKeyboardButton(f"📝 {title[:30]}", callback_data=f"v_{t_id}"))

    bot.send_message(message.chat.id, "✅ *MMI Tracking System Online*\nSelect an assignment:", 
                     reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith('v_'))
def handle_details(c):
    target_id = int(c.data.split('_')[1])
    data = fetch_data(c.message.chat.id)
    if not data: 
        return

    # Find the clicked assignment
    task = next((t for t in data['assignments'] if t['assignment_id'] == target_id), None)

    if task:
        stats = task['statistics']
        subs = task['submissions'] # This matches your JSON key
        
        # 1. Format On-Time List
        on_time_names = "\n".join([f"• {x['trainee_name']}" for x in subs['on_time']]) if subs['on_time'] else "None"
        
        # 2. Format Late List
        late_names = "\n".join([f"• {x['trainee_name']} ⏰" for x in subs['late']]) if subs['late'] else "None"
        
        # 3. Format Not Submitted List
        not_sub_names = "\n".join([f"• {x['trainee_name']}" for x in subs['not_submitted']]) if subs['not_submitted'] else "None (All Clear! 🎉)"
        
        report = (
            f"📊 *{task['title']}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕒 {task['time_info']}\n"
            f"📈 Rate: *{round(float(stats.get('submission_rate', 0)), 1)}%*\n"
            f"📥 {stats['submitted_count']} Submitted | {stats['not_submitted_count']} Missing\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ *ON TIME ({len(subs['on_time'])}):*\n{on_time_names}\n\n"
            f"⚠️ *LATE ({len(subs['late'])}):*\n{late_names}\n\n"
            f"🚫 *NOT SUBMITTED ({len(subs['not_submitted'])}):*\n{not_sub_names}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="back"))
        
        bot.edit_message_text(report, c.message.chat.id, c.message.message_id, 
                              parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "back")
def back(c):
    bot.delete_message(c.message.chat.id, c.message.message_id)
    show_menu(c.message)

if __name__ == "__main__":
    bot.infinity_polling()
