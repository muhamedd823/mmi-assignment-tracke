import telebot
from curl_cffi import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIG ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN)

def fetch_mmi_data():
    try:
        # Impersonate chrome to avoid 403 blocks from hosting providers
        r = requests.get(API_URL, impersonate="chrome", timeout=30)
        if r.status_code == 200:
            return r.json()
        print(f"Server Error: {r.status_code}")
        return None
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    data = fetch_mmi_data()
    if not data or 'assignments' not in data:
        bot.reply_to(message, "❌ Unable to connect to MMI Database. Check API/Server.")
        return

    markup = InlineKeyboardMarkup()
    for item in data['assignments']:
        btn_text = f"📝 {item['title'][:25]}..."
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"view_{item['assignment_id']}"))

    bot.send_message(message.chat.id, "📊 *MMI Assignment Tracker*\nSelect an assignment to see full details:", 
                     reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_'))
def show_details(call):
    target_id = int(call.data.split('_')[1])
    data = fetch_mmi_data()
    
    if not data:
        bot.answer_callback_query(call.id, "Error fetching data.")
        return

    # Find the specific assignment
    task = next((x for x in data['assignments'] if x['assignment_id'] == target_id), None)
    
    if task:
        l = task['lists']
        s = task['stats']
        
        # Build lists
        on_time_str = "\n".join([f"• {p['name']}" for p in l['on_time']]) or "None"
        late_str = "\n".join([f"• {p['name']} (Late)" for p in l['late']]) or "None"
        missing_str = "\n".join([f"• {p['name']}" for p in l['not_submitted']]) or "None 🎉"

        report = (
            f"📌 *{task['title']}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏰ *Deadline:* {task['deadline']}\n"
            f"ℹ️ *Status:* {task['time_info']}\n"
            f"📊 *Submission Rate:* {s['rate']}%\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ *SUBMITTED ON TIME ({len(l['on_time'])}):*\n{on_time_str}\n\n"
            f"⚠️ *SUBMITTED LATE ({len(l['late'])}):*\n{late_text}\n\n"
            f"🚫 *NOT SUBMITTED ({len(l['not_submitted'])}):*\n{missing_str}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Back to List", callback_data="main_menu"))
        
        bot.edit_message_text(report, call.message.chat.id, call.message.message_id, 
                              parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_menu(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_welcome(call.message)

if __name__ == "__main__":
    print("Bot is active...")
    bot.infinity_polling()
