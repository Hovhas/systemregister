# Systemregister — Sundsvalls kommunkoncern

## Projektöversikt

IT-systemregister för Sundsvalls kommunkoncern. Multi-org-stöd för DigIT (13+ politiskt styrda organisationer). Fyra regulatoriska drivkrafter: NIS2/CSL, ISO 27001, MSB/MCF-föreskrifter, GDPR.

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL 16
- **Frontend:** React 19, TypeScript, Vite 8, Tailwind CSS 4, shadcn/ui, TanStack Query v5, React Router v7
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

## UX-kontext

Målgrupp: IT-förvaltare och systemägare i kommunal sektor
Teknisk nivå: Medel — vana vid IT-system men inte utvecklare
Primära uppgifter: Registrera system, uppdatera ägarskap, följa upp efterlevnadsstatus
UX-principer: Få klick, tydlig återkoppling, förlåtande (lätt att ångra/korrigera)
Tillgänglighet: Minst WCAG 2.1 AA (krav enligt DOS-lagen)

### Kravställning för frontend

Förbättra formulär och sidor genom att:
- Inline-validering med tydliga felmeddelanden på svenska (onBlur-baserad)
- Förloppsindikator vid flerstegsflöden
- Bekräfta destruktiva åtgärder med dialogruta
- Återkoppling efter sparande (toast-notis)
- Synliga etiketter på alla formulärfält, inte bara platshållartext

### UX-heuristiker (checklista)

För varje komponent/sida, kontrollera:
1. Systemstatus synlig — vet användaren alltid vad som händer?
2. Felprevention — bekräftas destruktiva åtgärder?
3. Igenkänning före minnesbelastning — är alternativ synliga, inte dolda?
4. Konsekvens — samma mönster som resten av appen?
5. Hjälp och dokumentation — är tomma vyer informativa?

### Tillgänglighet

WCAG 2.1 AA uppnådd (Fas 6):
- aria-etiketter på alla interaktiva element
- Tillräcklig färgkontrast (WCAG AA = 4.5:1)
- Tangentbordsnavigering (tabIndex, onKeyDown på tabellrader)
- Fokusindikatorer

### Visuell profil

Sundsvalls kommuns grafiska identitet: blå primärfärg (`#0057A8`), svenska gränssnittstext. Dark mode stöds via Tailwind CSS 4 + shadcn/ui.

## Konventioner

- **Språk i kod:** Engelska (variabelnamn, kommentarer, docstrings)
- **Språk i UI:** Svenska (alla labels, texter, felmeddelanden)
- **API-prefix:** `/api/v1/`
- **Databasnamn:** `systemregister`
- **Multi-org:** Alla system-relaterade tabeller har `organization_id` FK. Row-Level Security (RLS) i PostgreSQL.
- **Audit trail:** Automatisk via SQLAlchemy event listeners — alla ändringar loggas i `audit_log`.
- **Migrationer:** Alembic autogenerate. Kör `alembic revision --autogenerate -m "beskrivning"` sedan `alembic upgrade head`.
- **Tester:** pytest + httpx (async). Minst happy path per endpoint. Kör per fil — `pytest tests/` (alla filer) har session-isoleringsbrister.
- **Linting:** ruff (backend), eslint + prettier (frontend)
- **Etiketter (frontend):** Centraliserade i `frontend/src/lib/labels.ts`. Importera därifrån — lägg aldrig etiketter direkt i komponenter.
- **FormField:** Använd alltid `components/FormField.tsx` (har korrekt htmlFor/useId). Tre lokala kopior finns kvar i äldre kod — migrera vid refactoring.

## Datamodell — kärntabeller

### organizations
Multi-org: varje kommun/bolag/samverkansorgan. Fält: id, name, org_number, org_type (enum: kommun/bolag/samverkan/digit), parent_org_id (nullable FK self-ref).

### systems
Huvudentitet. ~70 attribut fördelade på:
- Fasta kolumner: id (UUID), organization_id (FK), name, description, system_category (enum), lifecycle_status (enum), criticality (enum), created_at, updated_at
- JSONB-kolumn `extended_attributes` för flexibla fält per kategori (teknisk stack, kostnader etc.)
- Alla Skall-attribut från kravspecen ska vara fasta kolumner. Bör-attribut kan vara JSONB.
- NIS2/compliance-attribut direkt på systems: nis2_applicable, nis2_classification, last_risk_assessment_date, klassa_reference_id
- GDPR-attribut direkt på systems: treats_personal_data (bool)

### system_classifications
Historisk K/R/T-klassning. Fält: id, system_id (FK), confidentiality (0-4), integrity (0-4), availability (0-4), traceability (0-4), classified_by, classified_at, valid_until, notes.

### system_owners
Roller per system. Fält: id, system_id (FK), name, email, role (enum: system_owner/information_owner/system_administrator/technical_administrator/it_contact/dpo), organization_id (FK).

### system_integrations
Relationer. Fält: id, source_system_id (FK), target_system_id (FK), integration_type (enum: api/file_transfer/db_replication/event/manual), data_types, frequency, description, criticality.

### gdpr_treatments
ROPA-koppling. Fält: id, system_id (FK), data_categories (enum[]), legal_basis, data_processor, processor_agreement_status, third_country_transfer, dpia_conducted (bool), ropa_reference_id.

### contracts
Avtal/leverantörer. Fält: id, system_id (FK), supplier_name, supplier_org_number, contract_id_external, contract_start, contract_end, sla_description, license_model, procurement_type.

### audit_log
Ändringshistorik. Fält: id, table_name, record_id (UUID), action (enum: create/update/delete), changed_by, changed_at, old_values (JSONB), new_values (JSONB), ip_address.

## Fas-plan

### Fas 1–5 — KLAR
Backend (52+ endpoints), frontend (10 sidor), Docker, K8s deploy, Flux CD — live på intern.hovhas.se.

### Fas 6 — UX och polish — KLAR
- Inline onBlur-validering i formulär
- Toast-notiser efter CRUD-operationer
- WCAG 2.1 AA tillgänglighetspass (aria-labels, tangentbordsnavigering, fokusindikatorer)
- Skeleton loaders på alla sidor
- Retry-knappar vid API-fel
- Centraliserade etiketter i `lib/labels.ts`
- Sundsvalls kommun visuell profil + dark mode
- Favicon

### Fas 7 — Auth/OIDC — planerad
- OIDC-integration mot Authentik eller Keycloak
- JWT-validering per request
- `changed_by` och `ip_address` i audit_log (kräver auth-kontext)
- RLS kopplas mot autentiserad organisation (löser P1.1/P1.2)

## Testsvit

**Totalt: 2430 tester** (2003 backend + 427 frontend)

Backend körs isolerat per fil:
```bash
docker compose exec backend pytest tests/test_systems.py -v
```

Frontend (vitest):
```bash
cd frontend && npm test
```

Kör ALDRIG `pytest tests/` (alla filer samtidigt) — session-isoleringsbrister ger falskt fel. Se TESTRESULTAT.md för kända failures och åtgärdsplan.

## Kommandon

```bash
# Lokal dev
docker compose up -d
docker compose exec backend alembic upgrade head

# Kör tester (backend — per fil)
docker compose exec backend pytest tests/test_systems.py -v

# Kör alla frontend-tester
cd frontend && npm test

# Skapa ny migration
docker compose exec backend alembic revision --autogenerate -m "add xyz"

# API-docs
open http://localhost:8000/docs

# Frontend dev
cd frontend && npm run dev
```

## Miljövariabler

Se `.env.example`. Känsliga värden hanteras via SOPS i k8s.
