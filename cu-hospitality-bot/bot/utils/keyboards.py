from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def build_start_keyboard(role: str) -> InlineKeyboardMarkup:
    """Build the main menu based on user role."""
    buttons = []
    if role in ["unit_head", "executive", "announcer"]:
        buttons.append([InlineKeyboardButton("📢 New Announcement", callback_data="cmd_announce")])
        buttons.append([InlineKeyboardButton("📝 Drafts", callback_data="cmd_drafts"), 
                        InlineKeyboardButton("📅 Scheduled", callback_data="cmd_schedule")])
        buttons.append([InlineKeyboardButton("📑 Templates", callback_data="cmd_templates")])
    if role in ["unit_head", "executive"]:
        buttons.append([InlineKeyboardButton("⚙️ Manage Channels", callback_data="cmd_channels")])
    
    return InlineKeyboardMarkup(buttons)

def build_category_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📋 General", callback_data="cat_general"),
            InlineKeyboardButton("⚠️ Urgent", callback_data="cat_urgent")
        ],
        [
            InlineKeyboardButton("📅 Meeting", callback_data="cat_meeting"),
            InlineKeyboardButton("👔 Dress Code", callback_data="cat_dress_code")
        ],
        [
            InlineKeyboardButton("🗓 Service Duty", callback_data="cat_service_duty"),
            InlineKeyboardButton("🎉 Event", callback_data="cat_event")
        ],
        [
            InlineKeyboardButton("💒 Devotional", callback_data="cat_devotional"),
            InlineKeyboardButton("❤️ Welfare", callback_data="cat_welfare")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="ann_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_priority_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🟡 Normal", callback_data="pri_normal"),
            InlineKeyboardButton("🟠 High", callback_data="pri_high"),
            InlineKeyboardButton("🔴 Urgent", callback_data="pri_urgent")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="ann_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_media_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📸 Add Image / Poster", callback_data="med_photo")],
        [InlineKeyboardButton("⏭️ Skip (Text Only)", callback_data="med_skip")],
        [InlineKeyboardButton("❌ Cancel", callback_data="ann_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_channels_selection_keyboard(channels: list, selected_ids: list) -> InlineKeyboardMarkup:
    keyboard = []
    for ch in channels:
        status = "✅" if ch["id"] in selected_ids else "⬛"
        label = ch["label"] if ch["label"] else ch["name"]
        keyboard.append([InlineKeyboardButton(f"{status} {label}", callback_data=f"sel_chan_{ch['id']}")])
        
    keyboard.append([
        InlineKeyboardButton("✅ Select All", callback_data="sel_all"),
        InlineKeyboardButton("❌ Clear All", callback_data="sel_clear")
    ])
    keyboard.append([InlineKeyboardButton("➡️ Confirm", callback_data="sel_confirm")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="ann_cancel")])
    return InlineKeyboardMarkup(keyboard)

def build_preview_action_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✅ Send Now", callback_data="act_send"),
            InlineKeyboardButton("📅 Schedule Later", callback_data="act_schedule")
        ],
        [
            InlineKeyboardButton("💾 Save Draft", callback_data="act_draft"),
            InlineKeyboardButton("✏️ Edit", callback_data="act_edit"),
            InlineKeyboardButton("❌ Cancel", callback_data="ann_cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_schedule_confirm_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("✅ Confirm Time", callback_data="sch_confirm")],
        [InlineKeyboardButton("✏️ Change Time", callback_data="sch_change")],
        [InlineKeyboardButton("❌ Cancel", callback_data="ann_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_drafts_action_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📤 Send Now", callback_data=f"drf_send_{draft_id}"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"drf_edit_{draft_id}"),
            InlineKeyboardButton("🗑️ Delete", callback_data=f"drf_delete_{draft_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_scheduled_action_keyboard(schedule_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📋 Preview", callback_data=f"schd_prev_{schedule_id}"),
            InlineKeyboardButton("✏️ Reschedule", callback_data=f"schd_resch_{schedule_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"schd_cancel_{schedule_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_templates_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("➕ New Template", callback_data="tpl_new"),
            InlineKeyboardButton("📋 View Templates", callback_data="tpl_view")
        ],
        [
            InlineKeyboardButton("📤 Use Template", callback_data="tpl_use")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_channels_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("➕ Register Channel", callback_data="chn_register"),
            InlineKeyboardButton("📋 List Channels", callback_data="chn_list")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
