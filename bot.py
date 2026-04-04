import asyncio
import requests
import threading
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ================== CONFIG ==================
BOT_TOKEN = "8679659340:AAFDka-7x6doy5e_9areii48bKXOy5Egh-s"
API_URL = "https://lms.mersamedia.org/api_assignment_tracking.php?key=MMI_SECRET_2026"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
# ===========================================

async def fetch_data():
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"API Error: {e}")
        return None


def format_time_ago(minutes_past: int) -> str:
    if minutes_past < 60:
        return f"{minutes_past} min ago"
    hours = minutes_past // 60
    if hours < 24:
        return f"{hours} hr ago"
    days = hours // 24
    return f"{days} day{'s' if days != 1 else ''} ago"


def minutes_to_human_late(minutes: int) -> str:
    if minutes <= 0:
        return "On time"
    if minutes < 60:
        return f"{minutes} min late"
    hours = minutes // 60
    mins_left = minutes % 60
    if hours < 24:
        if mins_left == 0:
            return f"{hours} hr late"
        return f"{hours} hr {mins_left} min late"
    days = hours // 24
    hours_left = hours % 24
    if hours_left == 0:
        return f"{days} day late"
    return f"{days} day {hours_left} hr late"


def create_assignment_buttons(assignments):
    keyboard = []
    active_count = 0
    for ass in assignments:
        mins = ass.get("minutes_past", 0)
        if (mins // 1440) <= 5:
            active_count += 1
            short_title = ass["title"][:38] + "..." if len(ass["title"]) > 38 else ass["title"]
            keyboard.append([InlineKeyboardButton(f"📌 {short_title}", callback_data=f"ass_{ass['assignment_id']}")])

    if not keyboard:
        keyboard.append([InlineKeyboardButton("No recent assignments", callback_data="none")])

    keyboard.append([InlineKeyboardButton("📋 View All Assignments", callback_data="all_assignments")])
    keyboard.append([InlineKeyboardButton("🔄 Refresh Data", callback_data="refresh")])
    return InlineKeyboardMarkup(keyboard), active_count


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Fetching data...")
    data = await fetch_data()
    if not data or "assignments" not in data:
        await update.message.reply_text("❌ Could not fetch data.")
        return

    context.bot_data["assignment_data"] = data
    keyboard, active = create_assignment_buttons(data["assignments"])
    text = f"📚 **Active Assignments** ({active})\nSelect one:"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = await fetch_data() or context.bot_data.get("assignment_data")
    if data and "assignments" in data:
        context.bot_data["assignment_data"] = data

    if not data or "assignments" not in data:
        await query.edit_message_text("❌ No data. Use /start")
        return

    action = query.data
    assignments = data["assignments"]

    if action == "refresh":
        await query.edit_message_text("✅ Refreshed!", reply_markup=create_assignment_buttons(assignments)[0])
        return

    if action == "all_assignments":
        text = "📋 **All Assignments**\n\n"
        for ass in assignments:
            time_str = format_time_ago(ass.get("minutes_past", 0))
            rate = round(ass["statistics"].get("submission_rate", 0), 1)
            text += f"**{ass['title']}**\n⏰ {time_str}\n📈 Rate: {rate}%\n\n"
        kb = [[InlineKeyboardButton("⬅ Back", callback_data="back_to_list")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    if action == "back_to_list":
        keyboard, _ = create_assignment_buttons(assignments)
        await query.edit_message_text("📚 Select an assignment:", reply_markup=keyboard)
        return

    if action.startswith("ass_"):
        ass_id = int(action[4:])
        selected = next((a for a in assignments if a["assignment_id"] == ass_id), None)
        if not selected:
            await query.edit_message_text("Assignment not found.")
            return

        context.bot_data["selected_assignment"] = selected
        time_str = format_time_ago(selected.get("minutes_past", 0))
        text = f"✅ **{selected['title']}**\n⏰ {time_str}\n\nChoose option:"

        keyboard = [
            [InlineKeyboardButton("📊 Summary", callback_data="summary_this")],
            [InlineKeyboardButton("❌ Missing & Late", callback_data="missing_this")],
            [InlineKeyboardButton("⏳ Remaining Time", callback_data="remaining_this")],
            [InlineKeyboardButton("⬅ Back to List", callback_data="back_to_list")],
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if action == "summary_this":
        ass = context.bot_data.get("selected_assignment")
        if not ass: return
        stats = ass["statistics"]
        rate = round(stats.get("submission_rate", 0), 1)
        total = stats["submitted_count"] + stats.get("not_submitted_count", 0)
        time_str = format_time_ago(ass.get("minutes_past", 0))
        text = f"📊 **Summary**\n**{ass['title']}**\n⏰ {time_str}\n\n✅ Submitted: {stats['submitted_count']}/{total}\n📈 Rate: {rate}%"
        kb = [[InlineKeyboardButton("⬅ Back", callback_data="back_to_selected")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    if action == "missing_this":
        ass = context.bot_data.get("selected_assignment")
        if not ass: return
        text = f"❌ **Missing & Late**\n**{ass['title']}**\n\n"
        late_list = ass["submissions"].get("late", [])
        not_sub_list = ass["submissions"].get("not_submitted", [])

        if late_list:
            text += "🟠 **Late Submissions:**\n"
            for s in late_list:
                late_min = s.get("late_by_minutes", 0)
                late_text = minutes_to_human_late(late_min)
                text += f"• {s['trainee_name']} — **{late_text}**\n"
            text += "\n"

        if not_sub_list:
            text += "🔴 **Not Submitted:**\n"
            for s in not_sub_list:
                text += f"• {s['trainee_name']}\n"

        if not late_list and not not_sub_list:
            text += "🎉 Everyone is on time!"

        kb = [[InlineKeyboardButton("⬅ Back", callback_data="back_to_selected")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    if action == "remaining_this":
        ass = context.bot_data.get("selected_assignment")
        if not ass: return
        time_str = format_time_ago(ass.get("minutes_past", 0))
        text = f"⏳ **Remaining Time**\n**{ass['title']}**\n\nDeadline passed **{time_str}** ago."
        kb = [[InlineKeyboardButton("⬅ Back", callback_data="back_to_selected")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    if action == "back_to_selected":
        ass = context.bot_data.get("selected_assignment")
        if ass:
            time_str = format_time_ago(ass.get("minutes_past", 0))
            text = f"✅ **{ass['title']}**\n⏰ {time_str}\n\nChoose action:"
            keyboard = [
                [InlineKeyboardButton("📊 Summary", callback_data="summary_this")],
                [InlineKeyboardButton("❌ Missing & Late", callback_data="missing_this")],
                [InlineKeyboardButton("⏳ Remaining Time", callback_data="remaining_this")],
                [InlineKeyboardButton("⬅ Back to List", callback_data="back_to_list")],
            ]
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


def main():
    print("🚀 Starting Assignment Tracking Bot on Render...")
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # Keep-alive thread for Render free tier
    def keep_alive():
        while True:
            print(f"[{time.strftime('%H:%M:%S')}] Bot keep-alive ping...")
            time.sleep(240)  # every 4 minutes

    threading.Thread(target=keep_alive, daemon=True).start()

    asyncio.run(main())
