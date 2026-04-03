import telebot
import requests
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SETTINGS ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def fetch_data(chat_id=None):
    """
    Uses a browser-mimicking session to bypass SiteGround 403 blocks
    and safely handles JSON parsing to avoid 'Char 0' errors.
    """
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Referer': 'https://lms.mersamedia.org/',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        response = session.get(API_URL, headers=headers, timeout=20)
        
        # Check if we got a real 200 OK
        if response.status_code != 200:
            if chat_id:
                bot.send_message(chat_id, f"❌ Server Blocked Request (Error {response.status_code})")
            return None

        # Safely try to parse JSON
        try:
            return response.json()
        except json.JSONDecodeError:
            if chat_id:
                bot.send_message(chat_id, "❌ API Error: Server sent HTML instead of JSON. Check SiteGround Bot Protection.")
            print("Raw Response Content:", response.text[:200]) # Logs the HTML error for you in Render
            return None

    except Exception as e:
        if chat_id:
            bot.send_message(chat_id, f"⚠️ Connection Failed: {str(e)[:50]}")
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

    bot.send_message(message.chat.id, "✅ *System Online*\nSelect an assignment to track:", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith('v_'))
def handle_details(c):
    # Convert ID to int
    target_id = int(c.data.split('_')[1])
    
    data = fetch_data(c.message.chat.id)
    if not data: return

    task = next((t for t in data['assignments'] if t['assignment_id'] == target_id), None)

    if task:
        stats = task['statistics']
        not_sub = task['submissions']['not_submitted']
        names = "\n".join([f"• {x['trainee_name']}" for x in not_sub]) if not_sub else "✅ All Trainees Submitted!"
        
        # Calculate rate safely
        rate = round(float(stats.get('submission_rate', 0)), 1)

        report = (
            f"📊 *{task['title']}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕒 {task['time_info']}\n"
            f"📥 Submitted: *{stats['submitted_count']}*\n"
            f"❌ Missing: *{stats['not_submitted_count']}*\n"
            f"📈 Rate: *{rate}%*\n\n"
            f"🚫 *NOT SUBMITTED:* \n{names}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="go_back"))
        bot.edit_message_text(report, c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "go_back")
def go_back(c):
    bot.delete_message(c.message.chat.id, c.message.message_id)
    show_menu(c.message)

if __name__ == "__main__":
    bot.infinity_polling()
