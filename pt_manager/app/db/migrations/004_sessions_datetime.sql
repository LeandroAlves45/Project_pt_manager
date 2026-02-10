
-- Data: 2026-02-09

-- IMPORTANTE: Esta migration converte a coluna starts_at de DATE para DATETIME
-- Os dados existentes serão convertidos para DATETIME às 00:00:00


-- Verificação: Contar registros
-- SELECT COUNT(*) FROM sessions;
-- SELECT COUNT(*) FROM pack_consumptions;

ALTER TABLE sessions 
    ALTER COLUMN starts_at TYPE TIMESTAMP USING starts_at::timestamp,
    ALTER COLUMN created_at TYPE TIMESTAMP USING created_at::timestamp,
    ALTER COLUMN updated_at TYPE TIMESTAMP USING updated_at::timestamp;

ALTER TABLE pack_consumptions
    ALTER COLUMN created_at TYPE TIMESTAMP USING created_at::timestamp;
