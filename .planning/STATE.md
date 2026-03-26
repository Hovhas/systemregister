# State — Systemregister

**Uppdaterad:** 2026-03-26

## Aktuell status

**Fas 1 — Datamodell + API** (PAGAENDE)

Klart:
- [x] SQLAlchemy-modeller
- [x] Alembic-setup
- [x] CRUD endpoints: organizations, systems
- [x] Docker Compose
- [x] Dockerfile (multi-stage)
- [x] Kustomize base + dev-overlay
- [x] Seed-script med exempeldata

Kvar:
- [x] Sok/filter med query params (redan implementerat i systems.py)
- [x] Audit trail via SQLAlchemy events (backend/app/core/audit.py)
- [x] Grundlaggande tester — 30 tester (backend/tests/)

## Beslutslogg

| Datum | Beslut | Motivering |
|-------|--------|------------|
| 2026-03-26 | Skall-attribut som fasta kolumner, Bor som JSONB | Balans mellan schema-sakerhet och flexibilitet |
| 2026-03-26 | PostgreSQL RLS for multi-org | Dataisolering pa databasniva — sakrare an applikationslogik |
| 2026-03-26 | KLASSA som komplement, inte ersattning | KLASSA saknar API, CMDB-funk och multi-tenant |
| 2026-03-26 | Egenbyggd losning | Sundsvalls tekniska mognad + API-first + specifika multi-org-krav |

## Blockers

Inga aktiva blockers.

## Nasta steg

1. Implementera sok/filter pa systems-endpointen
2. Lagg till audit trail (SQLAlchemy event listeners)
3. Skriv tester (minst happy path per endpoint)
4. Nar fas 1 ar klar: paborja fas 2 (klassning, agarskap, RLS)

---

Kor `/projekt:status` for att se progress.
