import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.database import get_all_active_channels, get_channel_by_id, insert_channel, update_channel, deactivate_channel
from bot.decorators import require_role
from bot.utils.keyboards import build_channels_main_keyboard

logger = logging.getLogger(__name__)

# States for Register
REG_FORWARD, REG_NAME, REG_LABEL = range(3)
# States for Edit
EDIT_SELECT, EDIT_FIELD, EDIT_VALUE = range(3, 6)

# --- Main Entry ---
@require_role("executive")
async def channels_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        
    await update.effective_message.reply_text(
        "⚙️ <b>Channel Management</b>\n\n"
        "What would you like to do?",
        reply_markup=build_channels_main_keyboard(),
        parse_mode="HTML"
    )

@require_role("executive")
async def channels_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "chn_register":
        await query.edit_message_text(
            "➕ <b>Register a New Channel/Group</b>\n\n"
            "Please forward any message from the target group or channel to me.\n\n"
            "<i>(Type /cancel to abort)</i>",
            parse_mode="HTML"
        )
        return REG_FORWARD
        
    elif action == "chn_list":
        supabase = context.bot_data.get("supabase")
        channels = await get_all_active_channels(supabase)
        
        if not channels:
            await query.edit_message_text("No active channels registered.")
            return ConversationHandler.END
            
        text = "📋 <b>Active Channels:</b>\n\n"
        keyboard = []
        for ch in channels:
            label = f" ({ch['label']})" if ch['label'] else ""
            text += f"• {ch['name']}{label} - {ch['type']}\n"
            keyboard.append([
                InlineKeyboardButton(f"🧪 Test {ch['name']}", callback_data=f"chn_test_{ch['id']}"),
                InlineKeyboardButton(f"🗑️ Remove", callback_data=f"chn_rem_{ch['id']}")
            ])
            
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return ConversationHandler.END
        
    elif action.startswith("chn_test_"):
        ch_id = int(action.split("_")[2])
        supabase = context.bot_data.get("supabase")
        channel = await get_channel_by_id(supabase, ch_id)
        if not channel:
            await query.edit_message_text("Channel not found.")
            return ConversationHandler.END
            
        try:
            await context.bot.send_message(
                chat_id=channel["chat_id"],
                text="🧪 <b>Test Ping from Hospitality Bot!</b>",
                parse_mode="HTML"
            )
            await query.edit_message_text(f"✅ Test ping successful for {channel['name']}.")
        except Exception as e:
            await query.edit_message_text(f"❌ Test failed for {channel['name']}:\n{e}")
            
        return ConversationHandler.END
        
    elif action.startswith("chn_rem_"):
        ch_id = int(action.split("_")[2])
        supabase = context.bot_data.get("supabase")
        await deactivate_channel(supabase, ch_id)
        await query.edit_message_text("🗑️ Channel removed (deactivated).")
        return ConversationHandler.END

# --- Register Flow ---
async def reg_forward_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    
    # Check if forwarded
    if not msg.forward_origin:
        await msg.reply_text("This message doesn't seem to be forwarded from a channel or group. Try again or /cancel.")
        return REG_FORWARD
        
    # forward_origin can be various types
    origin = msg.forward_origin
    chat_id = None
    chat_type = None
    
    if hasattr(origin, 'chat'):
        chat_id = origin.chat.id
        chat_type = origin.chat.type
    elif hasattr(origin, 'sender_chat'):
        chat_id = origin.sender_chat.id
        chat_type = origin.sender_chat.type
    else:
        # User origin, not a group
        await msg.reply_text("This seems to be from a user. Please forward from a Group or Channel.")
        return REG_FORWARD
        
    context.user_data["reg_chat_id"] = chat_id
    context.user_data["reg_chat_type"] = chat_type
    
    await msg.reply_text("✅ Chat recognized. Please enter a Display Name for this channel:")
    return REG_NAME

async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_name"] = update.message.text.strip()
    await update.message.reply_text("Great. Now enter a Label (e.g., 'All Members', 'Executives') or type 'skip':")
    return REG_LABEL

async def reg_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    label = update.message.text.strip()
    if label.lower() == 'skip':
        label = None
        
    chat_id = context.user_data["reg_chat_id"]
    chat_type = context.user_data["reg_chat_type"]
    name = context.user_data["reg_name"]
    added_by = update.effective_user.id
    
    supabase = context.bot_data.get("supabase")
    res = await insert_channel(supabase, chat_id, name, chat_type, label, added_by)
    
    if res:
        await update.message.reply_text(
            f"✅ Channel registered successfully!\n\n"
            f"Name: {name}\n"
            f"Label: {label or 'N/A'}\n\n"
            f"⚠️ <b>Make sure this bot is an admin in that chat!</b>",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ Failed to register channel. It might already exist.")
        
    # Clean up
    for k in ["reg_chat_id", "reg_chat_type", "reg_name"]:
        context.user_data.pop(k, None)
        
    return ConversationHandler.END
