import telebot
import requests
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION ---
# Ensure this token is correct
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
# Ensure this URL is exactly as it appears in your browser
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def get_data(chat_id=None):
    """
    Fetches data from SiteGround. 
    Includes a User-Agent to bypass SiteGround's security firewall.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    try:
        # Increase timeout to 30 seconds for slower server responses
        response = requests.get(API_URL, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            if chat_id:
                bot.send_message(chat_id, f"⚠️ Server rejected request. Status Code: {response.status_code}")
            return None
    except Exception as e:
        if chat_id:
            bot.send_message(chat_id, f"❌ Connection Error: {str(e)[:100]}")
        print(f"Error: {e}")
        return None

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    """Fetches assignments and creates the menu buttons."""
    data = get_data(message.chat.id)
    
    if not data or 'assignments' not in data:
        # If get_data failed, it already sent a specific error message
        return

    markup = InlineKeyboardMarkup()
    
    for task in data['assignments']:
        t_id = task.get('assignment_id')
        t_title = task.get('title', 'Assignment')
        
        # Display short title on button
        short_title = (t_title[:25] + '...') if len(t_title) > 25 else t_title
        markup.add(InlineKeyboardButton(f"📝 {short_title}", callback_data=f"view_{t_id}"))

    bot.send_message(
        message.chat.id, 
        "✅ *Connected to LMS*\nSelect an assignment to see tracking details:", 
        reply_markup=markup, 
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith('view_'))
def handle_selection(c):
    """Shows details for the specific assignment clicked."""
    try:
        selected_id = int(c.data.split('_')[1])
    except:
        return bot.answer_callback_query(c.id, "Invalid Assignment ID.")

    data = get_data(c.message.chat.id)
    if not data:
        return

    # Find the specific assignment object in the JSON array
    task = next((t for t in data['assignments'] if t.get('assignment_id') == selected_id), None)

    if task:
        stats = task.get('statistics', {})
        subs = task.get('submissions', {})
        
        # List names of trainees who haven't submitted
        missing_list = [t['trainee_name'] for t in subs.get('not_submitted', [])]
        missing_text = "\n".join([f"• {name}" for name in missing_list]) if missing_list else "🎉 All trainees submitted!"

        # Format the rate to 1 decimal place
        rate = round(float(stats.get('submission_rate', 0)), 1)

        msg = (
            f"📊 *{task['title']}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏳ *Status:* {task.get('time_info')}\n\n"
            f"📥 Submitted: *{stats.get('submitted_count', 0)}*\n"
            f"❌ Missing: *{stats.get('not_submitted_count', 0)}*\n"
            f"📈 Rate: *{rate}%*\n\n"
            f"🚫 *NOT SUBMITTED:* \n{missing_text}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        back_btn = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_home"))
        bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=back_btn)
    else:
        bot.answer_callback_query(c.id, "Assignment details not found.")

@bot.callback_query_handler(func=lambda c: c.data == "back_home")
def back_home(c):
    """Deletes current message and re-runs the start menu."""
    bot.delete_message(c.message.chat.id, c.message.message_id)
    send_welcome(c.message)

if __name__ == "__main__":
    print("🚀 MMI Tracking Bot is now running...")
    bot.infinity_polling()
