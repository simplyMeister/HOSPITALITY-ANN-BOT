from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from bot.database import upsert_user, get_user, update_user_role
from bot.decorators import require_role
from bot.utils.keyboards import build_start_keyboard
from bot.config import UNIT_HEAD_IDS, UNIT_NAME

PROMOTE_USER_ID, PROMOTE_ROLE = range(2)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command: Register user, show welcome message and menu."""
    user = update.effective_user
    supabase = context.bot_data.get("supabase")
    
    # Upsert user
    full_name = user.full_name
    username = user.username
    await upsert_user(supabase, user.id, username, full_name)
    
    # Determine role for UI
    db_user = await get_user(supabase, user.id)
    role = db_user["role"] if db_user else "viewer"
    if user.id in UNIT_HEAD_IDS:
        role = "unit_head"
        
    text = (
        "🙏 Welcome to the Hospitality Unit Announcement Bot\n"
        "Covenant University Chapel\n\n"
        '"Serve one another humbly in love." — Galatians 5:13\n\n'
        "Use /help to see available commands."
    )
    
    keyboard = build_start_keyboard(role)
    await update.message.reply_text(text, reply_markup=keyboard)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command: List available commands based on role."""
    user = update.effective_user
    supabase = context.bot_data.get("supabase")
    db_user = await get_user(supabase, user.id)
    role = db_user["role"] if db_user else "viewer"
    if user.id in UNIT_HEAD_IDS:
        role = "unit_head"
        
    help_text = "<b>Available Commands:</b>\n\n"
    help_text += "👤 <b>Everyone:</b>\n"
    help_text += "• /start - Main menu and registration\n"
    help_text += "• /help - Show this help message\n"
    help_text += "• /cancel - Cancel any ongoing action\n\n"
    
    if role in ["announcer", "executive", "unit_head"]:
        help_text += "📢 <b>Announcers:</b>\n"
        help_text += "• /announce - Compose and send a new announcement\n"
        help_text += "• /drafts - View and manage saved drafts\n"
        help_text += "• /schedule - View and manage scheduled announcements\n"
        help_text += "• /templates - Manage announcement templates\n\n"
        
    if role in ["executive", "unit_head"]:
        help_text += "⚙️ <b>Executives:</b>\n"
        help_text += "• /channels - Manage target groups and channels\n\n"
        
    if role == "unit_head":
        help_text += "👑 <b>Unit Head:</b>\n"
        help_text += "• /promote - Promote a user to a new role\n"
        
    await update.message.reply_text(help_text, parse_mode="HTML")

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel command: Stop any active conversation."""
    await update.message.reply_text(
        "Action cancelled. Returning to main menu.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# --- Promote Flow ---
@require_role("unit_head")
async def promote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Please enter the Telegram User ID of the person you want to promote.\n\n"
        "<i>(You can use /cancel to abort)</i>",
        parse_mode="HTML"
    )
    return PROMOTE_USER_ID

async def promote_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid ID. Please send a valid numeric User ID.")
        return PROMOTE_USER_ID
        
    context.user_data["promote_target_id"] = target_id
    supabase = context.bot_data.get("supabase")
    
    user = await get_user(supabase, target_id)
    if not user:
        await update.message.reply_text("User not found in the database. They must start the bot first.")
        return ConversationHandler.END
        
    keyboard = [
        [
            InlineKeyboardButton("Executive", callback_data="prm_executive"),
            InlineKeyboardButton("Announcer", callback_data="prm_announcer")
        ],
        [
            InlineKeyboardButton("Viewer", callback_data="prm_viewer"),
            InlineKeyboardButton("❌ Cancel", callback_data="prm_cancel")
        ]
    ]
    
    await update.message.reply_text(
        f"Target User: {user['full_name']} (@{user.get('username', 'N/A')})\n"
        f"Current Role: {user['role']}\n\n"
        f"Select new role:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PROMOTE_ROLE

async def promote_role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    if action == "prm_cancel":
        await query.edit_message_text("Promotion cancelled.")
        context.user_data.pop("promote_target_id", None)
        return ConversationHandler.END
        
    new_role = action.split("_")[1]
    target_id = context.user_data.get("promote_target_id")
    supabase = context.bot_data.get("supabase")
    
    await update_user_role(supabase, target_id, new_role)
    
    await query.edit_message_text(f"✅ User ID {target_id} has been updated to {new_role}.")
    
    # DM the user
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"✅ You have been granted the role of {new_role} in the {UNIT_NAME} Announcement Bot."
        )
    except Exception:
        pass
        
    context.user_data.pop("promote_target_id", None)
    return ConversationHandler.END
