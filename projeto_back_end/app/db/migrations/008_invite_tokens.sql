-- =============================================================================
-- Migration 008: Client Invite Tokens
-- =============================================================================
--
-- Idempotent — safe to run multiple times (all statements use IF NOT EXISTS).
-- Runs automatically on container startup via migrate.py.
--
-- Purpose:
--   Adds invite token support to the users table so that trainers can
--   generate a one-time link for a client to set their own password.
--
-- Security design:
--   - The raw token is NEVER stored. Only the SHA-256 hex hash is persisted.
--   - The raw token travels in the invite URL; the hash is what we compare.
--   - This means even with full DB read access an attacker cannot forge a link.
--   - Tokens expire after 7 days and are cleared after first use.
--
-- Flow:
--   1. Trainer calls POST /clients/{id}/generate-invite
--      → backend generates random token, stores SHA-256(token), returns full URL
--   2. Trainer copies URL, sends via WhatsApp/SMS
--   3. Client opens /invite/{raw_token}
--      → frontend calls GET /invite/validate/{token} to get client name (public)
--   4. Client submits new password
--      → frontend calls POST /invite/set-password/{token}
--      → backend: hash token, find user, set password, clear token, auto-login
--   5. Client is redirected to /cliente/dashboard with their JWT
-- =============================================================================
 
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS invite_token_hash    VARCHAR(64),
    ADD COLUMN IF NOT EXISTS invite_token_expires_at TIMESTAMPTZ;
 
-- Index for fast token lookup on the set-password request
-- (every invite page load triggers this lookup)
CREATE INDEX IF NOT EXISTS idx_users_invite_token_hash
    ON users (invite_token_hash)
    WHERE invite_token_hash IS NOT NULL;