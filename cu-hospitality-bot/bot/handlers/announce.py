import logging
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from bot.database import get_all_active_channels, insert_announcement, log_delivery
from bot.decorators import require_role
from bot.utils.keyboards import (
    build_channels_selection_keyboard, build_preview_action_keyboard,
    build_schedule_confirm_keyboard, build_media_keyboard
)
from bot.utils.formatters import format_announcement
from bot.config import TIMEZONE
from bot.scheduler import scheduler, broadcast_announcement

logger = logging.getLogger(__name__)

# Simplified states: Title → Ask Media → Media Recv → Body → Channels → Action → Schedule
ANN_TITLE, ANN_ASK_MEDIA, ANN_MEDIA, ANN_BODY, ANN_CHANNELS, ANN_ACTION, ANN_SCHEDULE = range(20, 27)

# Keep these for compatibility with other files that import them
ANN_CATEGORY = 25
ANN_PRIORITY = 26
ANN_MEDIA = 27


@require_role("announcer")
async def announce_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point — initialize ann_data and ask for title."""
    ann_body = context.user_data.get("ann_body")

    context.user_data["ann_data"] = {
        "category": "general",
        "priority": "normal",
        "title": "",
        "body": ann_body or "",
        "media_type": None,
        "media_file_id": None,
        "target_channels": [],
        "scheduled_for": None
    }

    if update.callback_query:
        await update.callback_query.answer()

    await update.effective_message.reply_text(
        "📢 <b>New Announcement</b>\n\n"
        "Step 1: Enter a short title for this announcement:",
        parse_mode="HTML"
    )
    return ANN_TITLE


async def ann_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text == "/keep":
        text = context.user_data["ann_data"].get("title", "")
    
    if not text:
        await update.message.reply_text("Title cannot be empty. Try again.")
        return ANN_TITLE
    if len(text) > 100:
        await update.message.reply_text("Title is too long (max 100 chars). Try again.")
        return ANN_TITLE

    context.user_data["ann_data"]["title"] = text

    await update.message.reply_text(
        "Step 2: Would you like to add an image or poster to this announcement?",
        reply_markup=build_media_keyboard()
    )
    return ANN_ASK_MEDIA

async def ann_ask_media_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "ann_cancel":
        await query.edit_message_text("Announcement cancelled.")
        return ConversationHandler.END
        
    if query.data == "med_photo":
        await query.edit_message_text("Step 2.5: Please send the image/poster now (as a Photo).")
        return ANN_MEDIA
        
    # med_skip
    await _prompt_body_query(query, context)
    return ANN_BODY

async def ann_media_recv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data["ann_data"]["media_type"] = "photo"
        context.user_data["ann_data"]["media_file_id"] = update.message.photo[-1].file_id
    
    await _prompt_body_msg(update.message, context)
    return ANN_BODY

async def _prompt_body_query(query, context):
    body = context.user_data["ann_data"].get("body")
    if body:
        await query.edit_message_text(
            f"Step 3: Message Body\n\n"
            f"Here is the current message. Copy it, paste & edit in your text box, and send it back. Or type /keep to keep it as is:\n\n"
            f"<code>{body}</code>",
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text(
            "Step 3: Type your announcement message below.\n\n"
            "Write it exactly as you want it to appear in the channel:"
        )

async def _prompt_body_msg(message_obj, context):
    body = context.user_data["ann_data"].get("body")
    if body:
        await message_obj.reply_text(
            f"Step 3: Message Body\n\n"
            f"Here is the current message. Copy it, paste & edit in your text box, and send it back. Or type /keep to keep it as is:\n\n"
            f"<code>{body}</code>",
            parse_mode="HTML"
        )
    else:
        await message_obj.reply_text(
            "Step 3: Type your announcement message below.\n\n"
            "Write it exactly as you want it to appear in the channel:"
        )


async def ann_body(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text.strip() == "/keep":
        text = context.user_data["ann_data"].get("body", "")

    context.user_data["ann_data"]["body"] = text

    return await show_channels_selection(update, context, update.message)


async def show_channels_selection(update, context, message_obj):
    supabase = context.bot_data.get("supabase")
    channels = await get_all_active_channels(supabase)
    context.user_data["active_channels"] = channels

    if not channels:
        await message_obj.reply_text(
            "⚠️ No channels registered yet.\n\n"
            "Ask an executive to add channels via /channels first."
        )
        return ConversationHandler.END

    kb = build_channels_selection_keyboard(channels, context.user_data["ann_data"]["target_channels"])
    await message_obj.reply_text("Step 3: Select Target Channels", reply_markup=kb)
    return ANN_CHANNELS


async def ann_channels_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    selected = list(context.user_data["ann_data"]["target_channels"])
    channels = context.user_data.get("active_channels", [])

    if data == "ann_cancel":
        await query.answer()
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END

    elif data == "sel_confirm":
        if not selected:
            await query.answer("You must select at least one channel!", show_alert=True)
            return ANN_CHANNELS
        await query.answer()
        context.user_data["ann_data"]["target_channels"] = selected
        return await show_preview(update, context, query.message.chat_id)

    elif data == "sel_all":
        await query.answer()
        selected = [ch["id"] for ch in channels]

    elif data == "sel_clear":
        await query.answer()
        selected = []

    elif data.startswith("sel_chan_"):
        await query.answer()
        ch_id = int(data.split("_")[2])
        if ch_id in selected:
            selected.remove(ch_id)
        else:
            selected.append(ch_id)

    context.user_data["ann_data"]["target_channels"] = selected
    kb = build_channels_selection_keyboard(channels, selected)
    await query.edit_message_reply_markup(reply_markup=kb)
    return ANN_CHANNELS


async def show_preview(update, context, chat_id):
    """Send the announcement body as preview, then the action keyboard."""
    ann_data = context.user_data["ann_data"]
    preview_text = "<b>PREVIEW</b>\n\n" + format_announcement(ann_data, update.effective_user.full_name)
    
    if ann_data.get("media_file_id"):
        if len(preview_text) <= 1024:
            await context.bot.send_photo(chat_id=chat_id, photo=ann_data["media_file_id"], caption=preview_text, parse_mode="HTML")
        else:
            await context.bot.send_photo(chat_id=chat_id, photo=ann_data["media_file_id"])
            await context.bot.send_message(chat_id=chat_id, text=preview_text, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=chat_id, text=preview_text, parse_mode="HTML")
    await context.bot.send_message(
        chat_id=chat_id,
        text="Step 4: What would you like to do?",
        reply_markup=build_preview_action_keyboard()
    )
    return ANN_ACTION


async def ann_action_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data
    supabase = context.bot_data.get("supabase")
    ann_data = context.user_data["ann_data"]
    user_id = update.effective_user.id

    if action == "ann_cancel":
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END

    elif action == "act_draft":
        res = await insert_announcement(
            supabase, **ann_data, created_by=user_id, status="draft"
        )
        old_draft_id = ann_data.get("draft_id")
        if old_draft_id and old_draft_id != res["id"]:
            from bot.database import update_announcement
            await update_announcement(supabase, old_draft_id, status="cancelled")
        
        await query.edit_message_text("💾 Draft saved successfully!")
        return ConversationHandler.END

    elif action == "act_edit":
        await query.edit_message_text("Restarting. Enter a new title:")
        return ANN_TITLE

    elif action == "act_schedule":
        await query.edit_message_text(
            "Step 5: Schedule Time\n\n"
            "Enter date and time in format:\n"
            "<code>YYYY-MM-DD HH:MM</code> (24-hour, WAT)\n\n"
            "Example: 2025-05-18 07:30",
            parse_mode="HTML"
        )
        return ANN_SCHEDULE

    elif action == "act_send":
        await query.edit_message_text("📤 Sending...")

        now = datetime.now(pytz.utc).isoformat()
        res = await insert_announcement(
            supabase, **ann_data, created_by=user_id, status="sent", sent_at=now
        )
        ann_id = res["id"]
        
        old_draft_id = ann_data.get("draft_id")
        if old_draft_id and old_draft_id != ann_id:
            from bot.database import update_announcement
            await update_announcement(supabase, old_draft_id, status="cancelled")

        text = format_announcement(ann_data, update.effective_user.full_name)
        success_count = 0
        fail_count = 0

        from bot.database import get_channel_by_id, deactivate_channel
        for ch_id in ann_data["target_channels"]:
            channel = await get_channel_by_id(supabase, ch_id)
            if not channel or not channel["is_active"]:
                await log_delivery(supabase, ann_id, ch_id, None, "failed", "Inactive channel")
                fail_count += 1
                continue

            try:
                if ann_data.get("media_file_id"):
                    if len(text) <= 1024:
                        msg = await context.bot.send_photo(chat_id=channel["chat_id"], photo=ann_data["media_file_id"], caption=text)
                    else:
                        await context.bot.send_photo(chat_id=channel["chat_id"], photo=ann_data["media_file_id"])
                        msg = await context.bot.send_message(chat_id=channel["chat_id"], text=text)
                else:
                    msg = await context.bot.send_message(chat_id=channel["chat_id"], text=text)
                await log_delivery(supabase, ann_id, ch_id, msg.message_id, "delivered")
                success_count += 1
            except Exception as e:
                if "Forbidden" in str(e):
                    await deactivate_channel(supabase, ch_id)
                await log_delivery(supabase, ann_id, ch_id, None, "failed", str(e))
                fail_count += 1

        report = (
            f"📤 <b>Broadcast Complete</b>\n\n"
            f"✅ Delivered: {success_count} channel(s)\n"
            f"❌ Failed: {fail_count}\n\n"
            f"⏱ {datetime.now(pytz.timezone(TIMEZONE)).strftime('%d %b %Y, %I:%M %p %Z')}"
        )
        await context.bot.send_message(chat_id=user_id, text=report, parse_mode="HTML")

        context.user_data.pop("ann_body", None)
        context.user_data.pop("ann_category", None)
        return ConversationHandler.END


async def ann_schedule_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    tz = pytz.timezone(TIMEZONE)
    try:
        dt_naive = datetime.strptime(text, "%Y-%m-%d %H:%M")
        dt_aware = tz.localize(dt_naive)

        if dt_aware <= datetime.now(tz):
            await update.message.reply_text("Time must be in the future. Try again.")
            return ANN_SCHEDULE

        context.user_data["ann_data"]["scheduled_for"] = dt_aware.astimezone(pytz.utc).isoformat()
        context.user_data["temp_dt_aware"] = dt_aware

        await update.message.reply_text(
            f"⏰ Scheduled for {dt_aware.strftime('%A, %d %b %Y at %I:%M %p %Z')}",
            reply_markup=build_schedule_confirm_keyboard()
        )
        return ANN_SCHEDULE
    except ValueError:
        await update.message.reply_text("Invalid format. Use YYYY-MM-DD HH:MM")
        return ANN_SCHEDULE


async def ann_schedule_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data
    if action == "ann_cancel":
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END
    elif action == "sch_change":
        await query.edit_message_text("Enter the new date and time (YYYY-MM-DD HH:MM):")
        return ANN_SCHEDULE
    elif action == "sch_confirm":
        supabase = context.bot_data.get("supabase")
        ann_data = context.user_data["ann_data"]
        user_id = update.effective_user.id

        res = await insert_announcement(
            supabase, **ann_data, created_by=user_id, status="scheduled"
        )
        
        old_draft_id = ann_data.get("draft_id")
        if old_draft_id and old_draft_id != res["id"]:
            from bot.database import update_announcement
            await update_announcement(supabase, old_draft_id, status="cancelled")

        dt_aware = context.user_data["temp_dt_aware"]
        ann_id = res["id"]

        application = context.application
        scheduler.add_job(
            broadcast_announcement,
            trigger="date",
            run_date=dt_aware,
            args=[application, ann_id],
            id=str(ann_id),
            replace_existing=True
        )

        await query.edit_message_text(
            f"✅ Scheduled for {dt_aware.strftime('%d %b %Y, %I:%M %p')}."
        )
        return ConversationHandler.END
