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

## UX-kontext

Målgrupp: IT-förvaltare och systemägare i kommunal sektor
Teknisk nivå: Medel — vana vid IT-system men inte utvecklare
Primära uppgifter: Registrera system, uppdatera ägarskap, följa upp efterlevnadsstatus
UX-principer: Få klick, tydlig återkoppling, förlåtande (lätt att ångra/korrigera)
Tillgänglighet: Minst WCAG 2.1 AA (krav enligt DOS-lagen)

### Kravställning för frontend

Förbättra formulär och sidor genom att:
- Inline-validering med tydliga felmeddelanden på svenska
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

### Tillgänglighet (separat pass)

Granska tillgängligheten på alla sidor. Åtgärda:
- Saknade aria-etiketter
- Otillräcklig färgkontrast (WCAG AA = 4.5:1)
- Brister i tangentbordsnavigering
- Saknade fokusindikatorer

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

### Fas 1–5 — KLAR
Backend (52+ endpoints), frontend (10 sidor), Docker, K8s deploy, Flux CD — allt live på intern.hovhas.se.

### Fas 6 — UX-förbättringar och polish
- [ ] Inline-validering i formulär
- [ ] Toast-notiser efter CRUD-operationer
- [ ] WCAG 2.1 AA tillgänglighetspass
- [ ] Responsivitet för surfplatta/mobil
- [ ] OIDC-autentisering (Authentik/Keycloak)

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
