# Systemregister — Sundsvalls kommunkoncern

## Projektöversikt

IT-systemregister för Sundsvalls kommunkoncern. Multi-org-stöd för DigIT (13+ politiskt styrda organisationer). Fyra regulatoriska drivkrafter: NIS2/CSL, ISO 27001, MSB/MCF-föreskrifter, GDPR.

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL 16
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query, React Router
- **Auth:** OIDC (Authentik/Keycloak) — placeholder med JWT under utveckling
- **Deployment:** k3s, Flux CD, Kustomize, Longhorn PVC, Traefik IngressRoute, SOPS/age
- **Lokal dev:** Docker Compose (backend + postgres + frontend)

## Arkitektur

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│  React SPA  │────▶│  FastAPI API  │────▶│ PostgreSQL │
│  (Nginx)    │     │  (Uvicorn)   │     │  (CNPG)    │
└─────────────┘     └──────────────┘     └────────────┘
      │                    │
      └──── Traefik ───────┘
```

## Konventioner

- **Språk i kod:** Engelska (variabelnamn, kommentarer, docstrings)
- **Språk i UI:** Svenska (alla labels, texter, felmeddelanden)
- **API-prefix:** `/api/v1/`
- **Databasnamn:** `systemregister`
- **Multi-org:** Alla system-relaterade tabeller har `organization_id` FK. Row-Level Security (RLS) i PostgreSQL.
- **Audit trail:** Automatisk via SQLAlchemy event listeners — alla ändringar loggas i `audit_log`.
- **Migrationer:** Alembic autogenerate. Kör `alembic revision --autogenerate -m "beskrivning"` sedan `alembic upgrade head`.
- **Tester:** pytest + httpx (async). Minst happy path per endpoint.
- **Linting:** ruff (backend), eslint + prettier (frontend)

## Datamodell — kärntabeller

### organizations
Multi-org: varje kommun/bolag/samverkansorgan. Fält: id, name, org_number, org_type (enum: kommun/bolag/samverkan/digit), parent_org_id (nullable FK self-ref).

### systems
Huvudentitet. ~70 attribut fördelade på:
- Fasta kolumner: id (UUID), organization_id (FK), name, description, system_category (enum), lifecycle_status (enum), criticality (enum), created_at, updated_at
- JSONB-kolumn `extended_attributes` för flexibla fält per kategori (teknisk stack, kostnader etc.)
- Alla Skall-attribut från kravspecen ska vara fasta kolumner. Bör-attribut kan vara JSONB.

### system_classifications
Historisk K/R/T-klassning. Fält: id, system_id (FK), confidentiality (0-4), integrity (0-4), availability (0-4), traceability (0-4), classified_by, classified_at, valid_until, notes.

### system_owners
Roller per system. Fält: id, system_id (FK), user_id (nullable), name, email, role (enum: system_owner/information_owner/system_administrator/technical_administrator/it_contact/dpo), organization_id (FK).

### system_integrations
Relationer. Fält: id, source_system_id (FK), target_system_id (FK), integration_type (enum: api/file_transfer/db_replication/event/manual), data_types, frequency, description, criticality.

### gdpr_treatments
ROPA-koppling. Fält: id, system_id (FK), treats_personal_data (bool), data_categories (enum[]), legal_basis, data_processor, processor_agreement_status, third_country_transfer, dpia_status, ropa_reference_id.

### contracts
Avtal/leverantörer. Fält: id, system_id (FK), supplier_name, supplier_org_number, contract_id_external, contract_start, contract_end, sla_description, license_model, procurement_type.

### NIS2/compliance (på systems-tabellen)
NIS2- och compliance-attribut lagras direkt på systems: nis2_applicable (bool), nis2_classification (enum), last_risk_assessment_date, klassa_reference_id.

### audit_log
Ändringshistorik. Fält: id, table_name, record_id (UUID), action (enum: create/update/delete), changed_by, changed_at, old_values (JSONB), new_values (JSONB), ip_address.

## Fas-plan

### Fas 1 — Datamodell + API (PÅGÅENDE)
- [x] SQLAlchemy-modeller
- [x] Alembic-setup
- [x] CRUD endpoints: organizations, systems
- [x] Docker Compose
- [ ] Sök/filter med query params
- [ ] Audit trail via SQLAlchemy events
- [ ] Grundläggande tester

### Fas 2 — Kärnfunktionalitet
- [ ] Informationsklassning (K/R/T) med historik
- [ ] Ägarskapshantering (roller)
- [ ] Multi-org RLS i PostgreSQL
- [ ] Import/export (Excel, CSV, JSON)
- [ ] Systemintegrationer/beroenden

### Fas 3 — Frontend
- [ ] React-app med Vite + shadcn/ui
- [ ] Systemlista med sök/filter/sortering
- [ ] Detaljvy med flikar per attributkategori
- [ ] Dashboard med KPI:er (antal system, klassningsstatus, compliance-gap)
- [ ] Beroendekartan (d3 eller vis.js)

### Fas 4 — GDPR + compliance
- [ ] ROPA-koppling
- [ ] PuB-avtal-tracking
- [ ] NIS2-flaggning och rapporter
- [ ] PDF/Excel-rapportgenerering

### Fas 5 — K8s deploy
- [ ] Dockerfile (multi-stage)
- [ ] Kustomize base + overlays (dev/prod)
- [ ] Flux GitRepository + Kustomization
- [ ] Traefik IngressRoute
- [ ] SOPS-krypterade secrets
- [ ] CronJob: backup till TrueNAS

## Kommandon

```bash
# Lokal dev
docker compose up -d
docker compose exec backend alembic upgrade head

# Kör tester
docker compose exec backend pytest -v

# Skapa ny migration
docker compose exec backend alembic revision --autogenerate -m "add xyz"

# API-docs
open http://localhost:8000/docs
```

## Miljövariabler

Se `.env.example`. Känsliga värden hanteras via SOPS i k8s.
