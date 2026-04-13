# --- Stage 1: Backend build ---
FROM python:3.12-slim AS backend-build
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY backend/pyproject.toml .
RUN uv pip install --system -r pyproject.toml
COPY backend/ .

# --- Stage 2: Frontend build ---
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# --- Stage 3: Production image ---
FROM python:3.12-slim AS production
WORKDIR /app

# Kopiera Python-deps från build-stage
COPY --from=backend-build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-build /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=backend-build /usr/local/bin/alembic /usr/local/bin/alembic
COPY backend/ .

# Kopiera frontend build till static dir
COPY --from=frontend-build /app/dist /app/static

# Weasyprint system-dependencies + curl för HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
    libcairo2 libgdk-pixbuf-2.0-0 libharfbuzz0b libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Kopiera entrypoint-script (kör alembic upgrade head före uvicorn)
COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Non-root user
RUN useradd -r -s /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck mot /health (database-roundtrip)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -fs http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
