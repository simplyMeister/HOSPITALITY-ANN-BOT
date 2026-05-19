def format_announcement(announcement: dict, sender_name: str = "Unit Leader") -> str:
    """
    Returns the announcement body exactly as the announcer typed it.
    No auto-headers, badges, dividers, or footers — the leader structures it themselves.
    """
    return announcement.get("body", "")
