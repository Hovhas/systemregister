# Bidra till systemregister

## Utvecklingsmiljö

```bash
git clone https://github.com/Hovhas/systemregister.git
cd systemregister

# Starta PostgreSQL + backend + frontend
docker compose up -d

# Kör migrationer
docker compose exec backend alembic upgrade head

# Seed med exempeldata
docker compose exec backend python -m scripts.seed

# Frontend dev (om du kör utanför Docker)
cd frontend && npm install && npm run dev
```

API-dokumentation: http://localhost:8000/docs
Frontend: http://localhost:5173

## Codestyle

- **Backend:** ruff (config i `pyproject.toml`)
- **Frontend:** eslint + prettier
- **UI-text:** Svenska
- **Kod:** Engelska (variabelnamn, kommentarer, docstrings)
- **Type-hints:** Överallt (Python type hints + TypeScript strict mode)
- **Etiketter:** Centraliserade i `frontend/src/lib/labels.ts` — lägg aldrig etiketter direkt i komponenter

## Tester

### Backend

Kör per fil (session-isoleringsbrister gör att hela sviten inte kan köras samtidigt):

```bash
docker compose exec backend pytest tests/test_systems.py -v
docker compose exec backend pytest tests/test_gdpr.py -v
```

### Frontend

```bash
cd frontend && npm test
```

### TypeScript-typkontroll

```bash
cd frontend && npx tsc -b
```

## Pull Request-process

1. Skapa branch från `master`
2. Implementera + testa lokalt
3. Pusha + öppna PR
4. CI körs automatiskt (lint, tests, security scan, build)
5. Code review krävs innan merge
6. Squash & merge

## Commit-meddelanden

Använd konventionella prefix:

- `feat:` — ny funktion
- `fix:` — buggfix
- `refactor:` — refactoring utan beteendeändring
- `docs:` — dokumentation
- `test:` — tester
- `chore:` — bygg, CI, verktyg

## Säkerhet

Projektet följer OWASP Top 10 och ASVS nivå 2. Se `docs/SECURITY.md` för detaljer.

- Hårdkoda aldrig secrets — använd miljövariabler
- Rapportera sårbarheter direkt till projektansvarig (skapa inte publika issues)
- Alla beroenden skannas med `pip-audit` och `npm audit` i CI
