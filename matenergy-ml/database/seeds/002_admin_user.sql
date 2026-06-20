-- MatEnergy-ML — Seed: Default Admin User
--
-- IMPORTANT: This seed creates a placeholder admin account.
-- The password hash below is for 'ChangeMe2024!' (Argon2id).
-- CHANGE THE PASSWORD IMMEDIATELY after first login via:
--   PUT /api/v1/users/{id}  with a new strong password hash.
--
-- To generate a new hash:
--   python -c "from argon2 import PasswordHasher; print(PasswordHasher().hash('YourNewPassword'))"
--
-- Safe to run multiple times: ON CONFLICT DO NOTHING prevents duplicates.

DO $$
DECLARE
  admin_user_id  UUID := gen_random_uuid();
  admin_role_id  UUID;
  user_role_id   UUID := gen_random_uuid();
BEGIN
  -- Only insert if no admin user exists yet
  IF NOT EXISTS (SELECT 1 FROM users WHERE is_superuser = TRUE) THEN

    INSERT INTO users (
      id, email, username, hashed_password,
      is_active, is_superuser, failed_login_attempts, created_at
    ) VALUES (
      admin_user_id,
      'admin@matenergy.local',
      'admin',
      -- Argon2id hash of 'ChangeMe2024!' — REPLACE BEFORE PRODUCTION
      '$argon2id$v=19$m=65536,t=3,p=4$PLACEHOLDER_REPLACE_WITH_REAL_HASH$PLACEHOLDER',
      TRUE,
      TRUE,
      0,
      NOW()
    )
    ON CONFLICT (email) DO NOTHING;

    -- Assign admin role
    SELECT id INTO admin_role_id FROM roles WHERE name = 'admin' LIMIT 1;

    IF admin_role_id IS NOT NULL THEN
      INSERT INTO user_roles (id, user_id, role_id, assigned_at)
      VALUES (user_role_id, admin_user_id, admin_role_id, NOW())
      ON CONFLICT DO NOTHING;
    END IF;

  END IF;
END $$;

-- Note: The scripts/seed_db.py script provides a safer way to create
-- the admin user with a properly hashed password via Python/Argon2.
-- Use that script in development and CI environments.
