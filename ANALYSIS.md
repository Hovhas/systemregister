# ANALYSIS.md -- Systemregister fullstandig analys

Genererad: 2026-03-29 (ersatter analysen fran 2026-03-28)

---

## 1. Projektoversikt

| Kategori | Antal |
|----------|-------|
| **Backend-filer (app/)** | 18 .py |
| **Backend-endpoints** | 47 |
| **SQLAlchemy-modeller** | 8 |
| **Pydantic-schemas** | 25 |
| **Backend-tester** | ~1494 i 31 filer |
| **Alembic-migrationer** | 5 (0000-0004) |
| **Frontend-sidor** | 10 |
| **Frontend-komponenter (egna)** | 4 (Breadcrumb, ConfirmDialog, FormField, IntegrationDialog) |
| **Frontend-komponenter (shadcn/ui)** | 12 |
| **Frontend API-funktioner** | 28 |
| **Frontend-tester** | ~390 i 9 filer |
| **TypeScript interfaces/enums** | 25 |

### Tech stack
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, PostgreSQL 16
- Frontend: React 19, TypeScript, Vite 8, Tailwind CSS 4, shadcn/ui, TanStack Query v5, React Router v7
- Deploy: k3s, Flux CD, GitHub Actions CI

---

## 2. Arkitekturproblem

### 2.1 Backend

#### 2.1.1 RLS-policy vs Alembic-migration: Semantisk konflikt

Migration 0001 skapar RLS-policies med strikt `organization_id = current_org_id()` (utan NULL-bypass).
Men conftest.py skapar policyn med NULL-bypass: `current_org_id() IS NULL OR organization_id = current_org_id()`.

**Konsekvens:** Testerna och produktionskoden har olika RLS-semantik. I prod: om `set_org_context()` aldrig anropas blockeras alla rader. I test: NULL-bypass gor att allt syns.

#### 2.1.2 Inkonsekvent RLS-tillampning per endpoint

| Endpoint | Dependency | Korrekt? |
|----------|-----------|----------|
| `GET /systems/` (list) | `get_rls_db` | Ja |
| `GET /systems/{id}` (detail) | `get_rls_db` | Ja |
| `POST /systems/` (create) | `get_db` | Nej -- ingen org-validering |
| `PATCH /systems/{id}` | `get_db` | Nej -- kan andra utan RLS |
| `DELETE /systems/{id}` | `get_db` | Nej -- kan ta bort utan RLS |
| `POST /systems/{id}/classifications` | `get_db` | Nej |
| `POST /systems/{id}/owners` | `get_db` | Nej |
| `POST /integrations/` | `get_db` | Nej |
| `GET /integrations/` (list) | `get_rls_db` | Ja |
| `POST /systems/{id}/gdpr` | `get_db` | Nej |
| `POST /systems/{id}/contracts` | `get_db` | Nej |
| `GET /reports/*` | `get_db` | Nej -- cross-org utan skydd |
| `GET /audit/*` | `get_db` | Nej -- visar alla orgs |

**Alla skrivoperationer saknar RLS.**

#### 2.1.3 Cirkullara imports
Inga. Audit-modulen importerar modeller lazy. Rent.

#### 2.1.4 Databassessioner
`get_db()` anvander async context manager med try/commit/except rollback/finally close. Korrekt.

Problem:
- Felaktig typehint: `async def get_db() -> AsyncSession:` borde vara `AsyncGenerator[AsyncSession, None]`
- Auto-commit efter varje request (aven read-only endpoints)

#### 2.1.5 REST-konventioner -- inkonsekvent URL-struktur

| Resurs | Create/List | Update/Delete |
|--------|-------------|---------------|
| systems | `/systems/` + `/systems/{id}` | `/systems/{id}` |
| classifications | `/systems/{id}/classifications` | Saknas |
| owners | `/systems/{id}/owners` | `/owners/{id}` (bryter nesting!) |
| gdpr | `/systems/{id}/gdpr` | `/gdpr/{id}` (bryter nesting!) |
| contracts | `/systems/{id}/contracts` | `/contracts/{id}` (bryter nesting!) |
| integrations | `/integrations/` | `/integrations/{id}` |

Owners har dessutom redundant delete: bade `/owners/{id}` OCH `/systems/{id}/owners/{id}`.

#### 2.1.6 Business logic i route-handlers
`app/services/__init__.py` ar tom. All logik ligger direkt i route-handlers:
- `notifications.py`: 6 separata DB-querys
- `imports.py`: Parsning, validering, dedup blandat med handler
- `reports.py`: Helpers lever i API-modulen
- `classifications.py`: Auto-flaggar `has_elevated_protection` i endpoint

#### 2.1.7 Pydantic-schemas
- `SystemUpdate`, `OwnerUpdate`, `GDPRTreatmentUpdate`, `ContractUpdate`, `IntegrationUpdate` saknar `SafeStringMixin`
- `ClassificationCreate` saknar ocksa `SafeStringMixin`
- `PaginatedResponse.items: list` -- otypad, borde vara `list[SystemResponse]`

#### 2.1.8 Nullable-falt -- drift
- `System.criticality`: SQLAlchemy NOT NULL, migration nullable=True
- `System.lifecycle_status`: Samma drift

#### 2.1.9 N+1 query-problem
Mestadels korrekt med `selectinload`. Saknas: Contract-query i notifications laddar inte systemnamn.

#### 2.1.10 Audit trail -- brister
- `changed_by` och `ip_address` alltid None (auth saknas)
- `_AUDITED_TABLES` saknar `gdpr_treatments`, `contracts`, `system_integrations`
- `delete_system` anvander ra SQL DELETE -- triggar inte audit-listener

#### 2.1.11 Sakerhetsbrister
- `ProxyHeadersMiddleware` med `trusted_hosts="*"` -- accepterar X-Forwarded-For fran alla
- `extended_search` ILIKE utan escapning av `%` och `_` wildcards
- FK-violation vid create_system lacker som 500 istallet for 422

#### 2.1.12 onupdate=func.now() problem
`updated_at` anvander `onupdate=func.now()` som inte alltid fungerar med async SQLAlchemy. Battre: PostgreSQL trigger eller explicit sattning.

### 2.2 Datamodell

#### 2.2.1 SQLAlchemy vs Alembic drift
| Kolumn | SQLAlchemy | Migration 0000 |
|--------|-----------|----------------|
| `systems.criticality` | NOT NULL | `nullable=True` |
| `systems.lifecycle_status` | NOT NULL | `nullable=True` |

#### 2.2.2 Foreign keys och constraints
Korrekt. Alla barn har `ondelete="CASCADE"`.
Problem: `Organization.parent_org_id` FK saknar `ondelete` -- dangling references.

#### 2.2.3 Enum-typer
Migration 0004 downgrade skapar `integration_criticality` med felaktiga varden.

#### 2.2.4 UUID-hantering
Konsekvent.

#### 2.2.5 Index
Rimliga. Saknar index pa `Organization.parent_org_id`.

#### 2.2.6 Schema-inkonsistenser
- `ClassificationCreate.system_id` satts bade fran body och URL-path (path tar over)
- `OwnerCreate.system_id` -- samma problem
- Oanvanda scheman: `NIS2ReportResponse`, `ComplianceGapResponse` etc.
- `SystemUpdate` kan nollstalla required fields (name=null via PATCH)

#### 2.2.7 CLAUDE.md vs implementation
| CLAUDE.md sager | Verklighet |
|-----------------|-----------|
| `compliance_status` tabell | Existerar inte |
| `system_owners.user_id (nullable)` | Finns inte |
| `gdpr_treatments.treats_personal_data` | Ligger pa System |
| `gdpr_treatments.dpia_status` | Heter `dpia_conducted` (bool) |

### 2.3 Frontend

#### 2.3.1 API-anrop vs backend -- KRITISKT

**DashboardPage duplicerar API-funktioner**: Egna `getSystemStats()` och `getOrganizations()` med raw `fetch()` trots att `lib/api.ts` har samma med axios. Dashboardens lokala `SystemStats`-interface har **andra faltnamn** an `types/index.ts`.

**Kritikalitets-etiketter mismatchar**: Dashboard `hog`/`lag`/`aktiv`/`avveckling` vs backend `hög`/`låg`/`i_drift`/`under_avveckling`.

**Raw fetch() pa 4 stallen**: DashboardPage, App.tsx (NotificationBell), SystemDetailPage (AuditTimeline), ReportsPage.

#### 2.3.2 Laddnings- och feltillstand
Generellt bra. Inga retry-knappar. GDPR/Avtal-tabbar har bara `<p>Laddar...</p>`.

#### 2.3.3 Hardkodade URL:er
4 stallen med hardkodad `/api/v1` istallet for centrala axios-instansen.

#### 2.3.4 Duplicerad kod -- ALLVARLIGT

**Etiketter duplicerade i 5+ filer:**
`categoryLabels`, `lifecycleLabels`, `criticalityLabels` i SystemsPage, SystemFormPage, SystemDetailPage, IntegrationDialog, DependenciesPage.

**FormField duplicerad 4 ganger:**
Bara `components/FormField.tsx` har korrekt label-input-koppling (useId). De tre lokala kopiorna saknar htmlFor.

**`integrationTypeLabels` i 3 filer.**

#### 2.3.5 State management
- `OrganizationsPage.getSystemCount()` soker i query-cache med nyckel som aldrig matchar -- returnerar alltid 0.
- Inget centraliserat error-handling (global axios interceptor).

---

## 3. UX-granskning (Nielsens 10 heuristiker)

| # | Komponent | Fil | Heuristik | Allv. | Problem | Atgard |
|---|-----------|-----|-----------|-------|---------|--------|
| 1 | DashboardPage | DashboardPage.tsx | H2 System/verklighet | 3 | Kritikalitets/livscykel-nycklar mismatchar backend-enums. KPI visar felaktiga varden. | Centraliserade enum-etiketter |
| 2 | OrganizationsPage | OrganizationsPage.tsx | H5 Forebygga fel | 3 | Raderingsdialog visar alltid "0 system" (getSystemCount returnerar 0). Falskt saker. | Fixa med korrekt API-anrop |
| 3 | SystemFormPage | SystemFormPage.tsx | H9 Felaterhamtning | 2 | `apiError` satts aldrig trots JSX kontrollerar den | Satt apiError vid generella fel |
| 4 | SystemFormPage | SystemFormPage.tsx | H5 Forebygga fel | 2 | Validering bara vid submit, ingen realtidsvalidering | onBlur-validering |
| 5 | DashboardPage | DashboardPage.tsx | H4 Konsekvens | 2 | Egna fetch()-anrop vs axios i alla andra sidor | Migrera till centrala API |
| 6 | ImportPage | ImportPage.tsx | H1 Synlighet | 2 | Ingen progress under import av stora filer | Progress bar |
| 7 | ReportsPage | ReportsPage.tsx | H1 Synlighet | 2 | window.open() ingen feedback, fel = tom flik | Fetch + blob-nedladdning |
| 8 | DependenciesPage | DependenciesPage.tsx | H7 Flexibilitet | 2 | SVG fast 800x560, ingen zoom/panorering | d3-force + zoom |
| 9 | OrganizationsPage | OrganizationsPage.tsx | H3 Kontroll/frihet | 2 | Redigering behaller ibland gamla varden | Korrigera resetForm |
| 10 | DependenciesPage | DependenciesPage.tsx | H5 Forebygga fel | 2 | limit: 500 for systemnamn-map. Skalas inte. | Server-side-namn |
| 11 | Alla sidor | Alla | H10 Hjalp/dok | 2 | Inga tooltips for facktermer (undantag: SystemFormPage) | Tooltips |
| 12 | SystemsPage | SystemsPage.tsx | H1 Synlighet | 1 | Ingen resultatsammanfattning vid sokning | "X resultat" |
| 13 | SystemsPage | SystemsPage.tsx | H6 Igenkanning | 1 | Klickbara rader utan visuellt affordance | Hover-styling |
| 14 | NotificationsPage | NotificationsPage.tsx | H4 Konsekvens | 1 | Statistikkort kollapsar inte pa smala skarmar | Responsiv grid |
| 15 | SystemDetailPage | SystemDetailPage.tsx | H8 Estetik | 1 | 8 flikar trangt pa mobil | Overflow-scroll |
| 16 | AuditPage | AuditPage.tsx | H6 Igenkanning | 1 | Expanderbara rader bara liten chevron | "Visa detaljer"-text |
| 17 | SystemFormPage | SystemFormPage.tsx | H8 Estetik | 1 | 6 sektioner = mycket scrollning | Wizard/steg |

---

## 4. Testanalys

### 4.1 Backend-tester

| # | Fil | Antal | Testar | Status |
|---|-----|-------|--------|--------|
| 1 | test_health.py | 5 | GET /health | OK |
| 2 | test_organizations.py | 19 | CRUD, enum, parent-child, 404, 409 | OK |
| 3 | test_systems.py | 28 | CRUD, filter, sok, stats, JSONB | OK |
| 4 | test_classifications.py | 15 | Create, list, latest, boundary 0-4 | OK |
| 5 | test_owners.py | 17 | CRUD, alla 6 roller, duplikat | OK |
| 6 | test_integrations.py | 15 | CRUD, filter, system-scoped | OK |
| 7 | test_integrations_advanced.py | 23 | Alla typer, cross-org, kaskad | OK |
| 8 | test_gdpr.py | 32 | CRUD, alla statuser, DPIA | OK |
| 9 | test_contracts.py | 20 | CRUD, expiring, boundary | OK |
| 10 | test_reports.py | 13 | NIS2 JSON/XLSX, compliance-gap | OK |
| 11 | test_export.py | 25 | JSON/CSV/XLSX, org-filter, unicode | OK |
| 12 | test_import.py | 34 | JSON/CSV/XLSX, dubbletter, 100-rad | OK |
| 13 | test_audit.py | 26 | Audit trail, filter, pagination | Delvis felaktiga (se 4.2) |
| 14 | test_notifications.py | 23 | Alla typer, severity, summering | OK |
| 15 | test_rls.py | 25 | Multi-org isolering, 3-org-test | Delvis felaktiga (se 4.2) |
| 16 | test_security.py | 35 | SQLi, XSS, path traversal | OK |
| 17 | test_systems_search.py | 28 | ILIKE, aliases, product_name | OK |
| 18 | test_search_advanced.py | 31 | extended_attributes, hosting_model | OK |
| 19 | test_negative.py | 41 | Felaktig input, saknade falt | OK |
| 20 | test_validation.py | 77 | Schema-validering, boundary | OK |
| 21 | test_crud_flows.py | 43 | E2E CRUD | OK |
| 22 | test_compliance.py | 64 | NIS2/GDPR/MSB compliance-gap | OK |
| 23 | test_regression.py | 15 | Regressionstester | OK |
| 24 | test_performance.py | 22 | 50/100 system, paginering | OK |
| 25 | test_performance_stress.py | 74 | 200+ system, stress | OK |
| 26 | test_edge_cases_security.py | 86 | Extrema varden, specialtecken | OK |
| 27 | test_kravspec_category1_6.py | 67 | Kravspec kat 1-6 | OK |
| 28 | test_kravspec_category7_12.py | 110 | Kravspec kat 7-12 | OK |
| 29 | test_multiorg_security.py | 81 | Multi-org, RLS | OK |
| 30 | test_workflows_e2e.py | 110 | E2E workflows | OK |
| 31 | test_data_quality_compliance.py | 196 | Datakvalitet, integritet | OK |

### 4.2 Felaktiga tester

| # | Test | Problem | Typ |
|---|------|---------|-----|
| 1 | test_notifications: `test_notifications_total_matches_list_length` | Felmeddelande refererar `body["notifications"]` som inte finns (KeyError vid fail) | Felmeddelande |
| 2 | test_import: `test_import_classifications_basic` | Skickar `system_id` men endpoint forvanter `system_name`. Accepterar alla felkoder som pass. | Testar fel sak |
| 3 | test_import: `test_import_owners_basic` | Samma: skickar `system_id`/`organization_id` istallet for `system_name`. | Testar fel sak |
| 4 | test_audit: `test_audit_update_creates_update_entry` | Hamtar audit-poster men assertar aldrig att update-entry finns. No-op. | Testar inget |
| 5 | test_audit: `test_audit_delete_creates_delete_entry` | Samma: assertar aldrig. Dessutom: delete_system anvander ra SQL sa audit aldrig triggas. | Testar inget |
| 6 | test_audit: `test_audit_contract_create_logged` | Forvanter audit for contracts men `_AUDITED_TABLES` inkluderar inte contracts. Passerar pa att endpoint returnerar tom lista. | Felaktigt antagande |
| 7 | test_audit: `test_audit_gdpr_create_logged` | Samma: gdpr_treatments saknas i `_AUDITED_TABLES`. | Felaktigt antagande |
| 8 | test_rls: `test_rls_owners_isolated_between_orgs` | Testar system_id-filtrering, inte RLS-isolering. | Testar fel sak |
| 9 | test_contracts: `test_contract_end_before_start_rejected_or_accepted` | Dokumenterar att ogiltig data accepteras -- ingen validering finns. | Saknad validering |
| 10 | test_systems: `test_create_system_invalid_org` | FK-violation lackers som 500 -- testet normaliserar bugg. | Felaktigt antagande |

### 4.3 Saknad testtackning

**Backend:**
- `/api/v1/reports/nis2.html` -- saknar dedikerad test
- `/api/v1/reports/compliance-gap.pdf` -- enbart JSON testas
- Concurrent writes
- `extended_search` query-parameter
- Import klassningar med ogiltiga varden (confidentiality=5)
- `contract_end < contract_start` validering

**Frontend -- komponenter utan tester:**
- NotificationsPage
- OrganizationsPage
- AuditPage
- Breadcrumb
- FormField (centrala)
- App.tsx (routing, layout)
- useBlocker-beteende
- Tangentbordsnavigering
- Mobil-layout

### 4.4 Testinfrastruktur

**Backend:**
- Transaktionell rollback per test (bra isolering)
- Session-scoped engine
- RLS-stod i conftest (men med NULL-bypass som skiljer fran prod)
- Fabriksfunktioner for alla entiteter
- Problem: Test-DB hardkodad till `db:5432` (Docker-host)
- Duplicerade helpers: `create_org`/`create_system` per testfil trots factories.py

**Frontend:**
- MSW med `setupServer()`, `resetHandlers()` -- korrekt
- Polyfills for ResizeObserver, matchMedia, scrollIntoView, hasPointerCapture
- Testdata per fil -- ingen delad fixture-fil
- Konsekvent render-helpers per svit

---

## 5. Tillganglighet (WCAG 2.1 AA)

| # | Problem | Allv. | Filer |
|---|---------|-------|-------|
| A1 | 40+ formularfalt saknar label-input-koppling (htmlFor/id) | 3 | SystemFormPage, SystemDetailPage, IntegrationDialog |
| A2 | Tabellrader i SystemsPage klickbara utan tabIndex/onKeyDown | 2 | SystemsPage.tsx |
| A3 | AuditPage expanderbara rader saknar aria-expanded | 2 | AuditPage.tsx |
| A4 | DependenciesPage SVG-graf saknar role="img" och aria-label | 2 | DependenciesPage.tsx |
| A5 | ImportPage drop-zone saknar role="button" | 2 | ImportPage.tsx |
| A6 | DashboardPage org-filter saknar kopplad label | 1 | DashboardPage.tsx |

---

## 6. Refactoring-plan (prioritetsordning)

### P1 -- Maste fixas (bryter funktionalitet / sakerhet)

| # | Beskrivning | Filer | Insats | Beroenden |
|---|-------------|-------|--------|-----------|
| P1.1 | **RLS-policy drift**: Migration 0001 saknar NULL-bypass, conftest har den. Prod blockerar all data om auth saknas. Fixa migration ELLER lagg till auth-context. | migration 0001, conftest.py | M | - |
| P1.2 | **Alla skriv-endpoints saknar RLS**: POST/PATCH/DELETE anvander `get_db` istf `get_rls_db`. En anvandare kan mutate cross-org. | `app/api/*.py` | M | P1.1 |
| P1.3 | **Drift SQLAlchemy vs migration**: `systems.criticality` och `lifecycle_status` NOT NULL i modell, nullable i DB. | models.py, ny migration | S | - |
| P1.4 | **Update-schemas saknar SafeStringMixin**: `SystemUpdate`, `OwnerUpdate`, `GDPRTreatmentUpdate`, `ContractUpdate`, `IntegrationUpdate`, `ClassificationCreate`. Null bytes passerar. | `app/schemas/__init__.py` | S | - |
| P1.5 | **delete_system anvander ra SQL**: Triggar inte audit-listener. System-deletion loggas inte. | `app/api/systems.py` | S | - |
| P1.6 | **DashboardPage enum-mismatch**: `hog`/`lag`/`aktiv`/`avveckling` vs backend `hög`/`låg`/`i_drift`/`under_avveckling`. KPI visar felaktiga varden. | DashboardPage.tsx, types/index.ts | S | - |
| P1.7 | **OrganizationsPage getSystemCount returnerar 0**: Raderingsdialog ger felaktig feedback. | OrganizationsPage.tsx | S | - |
| P1.8 | **SystemFormPage apiError satts aldrig**: JSX visar `apiError` men satts aldrig. | SystemFormPage.tsx | S | - |
| P1.9 | **FK-violation vid create_system**: Lackers som 500 istallet for 422. | `app/api/systems.py` | S | - |
| P1.10 | **ProxyHeadersMiddleware trusted_hosts="*"**: Accepterar X-Forwarded-For fran alla. | `app/main.py` | S | - |

### P2 -- Bor fixas (datakvalitet, kodkvalitet, anvandbarhet)

| # | Beskrivning | Filer | Insats | Beroenden |
|---|-------------|-------|--------|-----------|
| P2.1 | **Affarslogik i route-handlers**: Skapa services/ for notifications, imports, reports | `app/api/*.py`, ny `app/services/` | L | - |
| P2.2 | **Inkonsekvent URL-struktur** for sub-resurser (owners, gdpr, contracts) | `app/api/owners.py`, `gdpr.py`, `contracts.py` | M | - |
| P2.3 | **Redundant delete-endpoint** for owners | `app/api/owners.py` | S | P2.2 |
| P2.4 | **Audit-tabeller ofullstandiga**: Saknar gdpr_treatments, contracts, system_integrations | `app/api/audit.py` | S | - |
| P2.5 | **Trasig downgrade migration 0004** | `alembic/versions/0004_*.py` | S | - |
| P2.6 | **ILIKE utan wildcard-escapning** i extended_search | `app/api/systems.py` | S | - |
| P2.7 | **Duplicerade API-anrop**: DashboardPage, NotificationBell, AuditTimeline anvander raw fetch() | 4 frontend-filer | M | P1.6 |
| P2.8 | **Duplicerade etiketter i 5+ filer**: Centralisera till `lib/labels.ts` | 5+ frontend-filer | M | - |
| P2.9 | **FormField duplicerad 4x**: Bara centrala har htmlFor. Migrera alla formular. | SystemFormPage, SystemDetailPage, IntegrationDialog | M | - |
| P2.10 | **DependenciesPage lokala typer med unsafe casting** | DependenciesPage.tsx | S | P2.8 |
| P2.11 | **Saknade frontend-tester**: 5 sidor + 2 komponenter saknar | `__tests__/` | L | - |
| P2.12 | **Tillganglighet: 40+ falt utan label-koppling** | Alla formularsidor | M | P2.9 |
| P2.13 | **Tabellrader inte tangentbordsarbara** | SystemsPage, AuditPage | S | - |
| P2.14 | **Felaktiga backend-tester** (10 st): Se sektion 4.2 | Diverse testfiler | M | - |
| P2.15 | **Test-DB hardkodad** till Docker-host `db:5432` | tests/conftest.py | S | - |
| P2.16 | **audit/notifications responses** handkodade dict utan Pydantic schema | `app/api/audit.py`, `notifications.py` | M | - |
| P2.17 | **contract_end < contract_start** accepteras utan validering | `app/schemas/__init__.py` | S | - |
| P2.18 | **ReportsPage hardkodad API_BASE** | ReportsPage.tsx | S | - |
| P2.19 | **ClassificationCreate/OwnerCreate.system_id** satts bade fran body och URL | `app/schemas/__init__.py` | S | - |

### P3 -- Kan fixas (polish, optimering)

| # | Beskrivning | Filer | Insats | Beroenden |
|---|-------------|-------|--------|-----------|
| P3.1 | **Organization.parent_org_id** saknar ondelete | models.py, ny migration | S | - |
| P3.2 | **Organization saknar index** pa parent_org_id | models.py, ny migration | S | - |
| P3.3 | **Onodiga dependencies**: python-jose, passlib, psycopg2-binary | pyproject.toml | S | - |
| P3.4 | **Dubbla dependency-grupper** i pyproject.toml | pyproject.toml | S | - |
| P3.5 | **Wildcard import** i models/__init__.py | models/__init__.py | S | - |
| P3.6 | **Notifications pagineras i minnet** | notifications.py | M | P2.1 |
| P3.7 | **Export utan storleksbegransning** | export.py | M | - |
| P3.8 | **Import owners validerar inte tom name** | imports.py | S | - |
| P3.9 | **SVG-graf saknar tillganglighet** | DependenciesPage.tsx | S | - |
| P3.10 | **ImportPage drop-zone saknar role** | ImportPage.tsx | S | - |
| P3.11 | **DependenciesPage limit: 500 skalas inte** | DependenciesPage.tsx | M | - |
| P3.12 | **Ingen retry-knapp vid API-fel** | Alla sidor | M | - |
| P3.13 | **PaginatedResponse.items otypad** | schemas/__init__.py | S | - |
| P3.14 | **Oanvanda scheman**: NIS2ReportResponse m.fl. | schemas/__init__.py | S | - |
| P3.15 | **datetime.utcnow() deprecated** | reports.py | S | - |
| P3.16 | **Duplicerade test-helpers**: create_org/create_system per fil trots factories.py | Alla testfiler | M | - |
| P3.17 | **Dockerfile.dev felaktigt uv-kommando** | Dockerfile.dev | S | - |
| P3.18 | **CLAUDE.md vs implementation drift** (se 2.2.7) | CLAUDE.md | S | - |

---

## Sammanfattning

| Prioritet | Antal | Fordelning |
|-----------|-------|-----------|
| P1 (maste) | 10 | 7S + 2M + 0L |
| P2 (bor) | 19 | 7S + 7M + 2L |
| P3 (kan) | 18 | 11S + 4M + 0L |
| **Totalt** | **47** | |

### Topp 5 allvarligaste problem
1. **RLS-bypass pa alla skrivoperationer** (P1.1, P1.2) -- cross-org data-manipulation
2. **delete_system loggas inte** (P1.5) -- audit trail bruten
3. **DashboardPage visar felaktiga KPI:er** (P1.6) -- anvandare ser fel data
4. **Raderingsdialog ljuger** om kopplde system (P1.7) -- dataintegritet
5. **Null-byte-validering saknas** pa Update-schemas (P1.4) -- sarbarhetsyta
