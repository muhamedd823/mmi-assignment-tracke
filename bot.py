import telebot
from curl_cffi import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SETTINGS ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN)

def fetch_data():
    try:
        # The 'impersonate' argument is what bypasses the SiteGround 403 error
        r = requests.get(API_URL, impersonate="chrome", timeout=30)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    data = fetch_data()
    if not data or 'assignments' not in data:
        bot.reply_to(message, "❌ Unable to connect to Database.")
        return

    markup = InlineKeyboardMarkup()
    for item in data['assignments']:
        # Original simple button creation
        btn_text = f"📝 {item['title']}"
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"view_{item['assignment_id']}"))

    bot.send_message(message.chat.id, "📊 *MMI Assignment Tracker*\nSelect an assignment:", 
                     reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_'))
def show_details(call):
    target_id = int(call.data.split('_')[1])
    data = fetch_data()
    
    if not data:
        return

    # Find the assignment
    task = next((x for x in data['assignments'] if x['assignment_id'] == target_id), None)
    
    if task:
        # Original simple report format
        report = (
            f"📌 *{task['title']}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏰ *Deadline:* {task.get('deadline', 'N/A')}\n"
            f"ℹ️ *Status:* {task.get('time_info', 'N/A')}\n"
        )
        
        # Original logic: only showing the "not_submitted" list
        if 'submissions' in task and 'not_submitted' in task['submissions']:
            missing = task['submissions']['not_submitted']
            names = "\n".join([f"• {p['trainee_name']}" for p in missing]) if missing else "None 🎉"
            report += f"\n🚫 *NOT SUBMITTED:*\n{names}"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="main_menu"))
        
        bot.edit_message_text(report, call.message.chat.id, call.message.message_id, 
                              parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_menu(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_welcome(call.message)

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
