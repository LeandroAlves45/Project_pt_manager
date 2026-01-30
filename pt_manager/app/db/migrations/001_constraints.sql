-- Idempotência: uma sessão só pode consumir 1 vez
--CREATE UNIQUE INDEX IF NOT EXISTS uq_pack_consumptions_session_id
--ON pack_consumptions (session_id);

--Unicidade: uma sessão só pode consumir um mesmo pack mais de 1 vez
CREATE UNIQUE INDEX IF NOT EXISTS uq_clients_phone
ON clients(phone);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pack_types_name
ON pack_types(name);