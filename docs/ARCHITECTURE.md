# Arkitektur — Systemregister

## Tech stack

| Lager | Teknik |
|-------|--------|
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS 4, shadcn/ui, TanStack Query v5, React Router v7 |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Databas | PostgreSQL 16 (RLS, JSONB) |
| Deploy | Dokploy (Docker-based PaaS) |
| CI | GitHub Actions (lint, test, security scan, build) |

## Request flow

```
Browser
  |
  v
Dokploy Reverse Proxy (HTTPS)
  |
  +---> Nginx (frontend, statiska filer)
  |       |
  |       +---> /api/* proxy_pass -->+
  |                                  |
  +----------------------------------+
  |
  v
Uvicorn (FastAPI)
  |
  +---> SecurityHeadersMiddleware
  +---> CORS Middleware
  +---> Rate Limiting
  |
  v
API Router (/api/v1/*)
  |
  +---> Pydantic validation (request)
  +---> get_rls_db (org-context)
  |
  v
SQLAlchemy ORM
  |
  +---> RLS filter (organization_id)
  +---> Audit event listener
  |
  v
PostgreSQL 16
```

## Datamodell

```mermaid
erDiagram
    organizations ||--o{ systems : "äger"
    organizations ||--o{ objekt : "äger"
    organizations ||--o{ modules : "äger"
    organizations ||--o{ information_assets : "äger"

    objekt ||--o{ systems : "objekt_id"

    systems ||--o{ system_classifications : "system_id"
    systems ||--o{ system_owners : "system_id"
    systems ||--o{ system_integrations : "source_system_id"
    systems ||--o{ system_integrations : "target_system_id"
    systems ||--o{ gdpr_treatments : "system_id"
    systems ||--o{ contracts : "system_id"
    systems ||--o{ components : "system_id"
    systems }o--o{ modules : "N:M system_modules"
    systems }o--o{ information_assets : "N:M system_information_assets"

    organizations {
        uuid id PK
        string name
        string org_number
        enum org_type
        uuid parent_org_id FK
    }

    objekt {
        uuid id PK
        uuid organization_id FK
        string name
        string object_owner
        string object_leader
    }

    systems {
        uuid id PK
        uuid organization_id FK
        uuid objekt_id FK
        string name
        enum system_category
        enum lifecycle_status
        enum criticality
        jsonb extended_attributes
    }

    components {
        uuid id PK
        uuid system_id FK
        uuid organization_id FK
        string name
        string component_type
    }

    modules {
        uuid id PK
        uuid organization_id FK
        string name
        enum lifecycle_status
        boolean uses_ai
    }

    information_assets {
        uuid id PK
        uuid organization_id FK
        string name
        boolean contains_personal_data
        int confidentiality
        int integrity
        int availability
    }

    system_classifications {
        uuid id PK
        uuid system_id FK
        int confidentiality
        int integrity
        int availability
        int traceability
    }

    system_owners {
        uuid id PK
        uuid system_id FK
        enum role
        string name
        string email
    }

    system_integrations {
        uuid id PK
        uuid source_system_id FK
        uuid target_system_id FK
        enum integration_type
        enum criticality
    }

    gdpr_treatments {
        uuid id PK
        uuid system_id FK
        string legal_basis
        enum processor_agreement_status
        boolean dpia_conducted
    }

    contracts {
        uuid id PK
        uuid system_id FK
        string supplier_name
        date contract_start
        date contract_end
    }

    audit_log {
        uuid id PK
        string table_name
        uuid record_id
        enum action
        string changed_by
        jsonb old_values
        jsonb new_values
    }
```

## Deployment-topologi

```
GitHub (Hovhas/systemregister)
  |
  | push to master
  v
Dokploy Webhook
  |
  v
Docker Build (multi-stage)
  |
  +---> Stage 1: Backend (uv + Python deps)
  +---> Stage 2: Frontend (npm + Vite build)
  +---> Stage 3: Production (Nginx + Uvicorn)
  |
  v
Dokploy Container
  |
  +---> Nginx (:80) - statiska filer + API proxy
  +---> Uvicorn (:8000) - FastAPI backend
  +---> PostgreSQL (Dokploy-managed)
```

## Entitetshierarki

```
Organisation
  |
  +---> Objekt (verksamhetsområde)
  |       |
  |       +---> System (IT-system)
  |               |
  |               +---> Komponent (delsystem)
  |               +---> Modul (N:M, delad mellan system)
  |               +---> Informationsmängd (N:M, delad mellan system)
  |               +---> Klassning (K/R/T historik)
  |               +---> Ägare/roller
  |               +---> Integrationer
  |               +---> GDPR-behandlingar
  |               +---> Avtal
  |
  +---> Modul (organisation-scope)
  +---> Informationsmängd (organisation-scope)
```
