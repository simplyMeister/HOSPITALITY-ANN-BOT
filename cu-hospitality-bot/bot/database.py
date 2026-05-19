import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
from supabase._async.client import AsyncClient, create_client
from bot.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

logger = logging.getLogger(__name__)

async def get_supabase() -> AsyncClient:
    return await create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# --- Users ---
async def get_user(supabase: AsyncClient, user_id: int) -> Optional[Dict]:
    try:
        res = await supabase.table("users").select("*").eq("user_id", user_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error in get_user: {e}")
        return None

async def upsert_user(supabase: AsyncClient, user_id: int, username: Optional[str], full_name: str) -> Optional[Dict]:
    try:
        existing = await get_user(supabase, user_id)
        if existing:
            # Update only username and full_name, NEVER downgrade role
            res = await supabase.table("users").update({
                "username": username,
                "full_name": full_name
            }).eq("user_id", user_id).execute()
            return res.data[0] if res.data else None
        else:
            res = await supabase.table("users").insert({
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "role": "viewer"
            }).execute()
            return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error in upsert_user: {e}")
        return None

async def update_user_role(supabase: AsyncClient, user_id: int, role: str) -> Optional[Dict]:
    try:
        res = await supabase.table("users").update({"role": role}).eq("user_id", user_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error in update_user_role: {e}")
        return None

# --- Channels ---
async def get_all_active_channels(supabase: AsyncClient) -> List[Dict]:
    try:
        res = await supabase.table("channels").select("*").eq("is_active", True).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error in get_all_active_channels: {e}")
        return []

async def get_channel_by_id(supabase: AsyncClient, channel_id: int) -> Optional[Dict]:
    try:
        res = await supabase.table("channels").select("*").eq("id", channel_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error in get_channel_by_id: {e}")
        return None

async def insert_channel(supabase: AsyncClient, chat_id: int, name: str, type_: str, label: Optional[str], added_by: int) -> Optional[Dict]:
    try:
        res = await supabase.table("channels").insert({
            "chat_id": chat_id,
            "name": name,
            "type": type_,
            "label": label,
            "added_by": added_by
        }).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error in insert_channel: {e}")
        return None

async def update_channel(supabase: AsyncClient, channel_id: int, **fields) -> Optional[Dict]:
    try:
        res = await supabase.table("channels").update(fields).eq("id", channel_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error in update_channel: {e}")
        return None

async def deactivate_channel(supabase: AsyncClient, channel_id: int) -> None:
    try:
        await supabase.table("channels").update({"is_active": False}).eq("id", channel_id).execute()
    except Exception as e:
        logger.error(f"Error in deactivate_channel: {e}")

# --- Announcements ---
async def insert_announcement(supabase: AsyncClient, **fields) -> Optional[Dict]:
    try:
        res = await supabase.table("announcements").insert(fields).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error in insert_announcement: {e}")
        return None

async def get_announcement(supabase: AsyncClient, announcement_id: int) -> Optional[Dict]:
    try:
        res = await supabase.table("announcements").select("*").eq("id", announcement_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error in get_announcement: {e}")
        return None

async def update_announcement(supabase: AsyncClient, announcement_id: int, **fields) -> Optional[Dict]:
    try:
        res = await supabase.table("announcements").update(fields).eq("id", announcement_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error in update_announcement: {e}")
        return None

async def get_drafts_by_user(supabase: AsyncClient, user_id: int) -> List[Dict]:
    try:
        res = await supabase.table("announcements").select("*").eq("status", "draft").eq("created_by", user_id).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error in get_drafts_by_user: {e}")
        return []

async def get_all_drafts(supabase: AsyncClient) -> List[Dict]:
    try:
        res = await supabase.table("announcements").select("*").eq("status", "draft").execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error in get_all_drafts: {e}")
        return []

async def get_scheduled_announcements(supabase: AsyncClient) -> List[Dict]:
    try:
        now = datetime.now(timezone.utc).isoformat()
        res = await supabase.table("announcements") \
            .select("*") \
            .eq("status", "scheduled") \
            .gt("scheduled_for", now) \
            .execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error in get_scheduled_announcements: {e}")
        return []

# --- Delivery Log ---
async def log_delivery(supabase: AsyncClient, announcement_id: int, channel_id: int, message_id: Optional[int], status: str, error_msg: Optional[str] = None):
    try:
        await supabase.table("delivery_log").insert({
            "announcement_id": announcement_id,
            "channel_id": channel_id,
            "message_id": message_id,
            "status": status,
            "error_msg": error_msg
        }).execute()
    except Exception as e:
        logger.error(f"Error in log_delivery: {e}")

# --- Templates ---
async def get_all_templates(supabase: AsyncClient) -> List[Dict]:
    try:
        res = await supabase.table("templates").select("*").execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error in get_all_templates: {e}")
        return []

async def get_template_by_id(supabase: AsyncClient, template_id: int) -> Optional[Dict]:
    try:
        res = await supabase.table("templates").select("*").eq("id", template_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error in get_template_by_id: {e}")
        return None

async def insert_template(supabase: AsyncClient, **fields) -> Optional[Dict]:
    try:
        res = await supabase.table("templates").insert(fields).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error in insert_template: {e}")
        return None

async def update_template(supabase: AsyncClient, template_id: int, **fields) -> Optional[Dict]:
    try:
        res = await supabase.table("templates").update(fields).eq("id", template_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error in update_template: {e}")
        return None

async def delete_template(supabase: AsyncClient, template_id: int) -> None:
    try:
        await supabase.table("templates").delete().eq("id", template_id).execute()
    except Exception as e:
        logger.error(f"Error in delete_template: {e}")

async def count_templates(supabase: AsyncClient) -> int:
    try:
        res = await supabase.table("templates").select("id", count="exact").execute()
        return res.count if res.count is not None else 0
    except Exception as e:
        logger.error(f"Error in count_templates: {e}")
        return 0

async def seed_templates(supabase: AsyncClient, templates: List[Dict]) -> None:
    try:
        for t in templates:
            await supabase.table("templates").insert(t).execute()
    except Exception as e:
        logger.error(f"Error in seed_templates: {e}")
