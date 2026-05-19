import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import get_drafts_by_user, get_all_drafts, get_announcement, update_announcement, get_user
from bot.decorators import require_role
from bot.utils.keyboards import build_drafts_action_keyboard
from bot.handlers.announce import ANN_CATEGORY

logger = logging.getLogger(__name__)

@require_role("announcer")
async def drafts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    supabase = context.bot_data.get("supabase")
    
    # Check role
    user = await get_user(supabase, user_id)
    role = user["role"] if user else "viewer"
    from bot.config import UNIT_HEAD_IDS
    if user_id in UNIT_HEAD_IDS:
        role = "unit_head"
        
    if role in ["unit_head", "executive"]:
        drafts = await get_all_drafts(supabase)
    else:
        drafts = await get_drafts_by_user(supabase, user_id)
        
    if not drafts:
        if update.callback_query:
            await update.callback_query.answer()
        await update.effective_message.reply_text("You have no saved drafts.")
        return
        
    if update.callback_query:
        await update.callback_query.answer()
        
    await update.effective_message.reply_text(f"📝 <b>Saved Drafts ({len(drafts)}):</b>", parse_mode="HTML")
    
    for draft in drafts:
        text = (
            f"📌 <b>{draft['title']}</b>\n"
            f"Category: {draft['category']}\n"
            f"Created: {draft['created_at'][:10]}"
        )
        if draft.get("media_file_id"):
            await update.effective_message.reply_photo(
                photo=draft["media_file_id"],
                caption=text,
                reply_markup=build_drafts_action_keyboard(draft["id"]),
                parse_mode="HTML"
            )
        else:
            await update.effective_message.reply_text(
                text, 
                reply_markup=build_drafts_action_keyboard(draft["id"]), 
                parse_mode="HTML"
            )

@require_role("announcer")
async def drafts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    supabase = context.bot_data.get("supabase")
    
    if action.startswith("drf_delete_"):
        d_id = int(action.split("_")[2])
        await update_announcement(supabase, d_id, status="cancelled")
        await query.edit_message_text("🗑️ Draft deleted.")
        
    elif action.startswith("drf_send_"):
        # This is complex because we need targets and it might not have targets set if saved early
        await query.edit_message_text("To send a draft, please use 'Edit' and complete the missing steps.")
        
    elif action.startswith("drf_edit_"):
        d_id = int(action.split("_")[2])
        draft = await get_announcement(supabase, d_id)

        if draft:
            context.user_data["ann_data"] = {
                "draft_id": d_id,
                "category": draft.get("category", "general"),
                "priority": draft.get("priority", "normal"),
                "title": draft.get("title", ""),
                "body": draft.get("body", ""),
                "media_type": draft.get("media_type"),
                "media_file_id": draft.get("media_file_id"),
                "target_channels": draft.get("target_channels") or [],
                "scheduled_for": None
            }

            await query.edit_message_text(
                "✏️ <b>Editing Draft</b>\n\n"
                "Here is the current title. Copy & paste it to edit, or type /keep to keep it:\n\n"
                f"<code>{draft.get('title', 'No Title')}</code>\n\n"
                "Step 1: Enter your new title (or /keep):",
                parse_mode="HTML"
            )
            from bot.handlers.announce import ANN_TITLE
            return ANN_TITLE
