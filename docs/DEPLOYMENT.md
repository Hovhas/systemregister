# Deployment — Systemregister

## Dokploy-flöde

```
GitHub push (master) → Dokploy webhook → Docker build → Deploy → Live
```

1. Utvecklare pushar till `master` på GitHub
2. Dokploy webhook triggas automatiskt
3. Multi-stage Dockerfile bygger:
   - Backend: Python 3.12 + uv + FastAPI
   - Frontend: Node + Vite build (statiska filer)
   - Production: Nginx + Uvicorn
4. Ny container deployas och ersätter föregående

## Dokploy-app

- **App-ID:** `hakans-systemregister-yuzjf3`
- **URL:** systemregister.hakans.sundsvall.dev

## Miljövariabler per miljö

| Variabel | Development | Production |
|----------|-------------|------------|
| `ENVIRONMENT` | `development` | `production` |
| `SECRET_KEY` | Dummy-värde | Slumpmässig 32-byte hex |
| `DATABASE_URL` | `postgresql+asyncpg://...@db:5432/systemregister` | Dokploy Postgres |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | `https://systemregister.hakans.sundsvall.dev` |
| `LOG_LEVEL` | `DEBUG` | `INFO` |

Konfigurera miljövariabler i Dokploy UI: App -> Environment.

## Healthcheck efter deploy

1. Verifiera att Dokploy-bygget lyckas (grön status i UI)
2. Kontrollera runtime-loggar i Dokploy: leta efter `Application startup complete`
3. Testa API: `curl https://systemregister.hakans.sundsvall.dev/api/v1/health`
4. Testa frontend: öppna URL i webbläsare

## Rollback

1. Öppna Dokploy UI
2. Gå till app -> Deployments
3. Välj en tidigare lyckad deployment
4. Klicka "Rollback"

## Viktigt

- Det finns ingen staging-miljö ännu. Allt deployas direkt till produktion.
- Tester (pytest, vitest) körs INTE automatiskt i Dokploy-bygget. TS-fel och import-fel fångas av Docker-bygget; runtime-fel fångas inte.
- CI via GitHub Actions kör lint, tester och security scan innan merge.
