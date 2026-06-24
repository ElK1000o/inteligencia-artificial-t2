# MatEnergy-ML Deployment Guide

## Prerequisites

- Docker Engine 24.0+
- Docker Compose v2.20+
- 4 GB RAM minimum (8 GB recommended for ML training)
- 10 GB free disk space

## Quick Start (one-shot bootstrap script)

`bootstrap.sh` (Linux/macOS/Git Bash/WSL) and `bootstrap.ps1` (native Windows
PowerShell) automate everything below in one command: `.env` generation with
random secrets, `docker compose up --build`, waiting for the backend
healthcheck, Alembic migrations, seeding roles + a known admin login,
importing the demo dataset, generating descriptors, training the 6 baseline
models, activating the best model per target property, and generating a
candidate ranking.

```bash
cd matenergy-ml/
./bootstrap.sh              # or: .\bootstrap.ps1
```

Flags: `--reset` / `-Reset` wipes existing containers and volumes first for a
guaranteed clean slate (use this if a previous run left an inconsistent
state); `--skip-train` / `-SkipTrain` skips model training + ranking for a
faster boot when you only need the dataset loaded. The script is idempotent
— re-running it without flags skips any step that already completed (seed,
import, descriptors, training, ranking) and only fills in what's missing.

It prints the admin email/password and the frontend/API URLs at the end.
Override the generated admin credentials by exporting `ADMIN_EMAIL` /
`ADMIN_PASSWORD` (bash) or setting `$env:ADMIN_EMAIL` / `$env:ADMIN_PASSWORD`
(PowerShell) before running.

### Manual Quick Start (equivalent, step by step)

```bash
# 1. Clone and enter the project
cd matenergy-ml/

# 2. Copy and configure environment
cp .env.example .env
# Edit .env — REQUIRED: set POSTGRES_PASSWORD and JWT_SECRET_KEY

# 3. Start all services
docker compose up -d --build

# 4. Run database migrations
docker compose exec backend alembic upgrade head

# 5. Seed initial roles and admin user
docker compose exec backend python scripts/seed_db.py

# 6. Import demo dataset, generate descriptors, train models, rank candidates
docker compose exec backend python scripts/import_demo_data.py
docker compose exec backend python scripts/generate_descriptors.py
docker compose exec backend python scripts/train_baseline_models.py
docker compose exec backend python scripts/generate_ranking.py

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

## Cloud Deployment (Railway)

This deploys the exact same images used locally to [Railway](https://railway.com),
giving you a permanent public URL so a reviewer never has to run anything
themselves. Railway was chosen over a self-managed VM for this academic
deployment because it needs near-zero server administration (no SSH, no
manual TLS/firewall setup) at a small, predictable cost (Hobby plan, ~US$5/mo
of usage credit, comfortably covering one low-traffic Postgres + two small
containers). The same approach works on Render with equivalent concepts
(services, env vars, a managed Postgres add-on, persistent disks).

> **Note on Redis**: `docker-compose.yml` runs a Redis container and
> `REDIS_URL` is a documented setting, but nothing in `backend/app` actually
> imports `redis` or wires up `slowapi`'s rate limiter — `slowapi` is in
> `requirements.txt` but unused. Rate limiting described in
> `docs/cybersecurity_threat_model.md` (A2) is **not currently implemented**,
> so Redis is not needed for this deployment. Skip the Redis plugin below;
> add it back (and actually wire up `slowapi.Limiter`) if you implement
> rate limiting later.

> **Critical — persistent storage for trained models**: the backend writes
> model artifacts (`.joblib` files) and generated reports to
> `ARTIFACT_STORAGE_PATH` (`/app/artifacts` by default). Locally this is a
> named Docker volume that survives restarts. **Railway/Render container
> filesystems are ephemeral by default** — without an attached persistent
> volume, every redeploy silently wipes `/app/artifacts` while the database
> still references those file paths and hashes, so any prediction/report
> attempt after a redeploy fails with `ArtifactIntegrityError` (hash/file
> not found) even though training "succeeded." Step 3 below adds a Railway
> Volume mounted at `/app/artifacts` to prevent this — do not skip it.

> **Before you deploy**: rotate the Materials Project API key first (see
> the Security section above / `docs/cybersecurity_threat_model.md` F1) —
> it was previously committed to this repository's git history, which is
> public, so treat the old key as already leaked. Generate a fresh one at
> https://materialsproject.org/api and use only the new one in Railway's
> variables.

### 1. Create the project

In the Railway dashboard: **New Project → Deploy from GitHub repo**, select
this repository. Railway will ask for a root — pick "empty project" first
(don't let it auto-detect a single service); you'll add four services
manually so the monorepo's two Dockerfiles and two managed databases are
each configured independently.

### 2. Add managed Postgres

**New → Database → PostgreSQL**. A managed plugin — no Dockerfile needed,
no manual setup. Note its service name (default `Postgres`) — you'll
reference it below. (Skip Redis — see the note above.)

### 3. Add the backend service

**New → GitHub Repo** (same repo again) → name it `backend`. In its
**Settings**:
- **Root Directory**: `matenergy-ml/backend` (Railway auto-detects the
  `Dockerfile` there)
- **Networking**: leave without a public domain — the frontend reaches it
  over Railway's private network, never directly from the internet
- **Healthcheck Path** (optional): `/health`
- **Volumes → New Volume**: mount path `/app/artifacts` (any size, a few
  hundred MB is plenty for joblib models + generated reports). Without
  this, trained models are lost on the next redeploy — see the warning
  above.

In its **Variables** tab, set (using Railway's `${{ServiceName.VAR}}`
reference syntax so credentials are never typed manually):

| Variable | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `POSTGRES_USER` | `${{Postgres.PGUSER}}` |
| `POSTGRES_PASSWORD` | `${{Postgres.PGPASSWORD}}` |
| `POSTGRES_DB` | `${{Postgres.PGDATABASE}}` |
| `POSTGRES_HOST` | `${{Postgres.PGHOST}}` |
| `POSTGRES_PORT` | `${{Postgres.PGPORT}}` |
| `SECRET_KEY` | output of `openssl rand -hex 32` |
| `JWT_SECRET_KEY` | output of `openssl rand -hex 32` (different value) |
| `MATERIALS_PROJECT_API_KEY` | your rotated key, or leave blank |
| `BACKEND_CORS_ORIGINS` | set after step 4, once you have the frontend's URL |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | your choice — used once in step 6 |

Leave `REDIS_URL` unset — nothing in the code reads it.

Deploy. Railway builds `matenergy-ml/backend/Dockerfile`; the entrypoint
runs `alembic upgrade head` automatically before the app starts (no manual
migration step needed on this platform — see `backend/docker-entrypoint.sh`).

### 4. Add the frontend service

**New → GitHub Repo** → name it `frontend`. **Settings**:
- **Root Directory**: `matenergy-ml/frontend`
- **Networking → Generate Domain** — this is the public URL the reviewer
  will open (e.g. `matenergy-ml.up.railway.app`)

**Variables**:

| Variable | Value |
|---|---|
| `BACKEND_HOST` | `${{backend.RAILWAY_PRIVATE_DOMAIN}}` |
| `BACKEND_PORT` | `8000` |

(`PORT` is injected automatically by Railway for the public domain — do not
set it yourself; the nginx template in `frontend/nginx.conf.template`
already reads it.) Deploy.

### 5. Wire up CORS

Copy the frontend's public URL from step 4, go back to the **backend**
service's Variables, and set `BACKEND_CORS_ORIGINS` to that URL (e.g.
`https://matenergy-ml.up.railway.app`). Railway redeploys the backend
automatically when a variable changes.

### 6. Seed data (one-time)

Install the Railway CLI (`npm i -g @railway/cli`), then from
`matenergy-ml/`:

```bash
railway login
railway link                                            # select this project
railway run --service backend python scripts/seed_db.py
railway run --service backend python scripts/import_demo_data.py
railway run --service backend python scripts/generate_descriptors.py
railway run --service backend python scripts/train_baseline_models.py
railway run --service backend python scripts/generate_ranking.py
```

These are the same idempotent scripts `bootstrap.sh` runs locally — safe to
re-run after any redeploy. To also activate a model per target property
(so the Dashboard doesn't show "0 active models"), copy the Python snippet
from the "Activating the best model" step inside `bootstrap.sh` and run it
the same way via `railway run --service backend python -c "..."`.

### 7. Verify

Open the frontend's public URL, log in with `ADMIN_EMAIL` / `ADMIN_PASSWORD`,
and confirm the Dashboard shows real data (materials, active models,
candidates). From here the reviewer only ever needs that one URL — Docker,
Alembic, and the CLI are no longer part of their workflow at all.

### Cost and maintenance notes

- Auto-deploys on every push to the connected branch; disable this in
  service Settings if you don't want every commit to redeploy automatically
  while iterating.
- Pausing or deleting the services stops billing; the Postgres/Redis data
  persists as long as those services (and their volumes) aren't deleted.
- Logs are available per-service in the Railway dashboard — use them the
  same way you'd use `docker compose logs backend` locally.

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
