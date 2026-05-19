import logging
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import ContextTypes
from bot.database import get_scheduled_announcements, update_announcement, get_announcement
from bot.decorators import require_role
from bot.utils.keyboards import build_scheduled_action_keyboard
from bot.utils.formatters import format_announcement
from bot.config import TIMEZONE
from bot.scheduler import scheduler

logger = logging.getLogger(__name__)

@require_role("announcer")
async def schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    supabase = context.bot_data.get("supabase")
    schedules = await get_scheduled_announcements(supabase)
    
    if not schedules:
        if update.callback_query:
            await update.callback_query.answer()
        await update.effective_message.reply_text("There are no scheduled announcements.")
        return
        
    if update.callback_query:
        await update.callback_query.answer()
        
    await update.effective_message.reply_text(f"📅 <b>Scheduled Announcements ({len(schedules)}):</b>", parse_mode="HTML")
    
    tz = pytz.timezone(TIMEZONE)
    for sch in schedules:
        dt = datetime.fromisoformat(sch["scheduled_for"]).astimezone(tz)
        time_str = dt.strftime("%d %b %Y, %I:%M %p")
        
        text = (
            f"📌 <b>{sch['title']}</b>\n"
            f"Category: {sch['category']}\n"
            f"Scheduled For: <b>{time_str}</b>\n"
            f"Targets: {len(sch['target_channels'])} channels"
        )
        await update.effective_message.reply_text(text, reply_markup=build_scheduled_action_keyboard(sch["id"]), parse_mode="HTML")

@require_role("announcer")
async def schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    supabase = context.bot_data.get("supabase")
    
    if action.startswith("schd_cancel_"):
        s_id = int(action.split("_")[2])
        await update_announcement(supabase, s_id, status="cancelled")
        try:
            scheduler.remove_job(str(s_id))
        except Exception:
            pass
        await query.edit_message_text("❌ Scheduled announcement cancelled.")
        
    elif action.startswith("schd_prev_"):
        s_id = int(action.split("_")[2])
        ann = await get_announcement(supabase, s_id)
        if ann:
            text = format_announcement(ann, "System Preview")
            if ann.get("media_file_id"):
                if ann["media_type"] == "photo":
                    await query.message.reply_photo(photo=ann["media_file_id"], caption=text, parse_mode="HTML")
                else:
                    await query.message.reply_document(document=ann["media_file_id"], caption=text, parse_mode="HTML")
            else:
                await query.message.reply_text(text, parse_mode="HTML")
                
    elif action.startswith("schd_resch_"):
        await query.edit_message_text("To reschedule, please cancel this and create a new one from Drafts (or recreate it).")
