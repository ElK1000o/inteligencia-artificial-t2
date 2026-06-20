# MatEnergy-ML Deployment Guide

## Prerequisites

- Docker Engine 24.0+
- Docker Compose v2.20+
- 4 GB RAM minimum (8 GB recommended for ML training)
- 10 GB free disk space

## Quick Start (Docker Compose)

```bash
# 1. Clone and enter the project
cd matenergy-ml/

# 2. Copy and configure environment
cp .env.example .env
# Edit .env — REQUIRED: set POSTGRES_PASSWORD and JWT_SECRET_KEY

# 3. Start all services
docker compose up -d

# 4. Run database migrations
docker compose exec backend alembic upgrade head

# 5. Seed initial roles and admin user
docker compose exec backend python scripts/seed_db.py

# 6. Import demo dataset
docker compose exec backend python scripts/import_demo_data.py

# 7. Open the app
# Frontend: http://localhost:3000
# API docs:  http://localhost:8000/docs
```

## Environment Configuration

| Variable | Required | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | **Yes** | PostgreSQL password — never use default in production |
| `JWT_SECRET_KEY` | **Yes** | 32+ character random string for JWT signing |
| `POSTGRES_USER` | No | Database user (default: `matenergy`) |
| `POSTGRES_DB` | No | Database name (default: `matenergy_db`) |
| `ENVIRONMENT` | No | `development` or `production` |
| `BACKEND_CORS_ORIGINS` | No | Comma-separated allowed origins |
| `MATERIALS_PROJECT_API_KEY` | No | MP API key for external data |
| `MAX_UPLOAD_SIZE_MB` | No | File upload limit (default: 50) |
| `STABILITY_THRESHOLD_EV` | No | Hull energy stability cutoff (default: 0.05) |

Generate a secure JWT secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Running Without Docker (Development)

### Backend

```bash
cd backend/
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
cp ../.env.example .env
# Edit .env

# Run migrations
alembic upgrade head

# Seed database
python scripts/seed_db.py

# Start backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend/
npm install
npm run dev
# Opens at http://localhost:5173
```

## First Run Workflow

After starting the system, run these scripts in order:

```bash
python scripts/seed_db.py           # Creates roles + admin user
python scripts/import_demo_data.py  # Imports 135 demo Li-ion materials
python scripts/generate_descriptors.py  # Computes 57 compositional features
python scripts/train_baseline_models.py # Trains 6 baseline ML models
python scripts/generate_ranking.py  # Creates candidate ranking
```

## Production Checklist

- [ ] Change all default credentials (`POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD`)
- [ ] Set `ENVIRONMENT=production` (disables /docs, /redoc)
- [ ] Restrict `BACKEND_CORS_ORIGINS` to your actual frontend domain
- [ ] Enable TLS via Nginx reverse proxy (do not expose port 8000 directly)
- [ ] Set up automated PostgreSQL backups (`pg_dump` cron or managed service)
- [ ] Configure log rotation for Docker container logs
- [ ] Set resource limits in `docker-compose.yml` (already included)
- [ ] Use Docker secrets or a secrets manager instead of `.env` file
- [ ] Run containers as non-root (already configured)
- [ ] Enable PostgreSQL SSL connections

## Backup and Restore

```bash
# Backup
docker compose exec db pg_dump -U matenergy matenergy_db > backup_$(date +%Y%m%d).sql

# Restore
docker compose exec -T db psql -U matenergy matenergy_db < backup_20250101.sql
```

## Troubleshooting

**Backend fails to start**: Ensure PostgreSQL is healthy (`docker compose ps`). The backend waits for the `service_healthy` condition.

**Alembic migration fails**: Check that `POSTGRES_PASSWORD` in `.env` matches the value used when the DB was first created.

**CSV upload rejected**: Verify the file is UTF-8 encoded, has a `formula` column, and is under `MAX_UPLOAD_SIZE_MB`.

**Model training fails**: Ensure descriptors have been generated for the dataset first (`scripts/generate_descriptors.py`).
