# Database Design — MatEnergy-ML

## 1. Entity-Relationship Overview

The MatEnergy-ML database schema is organised around the scientific workflow: users upload datasets, datasets contain materials, materials receive descriptor representations, descriptors feed ML model training, trained models generate predictions, and predictions are ranked to produce candidate shortlists. A complete audit trail overlays all mutating operations.

The primary relationships are:

```
users ──< user_roles >── roles
users ──< refresh_tokens
datasets ──< materials ──< material_compositions
                        ──< material_properties
                        ──< material_structures
materials ──< material_descriptors >── descriptor_sets
descriptor_sets ──< model_versions ──< model_artifacts
                                    ──< model_training_runs ──< model_metrics
                                                             ──< model_parameters
model_versions ──< prediction_batches ──< predictions
predictions >── candidate_rankings ──< ranking_items
users ──< audit_logs
users ──< security_events
```

All primary keys are UUIDs (`uuid4`). All foreign keys cascade appropriately (CASCADE for ownership, SET NULL for soft references). All timestamps use `TIMESTAMPTZ` (timezone-aware) with `server_default=now()`.

---

## 2. Table Groups

### 2.1 Authentication and Authorization Group

**`users`** — Core identity table.
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Auto-generated uuid4 |
| `email` | VARCHAR(320) | UNIQUE, NOT NULL, INDEX | RFC 5321 maximum length |
| `username` | VARCHAR(150) | UNIQUE, NOT NULL, INDEX | Display identifier |
| `hashed_password` | TEXT | NOT NULL | Argon2id hash |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Soft disable without delete |
| `is_superuser` | BOOLEAN | NOT NULL, DEFAULT FALSE | Bypass all RBAC checks |
| `failed_login_attempts` | INTEGER | NOT NULL, DEFAULT 0 | Brute-force counter |
| `locked_until` | TIMESTAMPTZ | NULL | Set on lockout; checked at login |
| `created_at` | TIMESTAMPTZ | NOT NULL, server_default | |
| `updated_at` | TIMESTAMPTZ | NULL, onupdate | |

**`roles`** — Named permission sets. Seed values: `admin`, `researcher`, `viewer`.

**`user_roles`** — Many-to-many junction with `(user_id, role_id)` unique constraint. Records `assigned_by` (nullable FK to users) for assignment audit.

**`refresh_tokens`** — One row per active refresh token. Columns: `jti` (JWT ID, unique index), `user_id`, `expires_at`, `is_revoked`, `revoked_at`, `user_agent`, `ip_address`. Token reuse detection compares incoming JTI against `is_revoked`.

**`password_reset_tokens`** — Single-use tokens. `token_hash` stores SHA-256 of the raw token; `used_at` is set on consumption to prevent replay.

### 2.2 Dataset Group

**`datasets`** — Upload provenance record.
Key columns: `id` (UUID PK), `name`, `description`, `source` (enum: csv_local, materials_project, jarvis, etc.), `file_path`, `file_hash` (SHA-256 for upload integrity), `row_count`, `status` (pending/processing/ready/failed), `created_by` (FK to users), `created_at`.

### 2.3 Materials Group

**`materials`** — One row per unique (formula, dataset_id) combination. Unique constraint on `(formula, dataset_id)`. Check constraint `nelements >= 1`. Indexed on `formula`, `reduced_formula`, `chemsys` for lookup performance.

**`material_compositions`** — Normalised atomic fraction table. Unique constraint on `(material_id, element_symbol)`. Check constraint `fraction >= 0 AND fraction <= 1`.

**`material_properties`** — Flexible property storage. A single material may have multiple property rows (e.g., both `energy_above_hull` and `band_gap`). The polymorphic value pattern uses three nullable value columns — `value_float`, `value_str`, `value_bool` — with a check constraint requiring exactly one to be non-null: `value_float IS NOT NULL OR value_str IS NOT NULL OR value_bool IS NOT NULL`. Indexed on `(material_id, property_name)`.

**`material_structures`** — One-to-one with `materials`. Stores lattice parameters (a, b, c, α, β, γ), volume, density, space group, crystal system, and the full pymatgen-compatible structure as JSONB (`structure_json`). Presence of this row indicates structural data is available for descriptor enrichment.

### 2.4 Descriptor Group

**`descriptor_sets`** — A named configuration of descriptor parameters (e.g., which pipeline version, which feature columns). Stores `feature_names` as a JSONB array.

**`material_descriptors`** — One row per (material, descriptor_set). The `features` JSONB column stores the full feature dictionary. This avoids a wide pivot table of 50+ float columns while enabling JSON field indexing via GIN index for future query patterns.

### 2.5 ML Group

**`model_versions`** — Model registry. Key columns: `model_type`, `task_type`, `target_property`, `is_active`, `descriptor_set_id`, `dataset_id`, `version_tag`, `created_by`. Indexed on `(model_type, target_property, is_active)` for fast active-model lookup.

**`model_artifacts`** — One-to-one with `model_versions`. Stores `file_path`, `sha256_hash` (64 hex chars), `file_size_bytes`, `artifact_type` (sklearn_joblib), `python_version`, `library_versions` (JSONB snapshot of scikit-learn, numpy, scipy versions at training time).

**`model_training_runs`** — Execution record. Status: `running | completed | failed`. Records `n_train_samples`, `n_test_samples`, `n_features`, `random_seed`, `hyperparameters` (JSONB), `duration_seconds`, and `error_message` on failure.

**`model_metrics`** — Normalised metric storage. One row per (training_run, split, metric_name). Unique constraint on `(training_run_id, split, metric_name)`. Splits: `train`, `test`, `cv`.

**`model_parameters`** — Serialised hyperparameter snapshot (JSONB per parameter). Redundant with `training_runs.hyperparameters` but enables individual parameter queries.

### 2.6 Rankings Group

**`candidate_rankings`** — A ranking session metadata record. Stores the scoring weights and filter criteria used.

**`ranking_items`** — One row per material per ranking. Stores `composite_score`, `stability_label`, `priority_label`, and individual sub-scores as JSONB.

### 2.7 Audit Group

**`audit_logs`** — Immutable append-only log. Indexed on `(user_id, created_at)` for user activity queries and on `(resource_type, resource_id)` for object history queries.

**`security_events`** — Elevated-severity events (login_failure, brute_force, token_reuse, suspicious_ip). Severity levels: `low | medium | high | critical`. `resolved` boolean for incident tracking.

**`system_settings`** — Key-value store for runtime configuration overrides. Values stored as JSONB.

**`api_usage_logs`** — Per-request performance and usage telemetry. Distinct from `audit_logs` (which tracks who did what); `api_usage_logs` tracks performance metrics.

### 2.8 Background Jobs Group

**`background_jobs`** — Tracks asynchronous DFT simulation jobs. Added in migration 002 (pre-existing schema); the ORM model `BackgroundJob` was added in Etapa 13.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK | Auto-generated uuid4 |
| `job_type` | VARCHAR(100) | NOT NULL | Job category, e.g. `"dft_simulation"` |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT `"pending"` | `pending` / `running` / `completed` / `failed` / `cancelled` |
| `created_by` | UUID | FK → `users.id` SET NULL | Submitting user; SET NULL on user deletion |
| `created_at` | TIMESTAMPTZ | NOT NULL, server_default | Submission timestamp |
| `started_at` | TIMESTAMPTZ | NULL | Set when daemon thread begins work |
| `completed_at` | TIMESTAMPTZ | NULL | Set on terminal status |
| `payload` | JSONB | NULL | Input parameters (formula, calculation_type, adapter, functional, encut, etc.) |
| `result` | JSONB | NULL | Output values (formation_energy_eV_per_atom, total_energy_eV, n_steps, converged, method, etc.) |
| `error_message` | TEXT | NULL | Python exception message on failure |
| `progress_pct` | INTEGER | NULL, CHECK 0–100 | Rough progress; set to 100 on completion |
| `celery_task_id` | VARCHAR(255) | NULL | Reserved for future Celery integration; unused in current daemon-thread implementation |

#### JSONB payload schema (DFT jobs)
```json
{
  "formula": "LiFePO4",
  "calculation_type": "RELAX",
  "adapter": "local",
  "functional": "PBE",
  "encut": 520,
  "kpoints_density": 64,
  "hubbard_u": {},
  "job_name": "LiFePO4 relaxation",
  "structure_source": "materials_project"
}
```

#### JSONB result schema (local adapter, completed)
```json
{
  "formation_energy_eV_per_atom": -2.83,
  "energy_above_hull_eV_per_atom": 0.0,
  "band_gap_eV": null,
  "total_energy_eV": -45.32,
  "n_atoms": 28,
  "n_steps": 12,
  "converged": true,
  "method": "ASE-EMT",
  "note": "EMT calculator — metallic system"
}
```

For the deterministic approximation path, `method` is `"deterministic-approx"` and values are seeded by `md5(formula)`. For the SLURM adapter, `result` holds ingestion metadata after `POST /dft-jobs/{id}/ingest` is called.

#### Threading model
Each job starts one daemon thread (`threading.Thread(daemon=True)`). The thread acquires its own database session via a `_get_session()` factory (separate `SessionLocal()` call per thread) to avoid sharing the request-scoped SQLAlchemy session across threads. A paired `threading.Event` in the module-level `_active` dict enables cancellation: the thread checks the event every 0.5 s during its initial 5 s sleep, then exits early if it is set.

---

## 3. Key Design Decisions

### UUID Primary Keys
All tables use `uuid4` UUIDs as primary keys rather than serial integers. Rationale: UUIDs are safe for distributed generation, do not expose record count information via sequential IDs, and integrate cleanly with Python's `uuid.uuid4()` without a database round-trip.

### TIMESTAMPTZ Everywhere
All timestamp columns use `TIMESTAMPTZ` (timestamp with time zone). PostgreSQL stores the value in UTC and converts on display. This eliminates daylight-saving-time ambiguity in audit records and cross-timezone deployments.

### JSONB for Semi-Structured Data
JSONB is used for data that varies by model type (hyperparameters), by user definition (feature names), by external source (structure serialisations), or where adding columns for each new property would require migrations (material properties could alternatively be a wide table with one column per property, but this would require a migration every time a new DFT property is added).

---

## 4. Indexing Strategy

| Table | Index | Rationale |
|---|---|---|
| `users` | `email`, `username` | Login and username lookup |
| `materials` | `formula`, `reduced_formula`, `chemsys` | Formula-based search |
| `material_properties` | `(material_id, property_name)` | Per-material property retrieval |
| `model_versions` | `(model_type, target_property, is_active)` | Active model discovery |
| `refresh_tokens` | `jti`, `user_id` | Token revocation and user token listing |
| `audit_logs` | `action`, `resource_type`, `(user_id, created_at)`, `(resource_type, resource_id)`, `created_at` | Audit query patterns |
| `predictions` | `batch_id`, `material_id` | Batch retrieval and material prediction history |

---

## 5. Constraint Design

Physical validity is enforced at the database layer as a last line of defence against application-layer bugs:

```sql
-- Atomic fractions must be valid probabilities
CHECK (fraction >= 0 AND fraction <= 1)

-- Materials must have at least one element
CHECK (nelements >= 1)

-- A property row must carry exactly one value type
CHECK (value_float IS NOT NULL
    OR value_str IS NOT NULL
    OR value_bool IS NOT NULL)

-- A prediction row must have either a regression or classification output
CHECK (predicted_value IS NOT NULL OR predicted_class IS NOT NULL)
```

Application-layer validation (Pydantic schemas, `MaterialValidationService`) also enforces domain-specific bounds (e.g., `energy_above_hull` in [-0.5, 10.0] eV/atom) before any database write.

---

## 6. Data Retention Strategy

| Table | Retention Policy |
|---|---|
| `audit_logs` | Retain 2 years minimum; archive to cold storage after 1 year |
| `security_events` | Retain 3 years minimum (security compliance) |
| `api_usage_logs` | Retain 90 days; aggregate daily statistics to a summary table |
| `predictions` | Retain indefinitely; partition by `created_at` when exceeding 10M rows |
| `model_artifacts` (files) | Retain permanently; tag superseded versions as `is_active = false` |
| `refresh_tokens` | Delete expired tokens via a nightly cleanup job |

---

## 7. Backup Strategy

**PostgreSQL native backup**: `pg_dump` (logical) or `pg_basebackup` (physical).

Recommended schedule for a research deployment:
- Full logical dump (`pg_dump --format=custom`) daily, retained 30 days
- WAL archiving enabled for point-in-time recovery (PITR) if the PostgreSQL instance is on a system supporting it
- Artifact storage volume backed up in sync with database backups (both must represent the same snapshot for model loading to succeed)

For the Docker Compose deployment, a backup sidecar service or a cron job on the host can execute:
```bash
docker compose exec db pg_dump -U matenergy -Fc matenergy_db > backup_$(date +%Y%m%d).dump
```

---

## 8. Future Partitioning Plan

When `predictions` or `audit_logs` exceed approximately 10 million rows, declarative range partitioning by `created_at` (monthly or quarterly intervals) should be implemented via Alembic migrations:

```sql
-- Example: convert predictions to a partitioned table
CREATE TABLE predictions_y2025m01 PARTITION OF predictions
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

Partition pruning will allow time-bounded audit queries to avoid full table scans. The Alembic migration should create existing partitions and set up a partition maintenance procedure.

---

## 9. Database Security

**Least-privilege application user**: The application connects with a dedicated `matenergy` user that has `CONNECT`, `SELECT`, `INSERT`, `UPDATE`, `DELETE` on application tables, and `EXECUTE` on specific functions. This user does NOT have `CREATE TABLE`, `DROP`, `TRUNCATE`, or `SUPERUSER` privileges. Schema migrations run under a separate migration user with `CREATE` privileges.

**No direct public access**: The PostgreSQL port (5432) should not be exposed to the public internet in production. In the Docker Compose configuration it is bound to `127.0.0.1:5432` for local access only; in production it should be accessible only within the private network.

**Connection string security**: `DATABASE_URL` is loaded from environment variables and never logged or included in error responses. The `pydantic-settings` `Settings` class marks the password field as `SecretStr` to prevent accidental logging.

**Encrypted connections**: In production, `sslmode=require` should be appended to the connection string and PostgreSQL configured with a valid TLS certificate.
