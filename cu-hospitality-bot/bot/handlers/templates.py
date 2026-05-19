import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.database import get_all_templates, get_template_by_id, insert_template, update_template, delete_template
from bot.decorators import require_role
from bot.utils.keyboards import build_templates_main_keyboard, build_category_keyboard

logger = logging.getLogger(__name__)

TPL_NAME, TPL_CAT, TPL_BODY = range(10, 13)
TPL_EDIT_SELECT, TPL_EDIT_ACTION, TPL_EDIT_VALUE = range(13, 16)

@require_role("announcer")
async def templates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        
    await update.effective_message.reply_text(
        "📑 <b>Template Management</b>\n\n"
        "Select an action below:",
        reply_markup=build_templates_main_keyboard(),
        parse_mode="HTML"
    )

@require_role("announcer")
async def templates_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    supabase = context.bot_data.get("supabase")
    
    if action == "tpl_new":
        await query.edit_message_text("➕ <b>New Template</b>\n\nEnter a unique name for this template:\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        return TPL_NAME
        
    elif action == "tpl_view":
        templates = await get_all_templates(supabase)
        if not templates:
            await query.edit_message_text("No templates found.")
            return ConversationHandler.END
            
        text = "📋 <b>Saved Templates:</b>\n\n"
        for t in templates:
            text += f"• <b>{t['name']}</b> ({t['category']})\n"
        await query.edit_message_text(text, parse_mode="HTML")
        return ConversationHandler.END
        
    elif action == "tpl_use":
        templates = await get_all_templates(supabase)
        if not templates:
            await query.edit_message_text("No templates found.")
            return ConversationHandler.END
            
        keyboard = []
        for t in templates:
            keyboard.append([InlineKeyboardButton(t["name"], callback_data=f"tpl_sel_{t['id']}")])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="ann_cancel")])
        
        await query.edit_message_text("Select a template to use:", reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END # Will be handled by announce.py or a generic callback
        
    elif action.startswith("tpl_sel_"):
        # Selected a template to use
        t_id = int(action.split("_")[2])
        from bot.database import get_template_by_id
        t = await get_template_by_id(supabase, t_id)
        if t:
            context.user_data["ann_data"] = {
                "category": "general",
                "priority": "normal",
                "title": t["name"], # Auto-fill title with template name
                "body": t["body"],
                "media_type": None,
                "media_file_id": None,
                "target_channels": [],
                "scheduled_for": None
            }
            
            from bot.handlers.announce import ANN_ASK_MEDIA
            from bot.utils.keyboards import build_media_keyboard
            
            await query.edit_message_text(
                "📢 <b>New Announcement from Template</b>\n\n"
                f"Title auto-set to: <b>{t['name']}</b>\n\n"
                "Step 2: Would you like to add an image or poster to this announcement?",
                reply_markup=build_media_keyboard(),
                parse_mode="HTML"
            )
            return ANN_ASK_MEDIA
        return ConversationHandler.END

# --- Create Flow ---
async def tpl_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tpl_name"] = update.message.text.strip()
    await update.message.reply_text("Great. Now send the message body for this template.\n\nYou can use placeholders: {date}, {time}, {unit_name}, {chapel_name}.")
    return TPL_BODY

async def tpl_body(update: Update, context: ContextTypes.DEFAULT_TYPE):
    body = update.message.text
    name = context.user_data["tpl_name"]
    
    supabase = context.bot_data.get("supabase")
    res = await insert_template(supabase, name=name, category="general", body=body, created_by=update.effective_user.id)
    
    if res:
        await update.message.reply_text("✅ Template saved successfully!")
    else:
        await update.message.reply_text("❌ Failed to save template. Name might already exist.")
        
    return ConversationHandler.END
