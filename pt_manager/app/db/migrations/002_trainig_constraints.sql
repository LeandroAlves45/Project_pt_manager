-- =========================
-- Training / Plans
-- =========================

-- Evita duplicar exercícios por nome (catálogo)
CREATE UNIQUE INDEX IF NOT EXISTS uq_exercises_name
ON exercises(name);

-- Garante que não duplicamos a mesma série para o mesmo exercício do dia
CREATE UNIQUE INDEX IF NOT EXISTS uq_plan_set_loads_parent_set
ON plan_exercise_set_loads(plan_day_exercise_id, set_number);

-- 1 plano ativo por cliente (active_to IS NULL)
-- SQLite suporta índices parciais (WHERE ...)
CREATE UNIQUE INDEX IF NOT EXISTS uq_client_active_plan_one_open
ON client_active_plans(client_id)
WHERE active_to IS NULL;
