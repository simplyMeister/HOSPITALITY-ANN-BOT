-- ============================================================
-- CU CHAPEL HOSPITALITY UNIT — ANNOUNCEMENT BOT SCHEMA
-- Run this in your Supabase project SQL Editor (once, on setup)
-- ============================================================

-- Users (role assignment only — not a member directory)
CREATE TABLE IF NOT EXISTS users (
    user_id     BIGINT PRIMARY KEY,
    username    TEXT,
    full_name   TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'viewer',
    -- 'unit_head' | 'executive' | 'announcer' | 'viewer'
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Registered broadcast targets
CREATE TABLE IF NOT EXISTS channels (
    id          BIGSERIAL PRIMARY KEY,
    chat_id     BIGINT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,       -- 'group' | 'channel' | 'supergroup'
    label       TEXT,                -- e.g. 'All Members', 'Executives', 'Group A'
    is_active   BOOLEAN DEFAULT TRUE,
    added_by    BIGINT REFERENCES users(user_id),
    added_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Announcements
CREATE TABLE IF NOT EXISTS announcements (
    id              BIGSERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    category        TEXT NOT NULL,
    -- 'general' | 'urgent' | 'meeting' | 'service_duty'
    -- | 'dress_code' | 'event' | 'devotional' | 'welfare'
    priority        TEXT NOT NULL DEFAULT 'normal',
    -- 'normal' | 'high' | 'urgent'
    media_type      TEXT,            -- 'photo' | 'document' | NULL
    media_file_id   TEXT,
    target_channels BIGINT[] NOT NULL,  -- PostgreSQL array of channel row IDs
    created_by      BIGINT NOT NULL REFERENCES users(user_id),
    status          TEXT NOT NULL DEFAULT 'draft',
    -- 'draft' | 'sent' | 'scheduled' | 'cancelled'
    sent_at         TIMESTAMPTZ,
    scheduled_for   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Per-channel delivery receipts
CREATE TABLE IF NOT EXISTS delivery_log (
    id              BIGSERIAL PRIMARY KEY,
    announcement_id BIGINT NOT NULL REFERENCES announcements(id),
    channel_id      BIGINT NOT NULL REFERENCES channels(id),
    message_id      BIGINT,
    status          TEXT NOT NULL,   -- 'delivered' | 'failed'
    error_msg       TEXT,
    delivered_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Message templates
CREATE TABLE IF NOT EXISTS templates (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    category    TEXT,
    body        TEXT NOT NULL,
    -- Supports {date}, {time}, {unit_name}, {chapel_name} placeholders
    created_by  BIGINT REFERENCES users(user_id),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_announcements_status     ON announcements(status);
CREATE INDEX IF NOT EXISTS idx_announcements_scheduled  ON announcements(scheduled_for) WHERE status = 'scheduled';
CREATE INDEX IF NOT EXISTS idx_delivery_announcement    ON delivery_log(announcement_id);
CREATE INDEX IF NOT EXISTS idx_channels_active          ON channels(is_active);

-- ============================================================
-- DISABLE RLS (bot uses service role key — RLS not needed)
-- ============================================================
ALTER TABLE users          DISABLE ROW LEVEL SECURITY;
ALTER TABLE channels       DISABLE ROW LEVEL SECURITY;
ALTER TABLE announcements  DISABLE ROW LEVEL SECURITY;
ALTER TABLE delivery_log   DISABLE ROW LEVEL SECURITY;
ALTER TABLE templates      DISABLE ROW LEVEL SECURITY;
