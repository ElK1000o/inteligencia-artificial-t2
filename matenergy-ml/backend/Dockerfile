# ============================================================
# MatEnergy-ML — Backend Dockerfile
# Python 3.12-slim, non-root user
# ============================================================

FROM python:3.12-slim AS base

# ---- System dependencies ----
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Non-root user ----
RUN groupadd --gid 1001 appgroup \
 && useradd  --uid 1001 --gid 1001 --no-create-home --shell /bin/bash appuser

# ---- Working directory ----
WORKDIR /app

# ---- Python dependencies ----
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ---- Application source ----
COPY --chown=appuser:appgroup . .

# ---- Storage directories ----
RUN mkdir -p /app/artifacts/models /app/artifacts/reports /app/data \
 && chown -R appuser:appgroup /app/artifacts /app/data

# ---- Switch to non-root user ----
USER appuser

# ---- Expose API port ----
EXPOSE 8000

# ---- Health check ----
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# ---- Entry point ----
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
