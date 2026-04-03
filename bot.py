import telebot
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SETTINGS ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
# Make sure this is exactly the URL you see in the browser
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def fetch_from_siteground(chat_id=None):
    """Uses a Session and Desktop-Class headers to bypass 403 blocks."""
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'DNT': '1',
        'Connection': 'keep-alive',
    }
    
    try:
        # We use session.get instead of requests.get for better persistence
        r = session.get(API_URL, headers=headers, timeout=20)
        
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 403:
            if chat_id:
                bot.send_message(chat_id, "🚫 *SiteGround Security Block (403)*\nThey think I'm a bot. Try refreshing or check SiteGround 'Bot Protection' settings.", parse_mode='Markdown')
            return None
        else:
            if chat_id:
                bot.send_message(chat_id, f"⚠️ Error {r.status_code}: Server issue.")
            return None
    except Exception as e:
        if chat_id:
            bot.send_message(chat_id, f"❌ Connection Error: {str(e)[:50]}")
        return None

@bot.message_handler(commands=['start', 'menu'])
def menu(m):
    data = fetch_from_siteground(m.chat.id)
    if not data: return

    markup = InlineKeyboardMarkup()
    for task in data.get('assignments', []):
        t_id = task.get('assignment_id')
        title = task.get('title', 'Assignment')
        markup.add(InlineKeyboardButton(f"📝 {title[:30]}", callback_data=f"v_{t_id}"))

    bot.send_message(m.chat.id, "✅ *System Online*\nChoose an assignment:", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith('v_'))
def details(c):
    target_id = int(c.data.split('_')[1])
    data = fetch_from_siteground(c.message.chat.id)
    if not data: return

    task = next((t for t in data['assignments'] if t['assignment_id'] == target_id), None)
    if task:
        stats = task['statistics']
        not_sub = task['submissions']['not_submitted']
        names = "\n".join([f"• {x['trainee_name']}" for x in not_sub]) if not_sub else "✅ All clear!"
        
        msg = (f"📊 *{task['title']}*\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"🕒 {task['time_info']}\n"
               f"📈 Rate: *{round(float(stats['submission_rate']), 1)}%*\n\n"
               f"🚫 *NOT SUBMITTED:* \n{names}")
        
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="back"))
        bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "back")
def back(c):
    bot.delete_message(c.message.chat.id, c.message.message_id)
    menu(c.message)

if __name__ == "__main__":
    bot.infinity_polling()
