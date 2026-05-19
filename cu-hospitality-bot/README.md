# Covenant University Chapel — Hospitality Unit Announcement Bot

This Telegram bot allows authorized unit leaders of the Hospitality Unit at Covenant University Chapel to compose, format, and broadcast announcements to registered Telegram groups/channels.

## Setup & Deployment

### 1. Supabase Setup
1. Create a new project on [Supabase](https://supabase.com).
2. Open the SQL Editor in your Supabase dashboard.
3. Run the complete contents of `supabase/schema.sql`.
4. Go to **Project Settings** > **API**.
5. Copy the **Project URL** and the **`service_role` secret key**.

### 2. Telegram Bot Setup
1. Chat with [@BotFather](https://t.me/BotFather) on Telegram.
2. Use `/newbot` to create a new bot.
3. Copy the HTTP API token.
4. **Make sure to add the bot as an Admin in any group/channel you want to register.**

### 3. Environment Variables
Copy `.env.example` to `.env` and fill in the required values:

```env
BOT_TOKEN=your_telegram_bot_token_here
UNIT_HEAD_IDS=123456789,987654321 # Bootstrap unit heads via Telegram User IDs

# Supabase
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_secret_key_here

# Bot identity
UNIT_NAME=Hospitality Unit
CHAPEL_NAME=Covenant University Chapel
TIMEZONE=Africa/Lagos
LOG_LEVEL=INFO
```
*(Note: Ensure you use the `service_role` key, not the `anon` key, as the bot requires write access to ignore RLS).*

### 4. Running the Bot (Docker)
Ensure Docker and Docker Compose are installed.
```bash
docker-compose up -d --build
```

## Roles & Permissions

| Role | Permissions |
| --- | --- |
| `unit_head` | Everything. Manage channels and roles. |
| `executive` | Create, send, and schedule announcements. Manage templates. |
| `announcer` | Create and send announcements. Use templates. |
| `viewer` | Only `/start` and `/help`. |

**Note**: To grant the initial `unit_head` role, add your Telegram User ID to the `UNIT_HEAD_IDS` comma-separated list in `.env`.

## Available Commands

*   `/start` - Register your profile and view the main menu.
*   `/help` - View available commands.
*   `/cancel` - Cancel any ongoing operation.
*   `/announce` - (Announcer+) Compose and send a new announcement.
*   `/drafts` - (Announcer+) View and manage saved drafts.
*   `/schedule` - (Announcer+) View and manage scheduled announcements.
*   `/templates` - (Announcer+) Manage announcement templates.
*   `/channels` - (Executive+) Manage target groups/channels.
*   `/promote` - (Unit Head) Promote a user to a new role.

## Timezone Note
All times generated and expected by the bot are in West Africa Time (`WAT` / `Africa/Lagos`).
