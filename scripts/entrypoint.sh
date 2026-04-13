#!/bin/bash
# Production entrypoint — kör migrations före uvicorn.
# Används av Dockerfile ENTRYPOINT.
set -e

echo "[entrypoint] Running alembic migrations..."
alembic upgrade head

echo "[entrypoint] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
