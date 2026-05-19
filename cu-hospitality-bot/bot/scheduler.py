import logging
import pytz
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application
from bot.database import get_scheduled_announcements, update_announcement, get_channel_by_id, log_delivery
from bot.config import TIMEZONE

logger = logging.getLogger(__name__)

# Initialize the scheduler
scheduler = AsyncIOScheduler(timezone=pytz.timezone(TIMEZONE))

async def broadcast_announcement(application: Application, announcement_id: int):
    """
    Job that runs to broadcast a scheduled announcement.
    """
    supabase = application.bot_data.get("supabase")
    if not supabase:
        logger.error("Supabase client not found in context.")
        return
        
    from bot.database import get_announcement, deactivate_channel
    from bot.utils.formatters import format_announcement
    
    announcement = await get_announcement(supabase, announcement_id)
    if not announcement or announcement["status"] != "scheduled":
        logger.warning(f"Announcement {announcement_id} not found or not scheduled.")
        return
        
    # Format the message
    text = format_announcement(announcement)
    
    target_channels = announcement["target_channels"]
    success_count = 0
    fail_count = 0
    
    # Do the broadcast
    for channel_id in target_channels:
        channel = await get_channel_by_id(supabase, channel_id)
        if not channel or not channel["is_active"]:
            await log_delivery(supabase, announcement_id, channel_id, None, "failed", "Channel inactive or deleted")
            fail_count += 1
            continue
            
        chat_id = channel["chat_id"]
        try:
            if announcement.get("media_file_id"):
                media_type = announcement["media_type"]
                if media_type == "photo":
                    if len(text) <= 1024:
                        msg = await application.bot.send_photo(chat_id=chat_id, photo=announcement["media_file_id"], caption=text, parse_mode="HTML")
                    else:
                        await application.bot.send_photo(chat_id=chat_id, photo=announcement["media_file_id"])
                        msg = await application.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
                else:
                    msg = await application.bot.send_document(chat_id=chat_id, document=announcement["media_file_id"], caption=text, parse_mode="HTML")
            else:
                msg = await application.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
                
            if announcement["priority"] == "urgent":
                try:
                    await application.bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id)
                except Exception as pin_e:
                    logger.warning(f"Could not pin message in {chat_id}: {pin_e}")
                    
            await log_delivery(supabase, announcement_id, channel_id, msg.message_id, "delivered")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send to channel {chat_id}: {e}")
            error_msg = str(e)
            if "Forbidden" in error_msg:
                await deactivate_channel(supabase, channel_id)
            await log_delivery(supabase, announcement_id, channel_id, None, "failed", error_msg)
            fail_count += 1

    # Update announcement status
    await update_announcement(supabase, announcement_id, status="sent", sent_at=datetime.now(timezone.utc).isoformat())
    
    # Notify creator
    creator_id = announcement["created_by"]
    report = (
        f"📤 <b>Scheduled Broadcast Complete</b>\n\n"
        f"✅ Delivered: {success_count} channels\n"
        f"❌ Failed: {fail_count}\n\n"
        f"📌 Title: {announcement['title']}"
    )
    try:
        await application.bot.send_message(chat_id=creator_id, text=report, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Could not notify creator {creator_id}: {e}")

async def restore_scheduled_jobs(application: Application):
    """
    Load all 'scheduled' announcements from Supabase and re-register them.
    """
    supabase = application.bot_data.get("supabase")
    if not supabase:
        return
        
    announcements = await get_scheduled_announcements(supabase)
    count = 0
    for ann in announcements:
        try:
            # Scheduled_for comes as ISO string
            dt = datetime.fromisoformat(ann["scheduled_for"])
            scheduler.add_job(
                broadcast_announcement,
                trigger="date",
                run_date=dt,
                args=[application, ann["id"]],
                id=str(ann["id"]),
                replace_existing=True
            )
            count += 1
        except Exception as e:
            logger.error(f"Failed to schedule job {ann['id']}: {e}")
            
    logger.info(f"Restored {count} scheduled announcements.")

def start_scheduler():
    scheduler.start()
