from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from bot.database import get_user
from bot.config import UNIT_HEAD_IDS

ROLES = {
    "unit_head": 4,
    "executive": 3,
    "announcer": 2,
    "viewer": 1,
}

def require_role(min_role: str):
    """
    Decorator to restrict access to handlers based on user roles.
    Checks UNIT_HEAD_IDS first to bootstrap access, then checks the database.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if not update.effective_user:
                return
            
            user_id = update.effective_user.id
            
            # Unit Heads from env override the database
            if user_id in UNIT_HEAD_IDS:
                user_role = "unit_head"
            else:
                supabase = context.bot_data.get("supabase")
                if supabase:
                    user = await get_user(supabase, user_id)
                    user_role = user["role"] if user else "viewer"
                else:
                    user_role = "viewer"
                
            if ROLES.get(user_role, 0) < ROLES.get(min_role, 0):
                if update.callback_query:
                    await update.callback_query.answer(f"❌ Requires {min_role} access.", show_alert=True)
                else:
                    await update.effective_message.reply_text(f"❌ You need {min_role} or higher privileges to use this command.")
                return
                
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator
