import telebot, requests, time, json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.background import BackgroundScheduler

BOT_TOKEN = '8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s'
YOUR_CHAT_ID = '7494977999'
API_URL = f'https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026'

bot = telebot.TeleBot(BOT_TOKEN)
sent_alerts = set()

def get_data():
    try:
        r = requests.get(API_URL, timeout=20)
        return r.json() if r.status_code == 200 else None
    except: return None

def format_msg(task, label="📊 MMI TRACKER"):
    stats = task.get('statistics', {})
    subs = task.get('submissions', {})
    late = "\n".join([f"• {x['trainee_name']}" for x in subs.get('late_submitted', [])[:10]])
    missing = "\n".join([f"• {x['trainee_name']}" for x in subs.get('not_submitted', [])[:15]])
    
    return (f"*{label}*\n━━━━━━━━━━━━\n📝 *{task.get('title')}*\n⏳ {task.get('time_info')}\n\n"
            f"✅ On-Time: {stats.get('on_time_count')}\n"
            f"📥 Late: {stats.get('late_count')}\n"
            f"❌ Missing: {stats.get('not_submitted_count')}\n"
            f"📈 Rate: {stats.get('submission_rate')}%\n\n"
            f"*LATE:* \n{late if late else 'None'}\n\n"
            f"*MISSING:* \n{missing if missing else 'None'}\n━━━━━━━━━━━━")

@bot.message_handler(commands=['start', 'menu'])
def menu(m):
    data = get_data()
    if not data: return bot.send_message(m.chat.id, "❌ API Error")
    markup = InlineKeyboardMarkup()
    for t in data['assignments']:
        markup.add(InlineKeyboardButton(f"📝 {t['title'][:30]}", callback_data=f"t_{t['id']}"))
    bot.send_message(m.chat.id, "🔍 Select Assignment:", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith('t_'))
def handle_t(c):
    tid = c.data.replace('t_', '')
    data = get_data()
    task = next((x for x in data['assignments'] if x['id'] == tid), None)
    if task:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="main"))
        bot.edit_message_text(format_msg(task), c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "main")
def back(c):
    bot.delete_message(c.message.chat.id, c.message.message_id)
    menu(c.message)

def auto():
    data = get_data()
    if not data: return
    for t in data['assignments']:
        d = t.get('time_difference_minutes', 0)
        for lbl, target in {"4H": -240, "3H": -180, "1H": -60, "PASSED": 1}.items():
            key = f"{t['id']}_{lbl}"
            if key not in sent_alerts and target <= d <= (target + 2):
                bot.send_message(YOUR_CHAT_ID, format_msg(t, f"🚨 {lbl} ALERT"), parse_mode='Markdown')
                sent_alerts.add(key)

sched = BackgroundScheduler()
sched.add_job(auto, 'interval', minutes=1)
sched.start()

print("🚀 Bot running...")
bot.infinity_polling()
