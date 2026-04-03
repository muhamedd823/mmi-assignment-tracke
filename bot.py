import telebot
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SETTINGS ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def fetch_data(chat_id=None):
    """
    Tricks SiteGround into thinking the bot is a real Chrome Browser.
    This fixes the '403 Forbidden' error.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    try:
        # Create a session to handle cookies if SiteGround requires them
        session = requests.Session()
        r = session.get(API_URL, headers=headers, timeout=20)
        
        if r.status_code == 200:
            return r.json()
        else:
            if chat_id:
                bot.send_message(chat_id, f"❌ SiteGround Blocked us again (Status: {r.status_code})")
            return None
    except Exception as e:
        if chat_id:
            bot.send_message(chat_id, f"⚠️ Connection Error: {str(e)[:50]}")
        return None

@bot.message_handler(commands=['start', 'menu'])
def start_menu(message):
    data = fetch_data(message.chat.id)
    if not data: return

    markup = InlineKeyboardMarkup()
    for task in data.get('assignments', []):
        t_id = task.get('assignment_id')
        title = task.get('title', 'Assignment')
        markup.add(InlineKeyboardButton(f"📝 {title[:30]}", callback_data=f"view_{t_id}"))

    bot.send_message(message.chat.id, "✅ *Connected!* Select an assignment:", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith('view_'))
def handle_view(c):
    target_id = int(c.data.split('_')[1])
    data = fetch_data(c.message.chat.id)
    if not data: return

    task = next((t for t in data['assignments'] if t['assignment_id'] == target_id), None)

    if task:
        stats = task['statistics']
        not_sub = task['submissions']['not_submitted']
        names = "\n".join([f"• {x['trainee_name']}" for x in not_sub]) if not_sub else "✅ All Submitted!"
        
        report = (
            f"📊 *{task['title']}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕒 {task['time_info']}\n"
            f"📥 Submitted: *{stats['submitted_count']}*\n"
            f"❌ Missing: *{stats['not_submitted_count']}*\n"
            f"📈 Rate: *{round(float(stats['submission_rate']), 1)}%*\n\n"
            f"🚫 *NOT SUBMITTED:* \n{names}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="back"))
        bot.edit_message_text(report, c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "back")
def go_back(c):
    bot.delete_message(c.message.chat.id, c.message.message_id)
    start_menu(c.message)

if __name__ == "__main__":
    bot.infinity_polling()
