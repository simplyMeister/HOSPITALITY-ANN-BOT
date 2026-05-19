import logging
import warnings
from telegram import Update
from telegram.ext import Application, CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.warnings import PTBUserWarning

# per_message=False is intentional for this bot (single conversation per user)
warnings.filterwarnings("ignore", message=".*per_message=False.*", category=PTBUserWarning)
from bot.config import BOT_TOKEN, setup_logging
from bot.database import get_supabase, count_templates, seed_templates
from bot.scheduler import start_scheduler, restore_scheduled_jobs

from bot.handlers.general import start_cmd, help_cmd, cancel_cmd, promote_cmd, promote_user_id, promote_role_callback, PROMOTE_USER_ID, PROMOTE_ROLE
from bot.handlers.announce import (
    announce_cmd, ann_title, ann_ask_media_cb, ann_media_recv, ann_body,
    ann_channels_cb, ann_action_cb,
    ann_schedule_receive, ann_schedule_cb,
    ANN_TITLE, ANN_ASK_MEDIA, ANN_MEDIA, ANN_BODY, ANN_CHANNELS, ANN_ACTION, ANN_SCHEDULE
)
from bot.handlers.drafts import drafts_cmd, drafts_callback
from bot.handlers.schedule import schedule_cmd, schedule_callback
from bot.handlers.channels import (
    channels_cmd, channels_callback, reg_forward_msg, reg_name, reg_label,
    REG_FORWARD, REG_NAME, REG_LABEL
)
from bot.handlers.templates import (
    templates_cmd, templates_callback, tpl_name, tpl_body,
    TPL_NAME, TPL_BODY
)

logger = setup_logging()

SEED_TEMPLATES = [
    {
        "name": "Sunday Service Reminder",
        "category": "service_duty",
        "body": "Dear Hospitality Unit members, kindly be reminded of our service duty this Sunday. Please arrive 30 minutes before service time in your duty outfit. God bless your service. 🙏"
    },
    {
        "name": "Unit Meeting Notice",
        "category": "meeting",
        "body": "Dear team, there will be a unit meeting on {date} at {time}. Attendance is compulsory. Venue to be communicated. Thank you."
    },
    {
        "name": "Dress Code Reminder",
        "category": "dress_code",
        "body": "Please be reminded of the dress code for our next service duty. Ensure you are properly dressed in your unit uniform. First impressions matter. 👔"
    },
    {
        "name": "Special Program Notice",
        "category": "event",
        "body": "The {chapel_name} will be hosting a special program on {date}. As the Hospitality Unit, we are called to serve with excellence. More details to follow."
    },
    {
        "name": "Devotional Reminder",
        "category": "devotional",
        "body": "\"Whatever you do, work at it with all your heart, as working for the Lord.\" — Col. 3:23. Let this word guide your service today. God bless the Hospitality Unit. 🙏"
    },
    {
        "name": "Welfare Check",
        "category": "welfare",
        "body": "Greetings from the {unit_name} leadership. We are checking in on everyone. Please reach out to your group leader if you need any support. We care about you. ❤️"
    }
]

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    # Basic error handling
    if isinstance(context.error, Exception):
        err_msg = str(context.error)
        if "Forbidden" in err_msg:
            # We already handle this in broadcast directly
            pass

async def post_init(application: Application) -> None:
    """Runs after the bot initializes but before it starts polling."""
    logger.info("Initializing Supabase...")
    try:
        supabase = await get_supabase()
        application.bot_data["supabase"] = supabase
        logger.info("Supabase connected.")
        
        # Check templates
        tc = await count_templates(supabase)
        if tc == 0:
            logger.info("Seeding initial templates...")
            await seed_templates(supabase, SEED_TEMPLATES)
            logger.info("Templates seeded.")
            
        # Start scheduler
        logger.info("Starting scheduler and restoring jobs...")
        start_scheduler()
        # Since scheduler uses context, we need to pass a context.
        # application itself can be passed as context or we use application context
        # Wait, context is needed for `bot_data` and `bot`. 
        # Actually `application` has `bot` and `bot_data`.
        # To simulate a context, we can just pass `application` if we change `scheduler.py` 
        # to accept `application` or a custom wrapper.
        # Let's adjust `scheduler.py` to use `application` instead of `context`.
        from bot.scheduler import restore_scheduled_jobs
        await restore_scheduled_jobs(application)
        
    except Exception as e:
        logger.critical(f"Failed to initialize: {e}")
        import sys
        sys.exit(1)

def main():
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is missing in .env")
        return
        
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    application.add_error_handler(error_handler)

    # --- Simple Commands ---
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("cancel", cancel_cmd))
    application.add_handler(CommandHandler("drafts", drafts_cmd))
    application.add_handler(CommandHandler("schedule", schedule_cmd))
    application.add_handler(CommandHandler("channels", channels_cmd))
    application.add_handler(CommandHandler("templates", templates_cmd))

    # --- Callbacks ---
    application.add_handler(CallbackQueryHandler(drafts_callback, pattern="^drf_(?!edit_)"))
    application.add_handler(CallbackQueryHandler(schedule_callback, pattern="^schd_"))
    application.add_handler(CallbackQueryHandler(channels_callback, pattern="^chn_(?!register)"))
    application.add_handler(CallbackQueryHandler(templates_callback, pattern="^tpl_(?!new)"))

    # --- Start Callbacks from Main Menu ---
    # Route button clicks directly to the command functions
    application.add_handler(CallbackQueryHandler(drafts_cmd, pattern="^cmd_drafts$"))
    application.add_handler(CallbackQueryHandler(schedule_cmd, pattern="^cmd_schedule$"))
    application.add_handler(CallbackQueryHandler(templates_cmd, pattern="^cmd_templates$"))
    application.add_handler(CallbackQueryHandler(channels_cmd, pattern="^cmd_channels$"))

    # --- Promote Conversation ---
    promote_conv = ConversationHandler(
        entry_points=[CommandHandler("promote", promote_cmd)],
        states={
            PROMOTE_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, promote_user_id)],
            PROMOTE_ROLE: [CallbackQueryHandler(promote_role_callback, pattern="^prm_")]
        },
        fallbacks=[CommandHandler("cancel", cancel_cmd)],
        per_message=False
    )
    application.add_handler(promote_conv)

    # --- Channels Register Conversation ---
    channels_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(channels_callback, pattern="^chn_register$")],
        states={
            REG_FORWARD: [MessageHandler(filters.ALL & ~filters.COMMAND, reg_forward_msg)],
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REG_LABEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_label)]
        },
        fallbacks=[CommandHandler("cancel", cancel_cmd)],
        per_message=False
    )
    application.add_handler(channels_conv)

    # --- Templates Create Conversation ---
    templates_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(templates_callback, pattern="^tpl_new$")],
        states={
            TPL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, tpl_name)],
            TPL_BODY: [MessageHandler(filters.TEXT & ~filters.COMMAND, tpl_body)]
        },
        fallbacks=[CommandHandler("cancel", cancel_cmd)],
        per_message=False
    )
    application.add_handler(templates_conv)

    # --- Announce Conversation ---
    announce_conv = ConversationHandler(
        entry_points=[
            CommandHandler("announce", announce_cmd),
            CallbackQueryHandler(announce_cmd, pattern="^cmd_announce$"),
            CallbackQueryHandler(drafts_callback, pattern="^drf_edit_"),
            CallbackQueryHandler(templates_callback, pattern="^tpl_sel_")
        ],
        states={
            ANN_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ann_title)],
            ANN_ASK_MEDIA: [CallbackQueryHandler(ann_ask_media_cb, pattern="^med_|ann_cancel")],
            ANN_MEDIA: [MessageHandler(filters.PHOTO, ann_media_recv)],
            ANN_BODY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ann_body)],
            ANN_CHANNELS: [CallbackQueryHandler(ann_channels_cb, pattern="^sel_|ann_cancel")],
            ANN_ACTION: [CallbackQueryHandler(ann_action_cb, pattern="^act_|ann_cancel")],
            ANN_SCHEDULE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ann_schedule_receive),
                CallbackQueryHandler(ann_schedule_cb, pattern="^sch_|ann_cancel")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_cmd)],
        per_message=False
    )
    application.add_handler(announce_conv)

    logger.info("✅ Hospitality Unit Announcement Bot is live — Covenant University Chapel")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
