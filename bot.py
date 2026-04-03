import telebot
import requests
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION ---
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
# Your SiteGround API URL
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def get_data():
    """Fetches the latest assignment data from the PHP API."""
    try:
        response = requests.get(API_URL, timeout=20)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Error: Status {response.status_code}")
            return None
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

def format_assignment_msg(task):
    """Formats the specific assignment details into a readable Markdown message."""
    stats = task.get('statistics', {})
    subs = task.get('submissions', {})
    
    # Extract missing names from the JSON list
    missing_names = [t['trainee_name'] for t in subs.get('not_submitted', [])]
    missing_str = "\n".join([f"• {name}" for name in missing_names]) if missing_names else "✅ All Trainees Submitted!"
    
    # Handle the long decimal in submission_rate
    rate = task['statistics'].get('submission_rate', 0)
    formatted_rate = round(float(rate), 1)

    msg = (
        f"📊 *{task.get('title')}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏳ *Status:* {task.get('time_info')}\n\n"
        f"📥 Submitted: *{stats.get('submitted_count', 0)}*\n"
        f"❌ Missing: *{stats.get('not_submitted_count', 0)}*\n"
        f"📈 Rate: *{formatted_rate}%*\n\n"
        f"🚫 *NOT SUBMITTED YET:* \n{missing_str}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    return msg

@bot.message_handler(commands=['start', 'menu', 'track'])
def send_welcome(message):
    """Main menu showing all available assignments as buttons."""
    data = get_data()
    
    if not data or 'assignments' not in data:
        bot.send_message(message.chat.id, "❌ *API Error:* Could not retrieve data from the server.", parse_mode='Markdown')
        return

    markup = InlineKeyboardMarkup()
    
    # Loop through all 6 assignments found in JSON
    for task in data['assignments']:
        t_id = task.get('assignment_id')
        t_title = task.get('title', 'Unknown Task')
        
        # Limit title length for the button
        short_title = (t_title[:30] + '..') if len(t_title) > 30 else t_title
        markup.add(InlineKeyboardButton(f"📝 {short_title}", callback_data=f"task_{t_id}"))

    bot.send_message(
        message.chat.id, 
        "🔍 *MMI Assignment Tracker*\nSelect an assignment to see the missing trainees:", 
        reply_markup=markup, 
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith('task_'))
def handle_task_selection(c):
    """Triggered when a specific assignment button is clicked."""
    try:
        # Get the ID from the callback and convert to INT to match JSON
        selected_id = int(c.data.replace('task_', ''))
    except:
        bot.answer_callback_query(c.id, "Invalid ID format.")
        return

    data = get_data()
    if not data:
        bot.answer_callback_query(c.id, "Error fetching data.")
        return

    # Find the EXACT task in the list that matches the clicked assignment_id
    selected_task = next((t for t in data['assignments'] if t.get('assignment_id') == selected_id), None)

    if selected_task:
        msg = format_assignment_msg(selected_task)
        
        # Add a back button
        back_markup = InlineKeyboardMarkup()
        back_markup.add(InlineKeyboardButton("⬅️ Back to List", callback_data="back_to_menu"))
        
        bot.edit_message_text(
            msg, 
            c.message.chat.id, 
            c.message.message_id, 
            parse_mode='Markdown', 
            reply_markup=back_markup
        )
    else:
        bot.answer_callback_query(c.id, f"Could not find Task #{selected_id}")

@bot.callback_query_handler(func=lambda c: c.data == "back_to_menu")
def handle_back_to_menu(c):
    """Deletes current message and re-opens the main menu."""
    bot.delete_message(c.message.chat.id, c.message.message_id)
    send_welcome(c.message)

if __name__ == "__main__":
    print("🚀 MMI Bot is starting...")
    bot.infinity_polling()
