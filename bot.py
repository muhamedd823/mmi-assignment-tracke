import telebot
from curl_cffi import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIG ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN)

def fetch_mmi_data():
    try:
        # Bypass SiteGround security
        r = requests.get(API_URL, impersonate="chrome", timeout=30)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    data = fetch_mmi_data()
    if not data or 'assignments' not in data:
        bot.reply_to(message, "❌ API Connection Failed. Please try again.")
        return

    markup = InlineKeyboardMarkup()
    for item in data['assignments']:
        # Match your API key: 'title' and 'assignment_id'
        btn_text = f"📝 {item['title'][:25]}..."
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"v_{item['assignment_id']}"))

    bot.send_message(message.chat.id, "📊 *MMI Assignment Tracker*\nSelect an assignment:", 
                     reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('v_'))
def show_details(call):
    target_id = int(call.data.split('_')[1])
    data = fetch_mmi_data()
    
    if not data:
        bot.answer_callback_query(call.id, "Data error.")
        return

    # Find assignment
    task = next((x for x in data['assignments'] if x['assignment_id'] == target_id), None)
    
    if task:
        # Match your specific JSON keys: 'statistics' and 'submissions'
        stats = task['statistics']
        subs = task['submissions']
        
        # Format Lists
        on_time = "\n".join([f"• {p['trainee_name']}" for p in subs['on_time']]) or "None"
        late = "\n".join([f"• {p['trainee_name']} ⚠️" for p in subs['late']]) or "None"
        missing = "\n".join([f"• {p['trainee_name']}" for p in subs['not_submitted']]) or "None 🎉"

        report = (
            f"📌 *{task['title']}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕒 *Status:* {task['time_info']}\n"
            f"📈 *Rate:* {round(stats['submission_rate'], 1)}% ({stats['submitted_count']} total)\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ *ON TIME ({len(subs['on_time'])}):*\n{on_time}\n\n"
            f"⚠️ *LATE ({len(subs['late'])}):*\n{late}\n\n"
            f"🚫 *NOT SUBMITTED ({len(subs['not_submitted'])}):*\n{missing}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_home"))
        
        bot.edit_message_text(report, call.message.chat.id, call.message.message_id, 
                              parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def back_to_menu(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_welcome(call.message)

if __name__ == "__main__":
    bot.infinity_polling()
