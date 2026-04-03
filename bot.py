import telebot, requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def get_data():
    try:
        return requests.get(API_URL, timeout=20).json()
    except: return None

def format_report(task):
    s = task['statistics']
    sub = task['submissions']
    late = "\n".join([f"• {x['trainee_name']}" for x in sub['late_submitted']])
    missing = "\n".join([f"• {x['trainee_name']}" for x in sub['not_submitted'][:15]])
    
    return (f"📊 *{task['title']}*\n"
            f"━━━━━━━━━━━━\n"
            f"✅ On-Time: {s['on_time_count']}\n"
            f"🚩 *LATE:* {s['late_count']}\n"
            f"❌ Missing: {s['not_submitted_count']}\n"
            f"📈 Rate: {s['submission_rate']}%\n\n"
            f"*LATE NAMES:*\n{late if late else 'None'}\n\n"
            f"*MISSING (Top 15):*\n{missing if missing else 'None'}")

@bot.message_handler(commands=['start', 'menu'])
def show_menu(m):
    data = get_data()
    if not data: return bot.reply_to(m, "API Error")
    
    markup = InlineKeyboardMarkup()
    for t in data['assignments']:
        # We use the actual Database ID in the callback
        markup.add(InlineKeyboardButton(f"📝 {t['title'][:35]}", callback_data=f"view_{t['id']}"))
    
    bot.send_message(m.chat.id, "🔔 *MMI Assignment Tracker*\nSelect a task to see Late/Missing trainees:", 
                     reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith('view_'))
def handle_view(c):
    target_id = c.data.split('_')[1]
    data = get_data()
    # Find the EXACT assignment matching the ID clicked
    task = next((x for x in data['assignments'] if x['id'] == target_id), None)
    
    if task:
        btn = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="back"))
        bot.edit_message_text(format_report(task), c.message.chat.id, c.message.message_id, 
                             parse_mode='Markdown', reply_markup=btn)

@bot.callback_query_handler(func=lambda c: c.data == "back")
def handle_back(c):
    bot.delete_message(c.message.chat.id, c.message.message_id)
    show_menu(c.message)

bot.infinity_polling()
