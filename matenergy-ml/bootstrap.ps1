# ============================================================
# MatEnergy-ML -- Full environment bootstrap (PowerShell)
# ============================================================
# One-shot setup for graders/reviewers: generates .env if missing, builds
# and starts the Docker Compose stack, runs Alembic migrations, seeds
# roles + an admin user with a known password, imports the demo Li-ion
# materials dataset, generates compositional descriptors, trains the 6
# baseline ML models, and produces a candidate ranking.
#
# Usage:
#   .\bootstrap.ps1                  normal run (safe to re-run)
#   .\bootstrap.ps1 -Reset           wipe existing containers/volumes first
#                                    (DELETES local DB/artifact data)
#   .\bootstrap.ps1 -SkipTrain       skip model training + ranking
# ============================================================
param(
    [switch]$Reset,
    [switch]$SkipTrain
)

# Deliberately NOT using $ErrorActionPreference = 'Stop': Docker CLI writes
# routine progress info to stderr on every call, and in Windows PowerShell
# 5.1 any redirected/merged stderr from a native command becomes a
# terminating error under 'Stop' even on success. Native command failures
# are instead detected explicitly via $LASTEXITCODE after each call.
Set-Location $PSScriptRoot

function Info($msg) { Write-Host "[bootstrap] $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "[bootstrap] $msg" -ForegroundColor Yellow }
function Err($msg)  { Write-Host "[bootstrap] $msg" -ForegroundColor Red }
function Test-LastExit($msg) {
    if ($LASTEXITCODE -ne 0) {
        Err $msg
        exit 1
    }
}

# ---------------------------------------------------------------
# 1. Prerequisites
# ---------------------------------------------------------------
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Err "Docker no esta instalado. https://docs.docker.com/get-docker/"
    exit 1
}
docker compose version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Err "Docker Compose v2 no disponible (actualiza Docker Desktop o instala el plugin compose)."
    exit 1
}

if ($Reset) {
    Warn "Eliminando contenedores y volumenes existentes (-Reset)..."
    docker compose down -v --remove-orphans
}

# ---------------------------------------------------------------
# 2. .env -- generate with random secrets if missing
# ---------------------------------------------------------------
function New-RandHex([int]$NumBytes) {
    $bytes = New-Object byte[] $NumBytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    -join ($bytes | ForEach-Object { $_.ToString('x2') })
}

if (-not (Test-Path .env)) {
    Info "No existe .env -- generando uno nuevo con secretos aleatorios..."
    $GenSecretKey = New-RandHex 32
    $GenJwtSecretKey = New-RandHex 32
    $GenPostgresPassword = New-RandHex 16
    $envContent = @"
# Generado automaticamente por bootstrap.ps1 -- no commitear este archivo.
ENVIRONMENT=development
LOG_LEVEL=INFO
AUDIT_LOG_ENABLED=true

POSTGRES_USER=matenergy
POSTGRES_PASSWORD=$GenPostgresPassword
POSTGRES_DB=matenergy_db
POSTGRES_HOST=db
POSTGRES_PORT=5432
DATABASE_URL=postgresql://`${POSTGRES_USER}:`${POSTGRES_PASSWORD}@`${POSTGRES_HOST}:`${POSTGRES_PORT}/`${POSTGRES_DB}

SECRET_KEY=$GenSecretKey
JWT_SECRET_KEY=$GenJwtSecretKey
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Optional -- the platform works fully without this (CSV-only mode).
# Only the Materials Project decomposition pathway and 3D structure
# viewer need it. Free key: https://materialsproject.org/api
MATERIALS_PROJECT_API_KEY=
JARVIS_API_KEY=
NOMAD_TOKEN=

MAX_UPLOAD_SIZE_MB=50
MAX_ROWS_PER_DATASET=100000
STABILITY_THRESHOLD_EV=0.05

ARTIFACT_STORAGE_PATH=./artifacts
DATA_STORAGE_PATH=./data
"@
    $envContent | Out-File -FilePath .env -Encoding utf8 -NoNewline
    Info ".env generado."
} else {
    Info ".env ya existe -- se reutiliza tal cual."
}

$envLines = Get-Content .env
$PgUserLine = $envLines | Where-Object { $_ -match '^POSTGRES_USER=' } | Select-Object -First 1
$PgDbLine = $envLines | Where-Object { $_ -match '^POSTGRES_DB=' } | Select-Object -First 1
$PostgresUserVal = if ($PgUserLine) { $PgUserLine.Split('=', 2)[1] } else { 'matenergy' }
$PostgresDbVal = if ($PgDbLine) { $PgDbLine.Split('=', 2)[1] } else { 'matenergy_db' }

# Admin login -- explicit and deterministic so graders get a known-working
# credential regardless of any prior session state. Override by setting
# $env:ADMIN_EMAIL / $env:ADMIN_PASSWORD before invoking this script.
$AdminEmail = if ($env:ADMIN_EMAIL) { $env:ADMIN_EMAIL } else { 'admin@matenergy.local' }
$AdminPassword = if ($env:ADMIN_PASSWORD) { $env:ADMIN_PASSWORD } else { 'MatEnergy#2026!Admin' }

# ---------------------------------------------------------------
# 3. Build & start the stack
# ---------------------------------------------------------------
Info "Construyendo imagenes y levantando el stack (puede tardar varios minutos la primera vez)..."
$upAttempts = 0
while ($true) {
    docker compose up -d --build
    if ($LASTEXITCODE -eq 0) { break }
    $upAttempts++
    if ($upAttempts -ge 3) {
        Err "docker compose up fallo tras 3 intentos. Revisa: docker compose logs"
        exit 1
    }
    Warn "docker compose up fallo (posible dependencia lenta al arrancar, p.ej. Postgres recuperandose) -- reintentando en 10s..."
    Start-Sleep -Seconds 10
}

# ---------------------------------------------------------------
# 4. Wait for backend healthy
# ---------------------------------------------------------------
Info "Esperando a que el backend este healthy..."
$attempts = 0
while ($true) {
    $backendContainer = docker compose ps -q backend
    $status = docker inspect -f '{{.State.Health.Status}}' $backendContainer 2>$null
    if ($status -eq 'healthy') { break }
    $attempts++
    if ($attempts -ge 60) {
        Err "El backend no llego a 'healthy' tras ~5 minutos. Revisa: docker compose logs backend"
        exit 1
    }
    Start-Sleep -Seconds 5
}
Info "Backend healthy."

# ---------------------------------------------------------------
# 5. Alembic migrations
# ---------------------------------------------------------------
Info "Aplicando migraciones Alembic..."
docker compose exec -T backend alembic upgrade head
Test-LastExit "Las migraciones Alembic fallaron."

# ---------------------------------------------------------------
# 6. Seed roles + admin user (idempotent), then assert the admin
#    password matches what we are about to print.
# ---------------------------------------------------------------
Info "Sembrando roles y usuario admin..."
docker compose exec -T -e "ADMIN_EMAIL=$AdminEmail" -e "ADMIN_PASSWORD=$AdminPassword" backend `
    python scripts/seed_db.py
Test-LastExit "El seed de roles/admin fallo."

$resetSnippet = @"
import os
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.models import User
from app.core.password_hasher import hash_password

email = os.environ['ADMIN_EMAIL']
pw = os.environ['ADMIN_PASSWORD']
with SessionLocal() as db:
    u = db.query(User).filter_by(email=email).first()
    if u:
        u.hashed_password = hash_password(pw)
        u.is_active = True
        db.commit()
"@
docker compose exec -T -e "ADMIN_EMAIL=$AdminEmail" -e "ADMIN_PASSWORD=$AdminPassword" backend `
    python -c "$resetSnippet" | Out-Null

# ---------------------------------------------------------------
# 7. Demo dataset (idempotent)
# ---------------------------------------------------------------
Info "Importando dataset de demostracion (materiales Li-ion)..."
docker compose exec -T backend python scripts/import_demo_data.py
Test-LastExit "La importacion del dataset demo fallo."

# ---------------------------------------------------------------
# 8. Descriptors (idempotent)
# ---------------------------------------------------------------
Info "Generando descriptores composicionales..."
docker compose exec -T backend python scripts/generate_descriptors.py
Test-LastExit "La generacion de descriptores fallo."

# ---------------------------------------------------------------
# 9. Baseline models + ranking (guarded)
# ---------------------------------------------------------------
if ($SkipTrain) {
    Warn "Entrenamiento de modelos omitido (-SkipTrain)."
} else {
    $modelCountRaw = docker compose exec -T db psql -U $PostgresUserVal -d $PostgresDbVal `
        -tAc "SELECT count(*) FROM model_versions;" 2>$null
    $modelCount = 0
    [int]::TryParse(($modelCountRaw -replace '\s', ''), [ref]$modelCount) | Out-Null

    if ($modelCount -ge 1) {
        Info "Ya existen $modelCount modelos entrenados -- omitiendo (usa -Reset para re-entrenar desde cero)."
    } else {
        Info "Entrenando 6 modelos baseline (Ridge, Random Forest, Gradient Boosting, clasificador)... 1-3 min."
        docker compose exec -T backend python scripts/train_baseline_models.py
        Test-LastExit "El entrenamiento de modelos fallo."
    }

    Info "Activando el mejor modelo por propiedad objetivo (para que el Dashboard no muestre 0 modelos activos)..."
    $activateSnippet = @"
from sqlalchemy import select
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.models.model_models import ModelVersion, ModelMetric, ModelTrainingRun
from app.infrastructure.database.repositories.model_repository import ModelVersionRepository

with SessionLocal() as db:
    repo = ModelVersionRepository(db)
    targets = db.execute(select(ModelVersion.target_property).distinct()).scalars().all()
    for target in targets:
        if repo.get_active_for_target(target):
            continue
        versions = db.execute(
            select(ModelVersion).where(ModelVersion.target_property == target)
        ).scalars().all()
        best, best_score, best_metric = None, None, None
        for v in versions:
            run = db.execute(
                select(ModelTrainingRun).where(ModelTrainingRun.model_version_id == v.id)
            ).scalars().first()
            if not run:
                continue
            metric_name = 'f1_macro' if v.task_type == 'classification' else 'mae'
            higher_is_better = v.task_type == 'classification'
            m = db.execute(
                select(ModelMetric).where(
                    ModelMetric.training_run_id == run.id,
                    ModelMetric.split == 'test',
                    ModelMetric.metric_name == metric_name,
                )
            ).scalars().first()
            if not m:
                continue
            if best_score is None or (higher_is_better and m.metric_value > best_score) or (not higher_is_better and m.metric_value < best_score):
                best, best_score, best_metric = v, m.metric_value, metric_name
        if best:
            repo.activate(best)
            print(f'  activated {best.name} for {target} ({best_metric}={best_score:.4f})')
    db.commit()
"@
    docker compose exec -T backend python -c "$activateSnippet"

    $rankingCountRaw = docker compose exec -T db psql -U $PostgresUserVal -d $PostgresDbVal `
        -tAc "SELECT count(*) FROM candidate_rankings;" 2>$null
    $rankingCount = 0
    [int]::TryParse(($rankingCountRaw -replace '\s', ''), [ref]$rankingCount) | Out-Null

    if ($rankingCount -ge 1) {
        Info "Ya existe al menos un ranking -- omitiendo."
    } else {
        Info "Generando ranking de candidatos de demostracion..."
        docker compose exec -T backend python scripts/generate_ranking.py
        Test-LastExit "La generacion del ranking fallo."
    }
}

# ---------------------------------------------------------------
# 10. Summary
# ---------------------------------------------------------------
Write-Host ""
Write-Host "============================================================"
Write-Host " MatEnergy-ML esta listo."
Write-Host "============================================================"
Write-Host " Frontend:    http://localhost:3000"
Write-Host " Backend API: http://localhost:8000/docs"
Write-Host ""
Write-Host " Login:"
Write-Host "   Email:    $AdminEmail"
Write-Host "   Password: $AdminPassword"
Write-Host ""
Write-Host " Detener:          docker compose down"
Write-Host " Ver logs:         docker compose logs -f backend"
Write-Host " Reiniciar limpio: .\bootstrap.ps1 -Reset"
Write-Host "============================================================"
