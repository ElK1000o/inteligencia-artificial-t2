#!/bin/sh
# Runs Alembic migrations before starting the application. Idempotent —
# "upgrade head" is a no-op when the schema is already current, so this is
# safe to run on every container start (local docker-compose and cloud
# platforms like Railway/Render that don't offer a separate migration step).
set -e

alembic upgrade head

exec "$@"
