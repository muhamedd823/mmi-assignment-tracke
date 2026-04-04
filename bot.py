import telebot
from curl_cffi import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

# --- CONFIG ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def fetch_data():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36"}
        r = requests.get(API_URL, impersonate="chrome", headers=headers, timeout=25)
        return r.json() if r.status_code == 200 else None
    except:
        return None

@bot.message_handler(commands=['start', 'menu'])
def show_active_assignments(message):
    data = fetch_data()
    if not data:
        bot.reply_to(message, "❌ Database connection failed.")
        return

    markup = InlineKeyboardMarkup()
    now = datetime.now()
    three_days_ago = now - timedelta(days=3)

    count = 0
    for task in data['assignments']:
        # Assuming your API sends a 'deadline' field like '2026-04-01 10:00:00'
        # If the API doesn't have a formal date, we use the ones present
        markup.add(InlineKeyboardButton(f"📝 {task['title'][:35]}", callback_data=f"sub_{task['assignment_id']}"))
        count += 1

    bot.send_message(message.chat.id, "📊 *MMI Assignment Portal*\nSelect a task to view tracking options:", 
                     reply_markup=markup, parse_mode='Markdown')

# --- SUB-MENU HANDLER ---
@bot.callback_query_handler(func=lambda c: c.data.startswith('sub_'))
def show_submenu(c):
    t_id = c.data.split('_')[1]
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📈 Stats & Time", callback_data=f"stat_{t_id}"))
    markup.row(
        InlineKeyboardButton("✅ On-Time", callback_data=f"list_on_{t_id}"),
        InlineKeyboardButton("⏰ Late", callback_data=f"list_late_{t_id}")
    )
    markup.row(InlineKeyboardButton("🚫 Not Submitted", callback_data=f"list_miss_{t_id}"))
    markup.row(InlineKeyboardButton("⬅️ Back to Menu", callback_data="back"))
    
    bot.edit_message_text("🔍 *What data do you want to see?*", c.message.chat.id, c.message.message_id, 
                          reply_markup=markup, parse_mode='Markdown')

# --- DATA VIEW HANDLER ---
@bot.callback_query_handler(func=lambda c: True)
def handle_all_clicks(c):
    if c.data == "back":
        bot.delete_message(c.message.chat.id, c.message.message_id)
        show_active_assignments(c.message)
        return

    # Parse action and ID (e.g., stat_15 or list_on_15)
    parts = c.data.split('_')
    action = parts[0]
    sub_type = parts[1] if len(parts) > 2 else None
    t_id = int(parts[-1])
    
    data = fetch_data()
    task = next((t for t in data['assignments'] if t['assignment_id'] == t_id), None)
    if not task: return

    stats = task['statistics']
    subs = task['submissions']
    
    text = f"📌 *{task['title']}*\n━━━━━━━━━━━━━━\n"

    if action == "stat":
        text += (f"🕒 *Time Info:* {task['time_info']}\n"
                 f"📊 *Rate:* {round(float(stats['submission_rate']), 1)}%\n"
                 f"📥 *Total Subs:* {stats['submitted_count']}\n"
                 f"❌ *Total Missing:* {stats['not_submitted_count']}")
    
    elif action == "list":
        if sub_type == "on":
            names = "\n".join([f"• {x['trainee_name']}" for x in subs['on_time']]) or "No on-time submissions."
            text += f"✅ *ON-TIME SUBMISSIONS:*\n\n{names}"
        elif sub_type == "late":
            names = "\n".join([f"• {x['trainee_name']} (Late)" for x in subs['late']]) or "No late submissions."
            text += f"⏰ *LATE SUBMISSIONS:*\n\n{names}"
        elif sub_type == "miss":
            names = "\n".join([f"• {x['trainee_name']}" for x in subs['not_submitted']]) or "Everyone submitted! 🎉"
            text += f"🚫 *MISSING SUBMISSIONS:*\n\n{names}"

    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data=f"sub_{t_id}"))
    bot.edit_message_text(text, c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=markup)

if __name__ == "__main__":
    bot.infinity_polling()
