-- =============================================================================
-- Migration 009: Notification JSONB template data (TD-01)
-- =============================================================================
--
-- Idempotent — safe to run multiple times (all statements use IF NOT EXISTS).
-- Runs automatically on container startup via migrate.py.
--
-- Problem being solved:
--   The message column stores notification data in a pipe-delimited string format:
--     "TEMPLATE_HTML|client_name=João|session_date=15/03/2026|..."
--   This is fragile: any value containing '=', '|' or ';' silently corrupts
--   the key-value parsing in the scheduler.
--
-- Solution:
--   Add a JSONB column (template_data) that stores structured data:
--     {"client_name": "João", "session_date": "15/03/2026", ...}
--   The scheduler checks template_data first. If not null, it uses it.
--   If null (legacy rows), it falls back to the old pipe parsing so that
--   existing pending notifications are not lost.
--
-- No data migration required:
--   Pending notifications using the old format will be processed normally
--   via the fallback path. New notifications created after this migration
--   will use template_data. The message column is kept for the fallback
--   and for plain-text trainer emails (which never used the pipe format).
-- =============================================================================
 
ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS template_data JSONB;
 