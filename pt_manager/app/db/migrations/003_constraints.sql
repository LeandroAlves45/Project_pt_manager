-- Índice para o worker buscar rapidamente pendentes por data
CREATE INDEX IF NOT EXISTS ix_notifications_status_scheduled_for
ON notifications (status, scheduled_for);

-- Idempotência: não criar múltiplas pending para o mesmo (session, canal, destino)
-- Postgres e SQLite suportam partial index (SQLite >= 3.8.0).
CREATE UNIQUE INDEX IF NOT EXISTS uq_notifications_pending_per_session_channel_recipient
ON notifications (session_id, channel, recipient_type)
WHERE status = 'PENDING';
