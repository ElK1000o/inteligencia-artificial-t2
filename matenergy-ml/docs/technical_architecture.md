# Technical Architecture — MatEnergy-ML

## 1. Architectural Philosophy

MatEnergy-ML is built around a **layered clean architecture** (sometimes called ports-and-adapters or hexagonal architecture). The core invariant is that dependencies always point inward: the domain layer has zero dependencies on infrastructure, the application layer depends only on the domain, and the infrastructure and presentation layers depend on the layers above them. This separation enables unit testing of domain logic without a database, swapping ML backends without touching business rules, and replacing the HTTP framework without rewriting the application layer.

The architecture deliberately avoids generic CRUD scaffolding. Each boundary crossing is explicit: routers call application services, application services call domain services and repository interfaces, repositories call SQLAlchemy, and ML trainers call scikit-learn pipelines. This verbosity is intentional — it makes the scientific workflow traceable at every step.

---

## 2. Layered Architecture

### 2.1 Presentation Layer (`app/api/v1/`)

FastAPI routers receive HTTP requests and delegate immediately to application services. Routers are responsible for:
- Deserialising request bodies via Pydantic v2 schemas (strict mode, no extra fields)
- Injecting authenticated user context via FastAPI `Depends`
- Enforcing RBAC through permission dependencies (`require_permission_dep`)
- Serialising responses to Pydantic response models
- Handling HTTP-level errors (4xx/5xx mapping from domain exceptions)

Routers hold no business logic. The maximum complexity permitted in a router function is: validate input → call service → return response model.

### 2.2 Application Layer (`app/application/`)

Use-case services orchestrate multi-step operations that span domain entities and infrastructure. Examples:
- `DatasetUploadService`: parse CSV, validate schema, call material repository, trigger descriptor pipeline, persist descriptor set
- `ModelTrainingService`: load feature matrix from descriptor repository, call `ModelTrainer`, compute evaluation metrics, persist artifact metadata
- `CandidateRankingService`: load predictions, call `CandidateScoringService`, persist ranking

Application services depend on repository interfaces (defined in the domain) rather than concrete implementations. This allows injecting mock repositories in tests.

### 2.3 Domain Layer (`app/domain/`)

The domain contains:
- **Entities** (`app/domain/entities/`): Python dataclasses representing domain objects — `Material`, `Dataset`, `Descriptor`, `ModelVersion`, `Prediction`, `CandidateRanking`, `User`. Entities carry only identity and domain logic; they have no ORM dependencies.
- **Domain services** (`app/domain/services/`): pure functions or stateless classes implementing scientific logic — `StabilityClassificationService` (applies the eV/atom threshold), `CandidateScoringService` (weighted multi-objective scoring), `MaterialValidationService` (physical plausibility checks), `DescriptorDefinitionService` (descriptor metadata registry).

Domain services never import SQLAlchemy, scikit-learn, or FastAPI.

### 2.4 Infrastructure Layer (`app/infrastructure/`)

Infrastructure implements the interfaces defined in the domain and application layers:

- **`infrastructure/database/`**: SQLAlchemy 2.x mapped classes (`models/`), generic and entity-specific repositories (`repositories/`), session factory (`session.py`).
- **`infrastructure/ml/`**: `ModelTrainer`, `RegressionEvaluator`, `ClassificationEvaluator`, `Predictor`, `build_sklearn_pipeline`, `prepare_train_test`.
- **`infrastructure/descriptors/`**: `CompositionalDescriptorPipeline`, `StructuralDescriptorPipeline`, `DescriptorPipeline` (orchestrator).
- **`infrastructure/materials/`**: `CSVLoader` — parses and validates material CSV uploads.
- **`infrastructure/security/`**: password hashing helpers, JWT utilities.
- **`infrastructure/external/`**: HTTP clients for Materials Project, JARVIS, and NOMAD APIs.
- **`infrastructure/reports/`**: report generation utilities.
- **`infrastructure/simulation/`**: atomistic simulation adapters and result ingestion (Etapa 13). `LocalSimulationAdapter` runs ASE/EMT calculations in daemon threads for supported metallic elements and falls back to a deterministic hash-seeded approximation for other formulas. `SlurmAdapter` generates real VASP input files (POSCAR, INCAR, KPOINTS via pymatgen) and a SLURM batch script without submitting to HPC — the script is returned via the `/inputs` endpoint for manual sbatch. `DFTResultIngester` reads completed job results from the `background_jobs` table and persists them as `MaterialProperty` rows. The abstract `DFTJobQueueInterface` defines the port; adapters implement it without depending on FastAPI or SQLAlchemy session objects directly (threads acquire their own `SessionLocal` session via a `_get_session()` factory).

---

## 3. Backend: FastAPI + Pydantic v2 + SQLAlchemy 2.x

**FastAPI** (0.115+) provides automatic OpenAPI schema generation, dependency injection, and async request handling. All route handlers are type-annotated; FastAPI uses those annotations to drive Pydantic validation and OpenAPI documentation simultaneously.

**Pydantic v2** (2.9+) enforces strict input validation on all request bodies and response models. `pydantic-settings` loads the application configuration from environment variables at startup, failing fast with a `ValidationError` if any required variable is absent.

**SQLAlchemy 2.x** is used in the ORM mapped-class style (not the legacy `declarative_base` + `Column` style). All models use `Mapped[T]` annotations and `mapped_column()`, enabling full type-checker support. The session factory uses `psycopg2` synchronously; an async upgrade path to `asyncpg` is identified as a future scalability improvement.

**Alembic** manages schema migrations. The `alembic/env.py` imports all SQLAlchemy models to enable autogenerate. Migrations are linear (no branches); every migration must be reversible for safe rollback.

**PyJWT + argon2-cffi**: JWT tokens use RS256 or HS256 (configurable). Passwords are hashed with Argon2id (memory-hard function). Raw passwords never leave the `PasswordHasher` class.

---

## 4. Database: PostgreSQL 16

### Schema Overview

The schema is divided into eight logical groups:
1. **Auth**: `users`, `roles`, `user_roles`, `refresh_tokens`, `password_reset_tokens`
2. **Datasets**: `datasets` (provenance, upload metadata)
3. **Materials**: `materials`, `material_compositions`, `material_properties`, `material_structures`
4. **Descriptors**: `descriptor_sets`, `material_descriptors`
5. **ML**: `model_versions`, `model_artifacts`, `model_training_runs`, `model_metrics`, `model_parameters`
6. **Rankings**: `candidate_rankings`, `ranking_items`
7. **Audit**: `audit_logs`, `security_events`, `system_settings`, `api_usage_logs`
8. **Background Jobs**: `background_jobs` — tracks async DFT job execution (status, progress, result JSONB, error)

### Indexing Strategy

Every foreign key column has an explicit index. Additional indexes target:
- `materials.formula`, `materials.reduced_formula`, `materials.chemsys` — for formula-based lookups
- `material_properties.(material_id, property_name)` — for per-material property retrieval
- `model_versions.(model_type, target_property, is_active)` — for active model discovery
- `audit_logs.(user_id, created_at)` and `(resource_type, resource_id)` — for audit queries
- `refresh_tokens.jti` — unique index for token revocation lookups

### JSONB Usage

JSONB columns store semi-structured data where a fixed schema would be overly rigid:
- `materials.elements`: list of element symbols for a material
- `material_structures.structure_json`: full pymatgen-compatible structure serialisation
- `model_training_runs.hyperparameters`: arbitrary key-value hyperparameter sets
- `model_artifacts.library_versions`: scikit-learn/numpy version snapshot at training time
- `audit_logs.metadata_`: additional context for audit events
- `system_settings.value`: key-value configuration store

JSONB GIN indexes are added where query patterns require JSON field searches (e.g., on `material_structures.structure_json` for spacegroup queries in future extensions).

---

## 5. ML Pipeline

### Training Flow

```
User triggers POST /models/train
    → ModelTrainingService.run()
        → DescriptorRepository.get_feature_matrix(dataset_id, descriptor_set_id)
        → preprocessing.check_for_leakage(feature_names, target)
        → preprocessing.prepare_train_test(X, y, test_size=0.2, seed=42)
        → ModelTrainer.train(model_type, task_type, X_train, y_train)
            → build_sklearn_pipeline() → [SimpleImputer → RobustScaler]
            → Pipeline([preprocessor, estimator]).fit(X_train, y_train)
        → ModelTrainer.save_artifact(pipeline) → UUID filename + SHA-256
        → Evaluator.evaluate(pipeline, X_train, X_test, y_train, y_test)
        → ModelRepository.persist(model_version, artifact, metrics)
```

### Artifact Management

Artifacts are stored as `artifacts/models/<model_name>_<uuid4>.joblib` with `joblib.dump(..., compress=3)`. The SHA-256 hash is computed at save time and stored in `model_artifacts.sha256_hash`. At load time, `ModelTrainer.load_artifact()` re-computes and compares the hash before deserialisation. A hash mismatch raises `ArtifactIntegrityError` and prevents model use. Artifacts are write-once; retraining always generates a new UUID filename.

### Model Registry

`model_versions.is_active` is a single boolean flag per (model_type, target_property) pair that marks the production-ready version. Only one model per (type, property) combination should be active at a time; the application layer enforces this via a transaction that deactivates the previous active version before activating the new one.

---

## 6. Descriptor Pipeline

### Compositional Descriptors (`CompositionalDescriptorPipeline`)

Parses chemical formulas via pymatgen `Composition` and computes, for each of the six elemental properties (atomic number, atomic mass, electronegativity, atomic radius, ionization energy, electron affinity):
- Fraction-weighted average: `avg_P = Σ_i (x_i * P_i) / Σ_i x_i`
- Maximum, minimum, range, and standard deviation across constituent elements

Additional compositional features: element-specific fractions for battery-relevant elements (Li, Cu, O, S, P, Fe, Mn, Co, Ni), transition-metal fraction, stoichiometric L-norms (L2, L3, L5, L7, L10), and valence electron statistics. The pipeline generates 50+ features per formula.

### Structural Descriptors (`StructuralDescriptorPipeline`)

Extracts lattice parameters (a, b, c, α, β, γ), volume, density, space group number, and crystal system from stored `material_structures.structure_json`. These descriptors are available only when structural information is provided (typically for Materials Project entries with known crystal structure).

### Descriptor Pipeline Orchestrator

`DescriptorPipeline` runs compositional descriptors unconditionally and structural descriptors conditionally. The output is merged into a flat feature dictionary, validated for NaN/Inf values (replaced with 0.0), and persisted as a `material_descriptors` row per material per descriptor set.

---

## 7. Frontend: React SPA

The frontend is a TypeScript React 18 SPA built with Vite 6. Key architectural decisions:

- **Routing**: React Router v6 with protected route wrappers that check the auth context
- **State management**: React Context for auth state; component-local state for forms; no Redux
- **API client**: Axios instance with interceptors that inject the `Authorization: Bearer <token>` header from localStorage and handle 401 responses by triggering token refresh
- **Token refresh**: Axios response interceptor catches 401, calls `POST /auth/refresh` with the refresh token from an `httpOnly`-like secure storage pattern, retries the original request
- **Forms**: react-hook-form with Zod validation schemas
- **Charts**: Recharts for metric visualisations and descriptor distribution plots
- **Styling**: Tailwind CSS 3.4 with utility-first approach

The frontend is served by Nginx in production (see `frontend/nginx.conf.template`), which also handles SPA fallback routing (`try_files $uri $uri/ /index.html`). The config is an envsubst template (processed by the base nginx image's entrypoint at container start) so `PORT`, `BACKEND_HOST`, and `BACKEND_PORT` can be overridden per deployment target without rebuilding the image — see `docs/deployment_guide.md` for the Railway deployment case, where `BACKEND_HOST` is set to the backend service's private network hostname instead of the docker-compose service name `backend`.

---

## 8. Security Architecture

### JWT Rotation

Access tokens have a 15-minute lifetime. Refresh tokens have a 7-day lifetime and are stored in the `refresh_tokens` table with a unique JTI (JWT ID) claim. On refresh, the old JTI is revoked (marked `is_revoked = true`) and a new token pair is issued. Replay of a revoked refresh token triggers a security event (`SecurityEvent.event_type = "token_reuse"`) and invalidates all tokens for that user.

### RBAC

Three roles: `ADMIN`, `RESEARCHER`, `VIEWER`. The permission matrix in `app/core/permissions.py` maps each role to a set of `resource:action` strings. FastAPI `Depends` factories (`require_permission_dep`, `require_roles`) check the authenticated user's roles against the required permission before executing any route.

### Audit Logging

Every mutating operation (dataset upload, model training, prediction, ranking) writes an `AuditLog` row containing: `user_id`, `action`, `resource_type`, `resource_id`, `ip_address`, `user_agent`, `request_method`, `request_path`, `status_code`, `duration_ms`, and a JSONB `metadata_` field for additional context. Security events (login failures, brute-force lockouts, token reuse) are recorded separately in `security_events`.

---

## 9. Data Flow Diagram (ASCII)

```
  Browser (React SPA)
       |
       | HTTPS / JSON
       v
  +--------------------+
  |  FastAPI Router    |  (Pydantic validation, JWT auth, RBAC)
  +--------------------+
       |
       | Python function call
       v
  +--------------------+
  | Application Service|  (orchestration, no I/O logic)
  +--------------------+
       |           |
       v           v
  +---------+  +------------------+
  | Domain  |  | Infrastructure   |
  | Service |  |  - Repositories  |
  | (pure)  |  |  - ML trainers   |
  +---------+  |  - Descriptors   |
               |  - External APIs |
               |  - Simulation    |  ← Etapa 13
               +------------------+
                    |        |          |
                    v        v          v
              PostgreSQL   Artifact   Daemon
                 (16)      Storage    Thread
               (background  (.joblib)  (ASE/EMT
                _jobs table)           or approx.)
```

---

## 10. Key Design Decisions and Trade-offs

| Decision | Rationale | Trade-off |
|---|---|---|
| Clean architecture | Testable domain logic, swappable infrastructure | More boilerplate than a simple CRUD scaffold |
| Synchronous SQLAlchemy (psycopg2) | Simpler code, sufficient for research workloads | Cannot handle high concurrency; async upgrade needed for production scale |
| scikit-learn over deep learning frameworks | Interpretable, fast to train, sufficient for compositional features | Cannot exploit raw crystal structure information as well as GNNs |
| Joblib + SHA-256 integrity | Simple, no MLflow dependency | No experiment tracking UI; metrics stored in DB instead |
| JSONB for hyperparameters | Schema-flexible; avoids migrations for new model types | Slightly harder to query than normalised columns |
| Argon2id passwords | Memory-hard; resistant to GPU cracking | Slightly higher login latency (~100 ms) |
| Short JWT access tokens (15 min) | Limits credential exposure window | Requires frequent refresh calls |

---

## 11. Scalability Considerations

The current architecture is designed for single-node research deployments handling tens of thousands of materials. Identified upgrade paths for larger scale:

- **Async database**: Replace `psycopg2` with `asyncpg` + `SQLAlchemy[asyncio]` for non-blocking I/O
- **Background task queue**: Move ML training to Celery + Redis or ARQ to avoid blocking HTTP workers
- **Table partitioning**: Partition `predictions` and `audit_logs` by `created_at` (monthly ranges) once row counts exceed ~10M
- **Model serving**: Replace inline `pipeline.predict()` calls with a dedicated model-serving microservice (e.g., BentoML or TorchServe) for GPU-accelerated inference
- **Graph neural networks**: Future integration of PyTorch Geometric for structure-based models requires a separate training infrastructure path
- **Horizontal scaling**: The stateless backend can be scaled behind a load balancer; the only shared state is PostgreSQL and the artifact storage volume (which can be migrated to S3-compatible object storage)
