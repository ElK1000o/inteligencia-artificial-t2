-- MatEnergy-ML — Seed: Roles
-- Executed automatically by PostgreSQL on first container start
-- (placed in /docker-entrypoint-initdb.d via docker-compose volume mount)
--
-- Safe to run multiple times: ON CONFLICT DO NOTHING prevents duplicates.

INSERT INTO roles (id, name, description, created_at)
VALUES
  (gen_random_uuid(), 'admin',      'Full platform access: user management, all data, all models', NOW()),
  (gen_random_uuid(), 'researcher', 'Can upload datasets, train models, run predictions and rankings', NOW()),
  (gen_random_uuid(), 'viewer',     'Read-only access to materials, models, and rankings', NOW())
ON CONFLICT (name) DO NOTHING;
