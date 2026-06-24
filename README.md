# MatEnergy-ML

**Computational Screening Platform for Energy Storage Materials Using Machine Learning**

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Description

MatEnergy-ML is a full-stack research platform for the computational screening and ranking of inorganic materials relevant to energy storage applications, including lithium-ion batteries, solid-state electrolytes, and cathode/anode candidates. The platform ingests datasets derived from density functional theory (DFT) calculations — primarily sourced from the Materials Project database — computes composition-based and structure-aware feature descriptors, trains supervised machine learning models for both regression and classification tasks, and ranks candidate materials according to multi-objective scoring functions.

The backend is implemented as a layered clean-architecture FastAPI service backed by PostgreSQL 16. All ML pipelines are built on scikit-learn and persisted as integrity-verified joblib artifacts. The platform enforces role-based access control (RBAC), comprehensive audit logging, and out-of-domain detection on every prediction request, reflecting the security and reproducibility requirements of academic computational materials science workflows.

This platform serves as the practical demonstrator for the doctoral thesis *"Computational Design of Energetic Materials for Advanced Storage Technologies Using Artificial Intelligence and Atomistic Simulation."* Its design prioritises reproducibility, scientific traceability, and extensibility toward future integration with atomistic simulation engines.

---

## Key Features

### Materials Science
- Ingestion of DFT-derived property datasets (CSV upload or Materials Project API)
- Composition-based descriptor pipeline: weighted elemental statistics, stoichiometric L-norms, transition-metal fractions, valence electron counts
- Structure-aware descriptor pass-through for pymatgen-serialised structures
- Target properties: `energy_above_hull`, `formation_energy_per_atom`, `band_gap`, `is_stable`
- Physical validity constraints enforced at database and API layers
- Multi-objective candidate ranking with configurable scoring weights

### Machine Learning
- Regression: Ridge, Random Forest, Gradient Boosting, MLP, SVR, Gaussian Process
- Classification: Logistic Regression, Random Forest, Gradient Boosting, MLP
- Reproducible train/test splits with fixed random seed (`FIXED_RANDOM_SEED = 42`)
- 5-fold cross-validation with stratification for classification tasks
- Out-of-domain detection via 3-sigma feature distribution heuristic
- Ensemble uncertainty quantification for tree-based models
- SHA-256 artifact integrity verification on every model load

### Platform
- JWT authentication with short-lived access tokens (15 min) and rotating refresh tokens (7 days)
- RBAC with three roles: `admin`, `researcher`, `viewer`
- Complete audit trail for all mutating operations
- Structured JSON logging via structlog
- Rate limiting via slowapi + Redis
- Interactive API documentation at `/api/v1/docs` (Swagger UI)

---

## Architecture Overview

The system follows a layered clean architecture. The **Presentation Layer** (FastAPI routers + Pydantic v2 schemas) handles HTTP serialisation and input validation. The **Application Layer** (use-case services) orchestrates domain logic without touching infrastructure. The **Domain Layer** contains entities, value objects, and domain service interfaces. The **Infrastructure Layer** implements those interfaces: PostgreSQL via SQLAlchemy 2.x mapped classes, scikit-learn ML pipelines, the descriptor computation engine, and external API clients (Materials Project, JARVIS, NOMAD).

The frontend is a React 18 / TypeScript SPA built with Vite, communicating with the backend exclusively via the versioned REST API. The entire stack is containerised with Docker Compose for reproducible deployment.

---

## Quick Start (one-shot bootstrap)

The fastest way to get a fully working instance — Docker stack, migrations,
seeded admin user, demo dataset, descriptors, 6 trained baseline models,
active models, and a candidate ranking — is the bootstrap script:

```bash
git clone <repo-url>
cd inteligencia-artificial-t2/matenergy-ml

./bootstrap.sh           # Linux / macOS / Git Bash / WSL
# or, on native Windows PowerShell:
.\bootstrap.ps1
```

No manual `.env` setup needed — it generates one with random secrets on
first run. Safe to re-run (every step is idempotent); pass `--reset` /
`-Reset` for a guaranteed clean slate, or `--skip-train` / `-SkipTrain` to
skip model training for a faster boot. At the end it prints the login
credentials and the URLs to open. See `docs/deployment_guide.md` for details
and troubleshooting.

### Manual setup (equivalent, step by step)

```bash
# 1. Clone the repository
git clone <repo-url>
cd inteligencia-artificial-t2/matenergy-ml

# 2. Create environment file
cp .env.example .env
# Edit .env — at minimum set POSTGRES_PASSWORD, SECRET_KEY, JWT_SECRET_KEY

# 3. Start all services
docker compose up --build -d

# 4. Run database migrations
docker compose exec backend alembic upgrade head

# 5. Seed roles/admin, demo data, descriptors, baseline models, ranking
docker compose exec backend python scripts/seed_db.py
docker compose exec backend python scripts/import_demo_data.py
docker compose exec backend python scripts/generate_descriptors.py
docker compose exec backend python scripts/train_baseline_models.py
docker compose exec backend python scripts/generate_ranking.py
```

Services will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

---

## Prerequisites

- Docker 24.0+
- Docker Compose v2.20+
- 4 GB RAM minimum (8 GB recommended for ML training)
- 10 GB free disk space

For local development without Docker:
- Python 3.12
- Node.js 20+
- PostgreSQL 16
- Redis 7 (optional, required for rate limiting)

---

## Installation (Local Development)

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env in the project root (matenergy-ml/.env)
cp ../.env.example ../.env
# Edit ../.env

# Run database migrations
alembic upgrade head

# Start development server (auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server (proxies API to localhost:8000)
npm run dev
```

---

## Configuration (.env)

| Variable | Required | Default | Description |
|---|---|---|---|
| `POSTGRES_PASSWORD` | Yes | — | PostgreSQL password |
| `SECRET_KEY` | Yes | — | General application secret (64 hex chars) |
| `JWT_SECRET_KEY` | Yes | — | JWT signing key (64 hex chars) |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token lifetime |
| `BACKEND_CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated allowed origins |
| `STABILITY_THRESHOLD_EV` | No | `0.05` | eV/atom threshold for stability label |
| `MAX_UPLOAD_SIZE_MB` | No | `50` | Maximum CSV upload size |
| `MAX_ROWS_PER_DATASET` | No | `100000` | Maximum rows per dataset |
| `MATERIALS_PROJECT_API_KEY` | No | `` | Materials Project API key |
| `ARTIFACT_STORAGE_PATH` | No | `./artifacts` | Path for model artifact storage |
| `REDIS_URL` | No | `` | Redis URL for rate limiting |

Generate strong secrets:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Running with Docker

```bash
# Start stack
docker compose up -d

# View logs
docker compose logs -f backend

# Stop stack
docker compose down

# Stop and remove volumes (WARNING: deletes data)
docker compose down -v
```

---

## Directory Structure

```
matenergy-ml/
├── backend/
│   ├── app/
│   │   ├── api/v1/            # FastAPI routers
│   │   ├── application/       # Use-case services (application layer)
│   │   ├── core/              # Config, constants, JWT, RBAC, logging
│   │   ├── domain/
│   │   │   ├── entities/      # Domain entities
│   │   │   └── services/      # Domain service interfaces
│   │   ├── infrastructure/
│   │   │   ├── database/      # SQLAlchemy models + repositories
│   │   │   ├── descriptors/   # Compositional + structural pipelines
│   │   │   ├── ml/            # Trainers, evaluators, predictor
│   │   │   ├── materials/     # CSV loader
│   │   │   └── security/      # Security utilities
│   │   ├── schemas/           # Pydantic v2 request/response schemas
│   │   └── tests/             # Unit, integration, ML, security tests
│   ├── alembic/               # Database migrations
│   └── scripts/               # Seed and utility scripts
├── frontend/
│   └── src/                   # React + TypeScript SPA
├── artifacts/
│   ├── models/                # Serialised model artifacts (.joblib)
│   └── reports/               # Generated evaluation reports
├── data/demo/                 # Demo datasets
├── database/seeds/            # SQL seed files for Docker init
├── docs/                      # Technical documentation
└── notebooks/                 # Exploratory Jupyter notebooks
```

---

## API Documentation

Interactive documentation is auto-generated from the OpenAPI schema:

- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`

See also: [docs/api_documentation.md](docs/api_documentation.md)

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Web framework | FastAPI | 0.115+ |
| ASGI server | Uvicorn | 0.32+ |
| Data validation | Pydantic v2 | 2.9+ |
| ORM | SQLAlchemy | 2.0+ |
| Migrations | Alembic | 1.14+ |
| Database | PostgreSQL | 16 |
| Cache / rate limiting | Redis | 7 |
| Authentication | PyJWT + argon2-cffi | 2.9+ |
| Materials science | pymatgen + matminer | 2024.11+ |
| Machine learning | scikit-learn | 1.5+ |
| Numerical computing | NumPy + SciPy + pandas | 2.x |
| Explainability | SHAP | 0.46+ |
| Logging | structlog | 24.4+ |
| Frontend framework | React + TypeScript | 18.3 + 5.7 |
| Build tool | Vite | 6.0+ |
| UI components | Tailwind CSS + Recharts | 3.4+ |
| HTTP client | axios | 1.7+ |
| Containerisation | Docker + Docker Compose | 24 + v2 |

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
