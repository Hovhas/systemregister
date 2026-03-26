# State — Systemregister

**Uppdaterad:** 2026-03-26

## Aktuell status

**Fas 2 — GDPR, beroenden och avtal** (KLAR)

### Fas 1 — Datamodell + API (KLAR)
- [x] SQLAlchemy-modeller (8 tabeller)
- [x] Alembic-setup
- [x] CRUD endpoints: organizations, systems
- [x] Docker Compose + Dockerfile
- [x] Kustomize base + dev-overlay
- [x] Seed-script med exempeldata
- [x] Sok/filter med query params
- [x] Audit trail via SQLAlchemy events
- [x] Grundlaggande tester — 30 tester

### Fas 2 — Karnfunktionalitet (KLAR)
- [x] Informationsklassning (K/R/T) med historik — CRUD + latest endpoint
- [x] Agarskapshantering (roller) — CRUD for SystemOwner
- [x] Systemintegrationer/beroenden — CRUD + filter + per-system-vy
- [x] Multi-org RLS i PostgreSQL — Alembic-migration + policies
- [x] Import/export (Excel, CSV, JSON)
- [x] Tester — 89 tester totalt (alla grona)

## Beslutslogg

| Datum | Beslut | Motivering |
|-------|--------|------------|
| 2026-03-26 | Skall-attribut som fasta kolumner, Bor som JSONB | Balans mellan schema-sakerhet och flexibilitet |
| 2026-03-26 | PostgreSQL RLS for multi-org | Dataisolering pa databasniva — sakrare an applikationslogik |
| 2026-03-26 | KLASSA som komplement, inte ersattning | KLASSA saknar API, CMDB-funk och multi-tenant |
| 2026-03-26 | Egenbyggd losning | Sundsvalls tekniska mognad + API-first + specifika multi-org-krav |
| 2026-03-26 | RLS via X-Organization-Id header | Placeholder tills OIDC-auth ar pa plats |
| 2026-03-26 | after_flush for audit trail | Atomart med original-transaktionen, inget extra roundtrip |

## Blockers

Inga aktiva blockers.

## Kanda problem

- FK-violations (t.ex. ogiltigt organization_id) ger 500 istf 422 — bor fixas
- classified_at anvander func.now() (transaktionstid) — tva klassningar i samma transaktion far identisk tid

## Nasta steg

Fas 3 — Frontend (React + shadcn/ui)

---

Kor `/projekt:status` for att se progress.
