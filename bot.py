import telebot
from curl_cffi import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

# --- CONFIG ---
# Replace with your actual token if this one is a placeholder
BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
API_URL = 'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN)

# Advanced Fetcher to bypass Web Application Firewalls (WAF)
def fetch_mmi_data():
    try:
        # Headers make the request look like it is coming from a Windows PC
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://lms.mersamedia.org/",
        }
        
        # impersonate="chrome" mimics the TLS fingerprint of Google Chrome
        response = requests.get(API_URL, impersonate="chrome", headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API Error: Server returned status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"⚠️ Connection Error: {str(e)}")
        return None

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    print(f"User {message.chat.id} started the bot.")
    data = fetch_mmi_data()
    
    if not data or 'assignments' not in data:
        bot.reply_to(message, "❌ *Unable to connect to MMI Database.*\n\nPossible reasons:\n1. SiteGround is blocking the Render server IP.\n2. The PHP script has a syntax error.\n3. The Secret Key is incorrect.", parse_mode='Markdown')
        return

    markup = InlineKeyboardMarkup()
    for item in data['assignments']:
        # Creates a button for each assignment
        btn_text = f"📝 {item['title'][:25]}..."
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"v_{item['assignment_id']}"))

    bot.send_message(message.chat.id, "📊 *MMI Assignment Tracker*\nSelect an assignment to view a comprehensive report:", 
                     reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('v_'))
def show_details(call):
    target_id = int(call.data.split('_')[1])
    data = fetch_mmi_data()
    
    if not data:
        bot.answer_callback_query(call.id, "Error: Data unavailable.")
        return

    # Find the specific assignment from the API data
    task = next((x for x in data['assignments'] if x['assignment_id'] == target_id), None)
    
    if task:
        stats = task['statistics']
        subs = task['submissions']
        
        # Build trainee lists using the keys from your working PHP JSON
        on_time_list = "\n".join([f"• {p['trainee_name']}" for p in subs['on_time']]) if subs['on_time'] else "None"
        late_list = "\n".join([f"• {p['trainee_name']} ⏰" for p in subs['late']]) if subs['late'] else "None"
        missing_list = "\n".join([f"• {p['trainee_name']}" for p in subs['not_submitted']]) if subs['not_submitted'] else "All Clear! 🎉"

        report = (
            f"📌 *{task['title']}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕒 *Timing:* {task['time_info']}\n"
            f"📈 *Submission Rate:* {round(stats['submission_rate'], 1)}%\n"
            f"📥 *Count:* {stats['submitted_count']} Submitted | {stats['not_submitted_count']} Missing\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ *ON TIME ({len(subs['on_time'])}):*\n{on_time_list}\n\n"
            f"⚠️ *LATE ({len(subs['late'])}):*\n{late_list}\n\n"
            f"🚫 *NOT SUBMITTED ({len(subs['not_submitted'])}):*\n{missing_list}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Back to List", callback_data="back_home"))
        
        bot.edit_message_text(report, call.message.chat.id, call.message.message_id, 
                              parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def back_to_menu(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_welcome(call.message)

if __name__ == "__main__":
    print("Bot is successfully running...")
    bot.infinity_polling()
