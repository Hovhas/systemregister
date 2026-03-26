# Systemregister — Sundsvalls kommunkoncern

IT-systemregister med stöd för NIS2/CSL, ISO 27001, MSB/MCF och GDPR.  
Multi-org-stöd för DigIT (13+ politiskt styrda organisationer).

## Snabbstart (lokal utveckling)

```bash
# Starta PostgreSQL + backend
docker compose up -d

# Kör migrationer
docker compose exec backend alembic upgrade head

# Seed med exempeldata
docker compose exec backend python -m scripts.seed

# API-dokumentation
open http://localhost:8000/docs
```

## Projektstruktur

```
systemregister/
├── CLAUDE.md              # Projektguide för Claude Code
├── docker-compose.yml     # Lokal dev-miljö
├── Dockerfile             # Produktion (multi-stage)
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI-endpoints
│   │   ├── core/          # Config, databas
│   │   ├── models/        # SQLAlchemy-modeller + enums
│   │   ├── schemas/       # Pydantic request/response
│   │   ├── services/      # Business logic
│   │   └── main.py        # FastAPI app
│   ├── alembic/           # Databasmigrationer
│   └── pyproject.toml
├── frontend/              # React + TypeScript (TBD fas 3)
├── k8s/
│   ├── base/              # Kustomize base manifests
│   └── overlays/dev/      # Dev-overlay
└── scripts/
    ├── init-db.sql        # PostgreSQL extensions
    └── seed.py            # Exempeldata
```

## Tech stack

- **Backend:** Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · Alembic · PostgreSQL 16
- **Frontend:** React 18 · TypeScript · Vite · Tailwind · shadcn/ui (fas 3)
- **Deploy:** k3s · Flux CD · Kustomize · Longhorn · Traefik · SOPS/age

## Regulatoriska drivkrafter

- Cybersäkerhetslagen (SFS 2025:1506) / NIS2
- MSBFS 2020:6 & 2020:7 (MCF)
- ISO/IEC 27001:2022 (Annex A.5.9, A.5.12 m.fl.)
- GDPR artikel 30 (behandlingsregister)
