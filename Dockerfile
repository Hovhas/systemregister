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

# Non-root user
RUN useradd -r -s /bin/false appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
