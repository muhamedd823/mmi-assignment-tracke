import telebot
import requests
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def get_data():
    """Fetches and validates the JSON data from SiteGround."""
    try:
        response = requests.get(API_URL, timeout=25)
        # Check if the site is returning 200 OK
        if response.status_code != 200:
            print(f"Server Error: {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        print(f"Fetch failure: {e}")
        return None

def format_assignment_msg(task):
    """Formats the specific assignment details."""
    stats = task.get('statistics', {})
    subs = task.get('submissions', {})
    
    # Get the list of names from the 'not_submitted' array
    missing_names = [t['trainee_name'] for t in subs.get('not_submitted', [])]
    missing_str = "\n".join([f"• {name}" for name in missing_names]) if missing_names else "✅ Everyone has submitted!"
    
    # Handle the long decimal formatting
    raw_rate = stats.get('submission_rate', 0)
    formatted_rate = round(float(raw_rate), 1)

    return (
        f"📊 *{task.get('title')}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏳ *Status:* {task.get('time_info')}\n\n"
        f"📥 Submitted: *{stats.get('submitted_count', 0)}*\n"
        f"❌ Missing: *{stats.get('not_submitted_count', 0)}*\n"
        f"📈 Rate: *{formatted_rate}%*\n\n"
        f"🚫 *NOT SUBMITTED:* \n{missing_str}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    data = get_data()
    
    # If data is None, it means the API is failing or JSON is invalid
    if not data or 'assignments' not in data:
        bot.send_message(message.chat.id, "❌ *API Error*\nCheck your Render logs or visit the API URL in a browser to see if it loads correctly.", parse_mode='Markdown')
        return

    markup = InlineKeyboardMarkup()
    for task in data['assignments']:
        # Match your JSON key 'assignment_id'
        t_id = task.get('assignment_id')
        t_title = task.get('title', 'Assignment')
        
        # Create unique callback data
        markup.add(InlineKeyboardButton(f"📝 {t_title[:30]}", callback_data=f"task_{t_id}"))

    bot.send_message(message.chat.id, "🔍 *MMI Tracker*\nSelect a task to view details:", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith('task_'))
def handle_task_selection(c):
    # Convert callback string ID to integer
    try:
        selected_id = int(c.data.split('_')[1])
    except:
        return bot.answer_callback_query(c.id, "Invalid ID.")

    data = get_data()
    if not data:
        return bot.answer_callback_query(c.id, "API Error during fetch.")

    # Find the specific assignment in the list
    selected_task = next((t for t in data['assignments'] if t.get('assignment_id') == selected_id), None)

    if selected_task:
        back_markup = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back to List", callback_data="back_to_menu"))
        bot.edit_message_text(
            format_assignment_msg(selected_task),
            c.message.chat.id,
            c.message.message_id,
            parse_mode='Markdown',
            reply_markup=back_markup
        )
    else:
        bot.answer_callback_query(c.id, "Task data not found.")

@bot.callback_query_handler(func=lambda c: c.data == "back_to_menu")
def handle_back(c):
    bot.delete_message(c.message.chat.id, c.message.message_id)
    send_welcome(c.message)

if __name__ == "__main__":
    print("🚀 Bot is polling...")
    bot.infinity_polling()
