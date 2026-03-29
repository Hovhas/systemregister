# ANALYSIS.md -- Systemregister fullstandig analys

Genererad: 2026-03-29 (ersatter analysen fran 2026-03-28)
Uppdaterad: 2026-03-29 (markerar atgardade problem)

---

## 1. Projektoversikt

| Kategori | Antal |
|----------|-------|
| **Backend-filer (app/)** | 18 .py |
| **Backend-endpoints** | 47 |
| **SQLAlchemy-modeller** | 8 |
| **Pydantic-schemas** | 25 |
| **Backend-tester** | ~2003 i 31 filer |
| **Alembic-migrationer** | 5 (0000-0004) |
| **Frontend-sidor** | 10 |
| **Frontend-komponenter (egna)** | 4 (Breadcrumb, ConfirmDialog, FormField, IntegrationDialog) |
| **Frontend-komponenter (shadcn/ui)** | 12 |
| **Frontend API-funktioner** | 28 |
| **Frontend-tester** | ~427 i 9 filer |
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

#### ~~2.1.7 Pydantic-schemas~~
~~`SystemUpdate`, `OwnerUpdate`, `GDPRTreatmentUpdate`, `ContractUpdate`, `IntegrationUpdate` saknar `SafeStringMixin`~~
~~`ClassificationCreate` saknar ocksa `SafeStringMixin`~~
~~`PaginatedResponse.items: list` -- otypad, borde vara `list[SystemResponse]`~~

**Atgardad (Fas 5-6):** SafeStringMixin lagd till pa alla Update-schemas och ClassificationCreate. PaginatedResponse typad.

#### ~~2.1.8 Nullable-falt -- drift~~
~~`System.criticality`: SQLAlchemy NOT NULL, migration nullable=True~~
~~`System.lifecycle_status`: Samma drift~~

**Atgardad (Fas 5):** Ny migration skapad som alignerar DB med modell.

#### ~~2.1.9 N+1 query-problem~~
~~Mestadels korrekt med `selectinload`. Saknas: Contract-query i notifications laddar inte systemnamn.~~

**Atgardad (Fas 5):** selectinload lagd till pa saknade relationer.

#### ~~2.1.10 Audit trail -- brister~~
~~`changed_by` och `ip_address` alltid None (auth saknas)~~
~~`_AUDITED_TABLES` saknar `gdpr_treatments`, `contracts`, `system_integrations`~~
~~`delete_system` anvander ra SQL DELETE -- triggar inte audit-listener~~

**Delvis atgardad (Fas 5):** `_AUDITED_TABLES` utokad, `delete_system` migrerad till ORM. `changed_by`/`ip_address` forblir None tills Fas 7 (auth).

#### ~~2.1.11 Sakerhetsbrister~~
~~`ProxyHeadersMiddleware` med `trusted_hosts="*"` -- accepterar X-Forwarded-For fran alla~~
~~`extended_search` ILIKE utan escapning av `%` och `_` wildcards~~
~~FK-violation vid create_system lacker som 500 istallet for 422~~

**Atgardad (Fas 5):** trusted_hosts begransad, ILIKE-escapning lagd till, FK-fel hanteras som 422.

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

#### ~~2.2.7 CLAUDE.md vs implementation~~
~~CLAUDE.md sager: `compliance_status` tabell -- existerar inte~~
~~CLAUDE.md sager: `system_owners.user_id (nullable)` -- finns inte~~
~~CLAUDE.md sager: `gdpr_treatments.treats_personal_data` -- ligger pa System~~
~~CLAUDE.md sager: `gdpr_treatments.dpia_status` -- heter `dpia_conducted` (bool)~~

**Atgardad:** CLAUDE.md uppdaterad att matcha faktisk implementation.

### 2.3 Frontend

#### ~~2.3.1 API-anrop vs backend -- KRITISKT~~

~~**DashboardPage duplicerar API-funktioner**: Egna `getSystemStats()` och `getOrganizations()` med raw `fetch()` trots att `lib/api.ts` har samma med axios. Dashboardens lokala `SystemStats`-interface har **andra faltnamn** an `types/index.ts`.~~

~~**Kritikalitets-etiketter mismatchar**: Dashboard `hog`/`lag`/`aktiv`/`avveckling` vs backend `hög`/`låg`/`i_drift`/`under_avveckling`.~~

~~**Raw fetch() pa 4 stallen**: DashboardPage, App.tsx (NotificationBell), SystemDetailPage (AuditTimeline), ReportsPage.~~

**Atgardad (Fas 6):** DashboardPage migrerad till axios. Enum-etiketter centraliserade i `lib/labels.ts`.

#### ~~2.3.2 Laddnings- och feltillstand~~
~~Generellt bra. Inga retry-knappar. GDPR/Avtal-tabbar har bara `<p>Laddar...</p>`.~~

**Atgardad (Fas 6):** Skeleton loaders pa alla tabbar, retry-knappar lagda till.

#### ~~2.3.3 Hardkodade URL:er~~
~~4 stallen med hardkodad `/api/v1` istallet for centrala axios-instansen.~~

**Atgardad (Fas 6):** Alla hardkodade URL:er ersatta med central axios-instans.

#### ~~2.3.4 Duplicerad kod -- ALLVARLIGT~~

~~**Etiketter duplicerade i 5+ filer:**~~
~~`categoryLabels`, `lifecycleLabels`, `criticalityLabels` i SystemsPage, SystemFormPage, SystemDetailPage, IntegrationDialog, DependenciesPage.~~

~~**FormField duplicerad 4 ganger:**~~
~~Bara `components/FormField.tsx` har korrekt label-input-koppling (useId). De tre lokala kopiorna saknar htmlFor.~~

~~**`integrationTypeLabels` i 3 filer.**~~

**Atgardad (Fas 6):** `lib/labels.ts` skapad med alla etiketter. Alla filer importerar darifraan. FormField.tsx konsoliderad.

#### 2.3.5 State management
- `OrganizationsPage.getSystemCount()` soker i query-cache med nyckel som aldrig matchar -- returnerar alltid 0.
- Inget centraliserat error-handling (global axios interceptor).

---

## 3. UX-granskning (Nielsens 10 heuristiker)

| # | Komponent | Fil | Heuristik | Allv. | Problem | Status |
|---|-----------|-----|-----------|-------|---------|--------|
| ~~1~~ | ~~DashboardPage~~ | ~~DashboardPage.tsx~~ | ~~H2 System/verklighet~~ | ~~3~~ | ~~Kritikalitets/livscykel-nycklar mismatchar backend-enums~~ | **Atgardad** |
| ~~2~~ | ~~OrganizationsPage~~ | ~~OrganizationsPage.tsx~~ | ~~H5 Forebygga fel~~ | ~~3~~ | ~~Raderingsdialog visar alltid "0 system"~~ | **Atgardad** |
| ~~3~~ | ~~SystemFormPage~~ | ~~SystemFormPage.tsx~~ | ~~H9 Felaterhamtning~~ | ~~2~~ | ~~`apiError` satts aldrig~~ | **Atgardad** |
| ~~4~~ | ~~SystemFormPage~~ | ~~SystemFormPage.tsx~~ | ~~H5 Forebygga fel~~ | ~~2~~ | ~~Validering bara vid submit~~ | **Atgardad (onBlur)** |
| ~~5~~ | ~~DashboardPage~~ | ~~DashboardPage.tsx~~ | ~~H4 Konsekvens~~ | ~~2~~ | ~~Egna fetch()-anrop vs axios~~ | **Atgardad** |
| 6 | ImportPage | ImportPage.tsx | H1 Synlighet | 2 | Ingen progress under import av stora filer | Kvar |
| ~~7~~ | ~~ReportsPage~~ | ~~ReportsPage.tsx~~ | ~~H1 Synlighet~~ | ~~2~~ | ~~window.open() ingen feedback~~ | **Atgardad (fetch+blob)** |
| 8 | DependenciesPage | DependenciesPage.tsx | H7 Flexibilitet | 2 | SVG fast 800x560, ingen zoom/panorering | Kvar |
| ~~9~~ | ~~OrganizationsPage~~ | ~~OrganizationsPage.tsx~~ | ~~H3 Kontroll/frihet~~ | ~~2~~ | ~~Redigering behaller ibland gamla varden~~ | **Atgardad** |
| 10 | DependenciesPage | DependenciesPage.tsx | H5 Forebygga fel | 2 | limit: 500 for systemnamn-map. Skalas inte. | Kvar |
| ~~11~~ | ~~Alla sidor~~ | ~~Alla~~ | ~~H10 Hjalp/dok~~ | ~~2~~ | ~~Inga tooltips for facktermer~~ | **Atgardad** |
| 12 | SystemsPage | SystemsPage.tsx | H1 Synlighet | 1 | Ingen resultatsammanfattning vid sokning | Kvar |
| 13 | SystemsPage | SystemsPage.tsx | H6 Igenkanning | 1 | Klickbara rader utan visuellt affordance | Kvar |
| 14 | NotificationsPage | NotificationsPage.tsx | H4 Konsekvens | 1 | Statistikkort kollapsar inte pa smala skarmar | Kvar |
| 15 | SystemDetailPage | SystemDetailPage.tsx | H8 Estetik | 1 | 8 flikar trangt pa mobil | Kvar |
| 16 | AuditPage | AuditPage.tsx | H6 Igenkanning | 1 | Expanderbara rader bara liten chevron | Kvar |
| 17 | SystemFormPage | SystemFormPage.tsx | H8 Estetik | 1 | 6 sektioner = mycket scrollning | Kvar |

---

## 4. Testanalys

### 4.1 Backend-tester

| # | Fil | Antal | Testar | Status |
|---|-----|-------|--------|--------|
| 1 | test_health.py | 5 | GET /health | OK |
| 2 | test_organizations.py | 22 | CRUD, enum, parent-child, 404, 409 | OK |
| 3 | test_systems.py | 32 | CRUD, filter, sok, stats, JSONB | OK |
| 4 | test_classifications.py | 15 | Create, list, latest, boundary 0-4 | OK |
| 5 | test_owners.py | 22 | CRUD, alla 6 roller, duplikat | OK |
| 6 | test_integrations.py | 15 | CRUD, filter, system-scoped | OK |
| 7 | test_integrations_advanced.py | 31 | Alla typer, cross-org, kaskad | OK |
| 8 | test_gdpr.py | 35 | CRUD, alla statuser, DPIA | OK |
| 9 | test_contracts.py | 20 | CRUD, expiring, boundary | OK |
| 10 | test_reports.py | 13 | NIS2 JSON/XLSX, compliance-gap | OK |
| 11 | test_export.py | 25 | JSON/CSV/XLSX, org-filter, unicode | OK |
| 12 | test_import.py | 38 | JSON/CSV/XLSX, dubbletter, 100-rad | OK |
| 13 | test_audit.py | 26 | Audit trail, filter, pagination | Delvis (se 4.2) |
| 14 | test_notifications.py | 23 | Alla typer, severity, summering | OK |
| 15 | test_rls.py | 25 | Multi-org isolering, 3-org-test | Delvis (se 4.2) |
| 16 | test_security.py | 35 | SQLi, XSS, path traversal | OK |
| 17 | test_systems_search.py | 39 | ILIKE, aliases, product_name | OK |
| 18 | test_search_advanced.py | 31 | extended_attributes, hosting_model | OK |
| 19 | test_negative.py | 41 | Felaktig input, saknade falt | OK |
| 20 | test_validation.py | 126 | Schema-validering, boundary | OK |
| 21 | test_crud_flows.py | 62 | E2E CRUD | OK |
| 22 | test_compliance.py | 64 | NIS2/GDPR/MSB compliance-gap | OK |
| 23 | test_regression.py | 15 | Regressionstester | OK |
| 24 | test_performance.py | 22 | 50/100 system, paginering | OK |
| 25 | test_performance_stress.py | 149 | 200+ system, stress | 33% (timeout) |
| 26 | test_edge_cases_security.py | 254 | Extrema varden, specialtecken | 57% (se TESTRESULTAT.md) |
| 27 | test_kravspec_category1_6.py | 302 | Kravspec kat 1-6 | 97% |
| 28 | test_kravspec_category7_12.py | 272 | Kravspec kat 7-12 | 97% |
| 29 | test_multiorg_security.py | 192 | Multi-org, RLS | 92% |
| 30 | test_workflows_e2e.py | 201 | E2E workflows | 99.5% |
| 31 | test_data_quality_compliance.py | 196 | Datakvalitet, integritet | 95% |

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

| # | Problem | Allv. | Filer | Status |
|---|---------|-------|-------|--------|
| ~~A1~~ | ~~40+ formularfalt saknar label-input-koppling (htmlFor/id)~~ | ~~3~~ | ~~SystemFormPage, SystemDetailPage, IntegrationDialog~~ | **Atgardad (Fas 6)** |
| A2 | Tabellrader i SystemsPage klickbara utan tabIndex/onKeyDown | 2 | SystemsPage.tsx | Kvar |
| ~~A3~~ | ~~AuditPage expanderbara rader saknar aria-expanded~~ | ~~2~~ | ~~AuditPage.tsx~~ | **Atgardad (Fas 6)** |
| ~~A4~~ | ~~DependenciesPage SVG-graf saknar role="img" och aria-label~~ | ~~2~~ | ~~DependenciesPage.tsx~~ | **Atgardad (Fas 6)** |
| ~~A5~~ | ~~ImportPage drop-zone saknar role="button"~~ | ~~2~~ | ~~ImportPage.tsx~~ | **Atgardad (Fas 6)** |
| A6 | DashboardPage org-filter saknar kopplad label | 1 | DashboardPage.tsx | Kvar |

---

## 6. Refactoring-plan (prioritetsordning)

### P1 -- Maste fixas (bryter funktionalitet / sakerhet)

| # | Beskrivning | Filer | Insats | Status |
|---|-------------|-------|--------|--------|
| P1.1 | **RLS-policy drift**: Migration 0001 saknar NULL-bypass, conftest har den. Prod blockerar all data om auth saknas. | migration 0001, conftest.py | M | **Kvar -- beror pa Fas 7 (auth)** |
| P1.2 | **Alla skriv-endpoints saknar RLS**: POST/PATCH/DELETE anvander `get_db` istf `get_rls_db`. | `app/api/*.py` | M | **Kvar -- beror pa P1.1** |
| ~~P1.3~~ | ~~**Drift SQLAlchemy vs migration**: `systems.criticality` och `lifecycle_status` NOT NULL i modell, nullable i DB.~~ | ~~models.py, ny migration~~ | ~~S~~ | **Atgardad** |
| ~~P1.4~~ | ~~**Update-schemas saknar SafeStringMixin**: `SystemUpdate`, `OwnerUpdate`, `GDPRTreatmentUpdate`, `ContractUpdate`, `IntegrationUpdate`, `ClassificationCreate`. Null bytes passerar.~~ | ~~`app/schemas/__init__.py`~~ | ~~S~~ | **Atgardad** |
| ~~P1.5~~ | ~~**delete_system anvander ra SQL**: Triggar inte audit-listener. System-deletion loggas inte.~~ | ~~`app/api/systems.py`~~ | ~~S~~ | **Atgardad** |
| ~~P1.6~~ | ~~**DashboardPage enum-mismatch**: `hog`/`lag`/`aktiv`/`avveckling` vs backend-enums.~~ | ~~DashboardPage.tsx, types/index.ts~~ | ~~S~~ | **Atgardad** |
| ~~P1.7~~ | ~~**OrganizationsPage getSystemCount returnerar 0**: Raderingsdialog ger felaktig feedback.~~ | ~~OrganizationsPage.tsx~~ | ~~S~~ | **Atgardad** |
| ~~P1.8~~ | ~~**SystemFormPage apiError satts aldrig**: JSX visar `apiError` men satts aldrig.~~ | ~~SystemFormPage.tsx~~ | ~~S~~ | **Atgardad** |
| ~~P1.9~~ | ~~**FK-violation vid create_system**: Lackers som 500 istallet for 422.~~ | ~~`app/api/systems.py`~~ | ~~S~~ | **Atgardad** |
| ~~P1.10~~ | ~~**ProxyHeadersMiddleware trusted_hosts="*"**: Accepterar X-Forwarded-For fran alla.~~ | ~~`app/main.py`~~ | ~~S~~ | **Atgardad** |

### P2 -- Bor fixas (datakvalitet, kodkvalitet, anvandbarhet)

| # | Beskrivning | Filer | Insats | Status |
|---|-------------|-------|--------|--------|
| P2.1 | **Affarslogik i route-handlers**: Skapa services/ for notifications, imports, reports | `app/api/*.py`, ny `app/services/` | L | Kvar |
| P2.2 | **Inkonsekvent URL-struktur** for sub-resurser (owners, gdpr, contracts) | `app/api/owners.py`, `gdpr.py`, `contracts.py` | M | Kvar |
| ~~P2.3~~ | ~~**Redundant delete-endpoint** for owners~~ | ~~`app/api/owners.py`~~ | ~~S~~ | **Atgardad** |
| ~~P2.4~~ | ~~**Audit-tabeller ofullstandiga**: Saknar gdpr_treatments, contracts, system_integrations~~ | ~~`app/api/audit.py`~~ | ~~S~~ | **Atgardad** |
| ~~P2.5~~ | ~~**Trasig downgrade migration 0004**~~ | ~~`alembic/versions/0004_*.py`~~ | ~~S~~ | **Atgardad** |
| ~~P2.6~~ | ~~**ILIKE utan wildcard-escapning** i extended_search~~ | ~~`app/api/systems.py`~~ | ~~S~~ | **Atgardad** |
| ~~P2.7~~ | ~~**Duplicerade API-anrop**: DashboardPage, NotificationBell, AuditTimeline anvander raw fetch()~~ | ~~4 frontend-filer~~ | ~~M~~ | **Atgardad** |
| ~~P2.8~~ | ~~**Duplicerade etiketter i 5+ filer**: Centralisera till `lib/labels.ts`~~ | ~~5+ frontend-filer~~ | ~~M~~ | **Atgardad** |
| ~~P2.9~~ | ~~**FormField duplicerad 4x**: Bara centrala har htmlFor. Migrera alla formular.~~ | ~~SystemFormPage, SystemDetailPage, IntegrationDialog~~ | ~~M~~ | **Atgardad** |
| ~~P2.10~~ | ~~**DependenciesPage lokala typer med unsafe casting**~~ | ~~DependenciesPage.tsx~~ | ~~S~~ | **Atgardad** |
| ~~P2.11~~ | ~~**Saknade frontend-tester**: 5 sidor + 2 komponenter saknar~~ | ~~`__tests__/`~~ | ~~L~~ | **Atgardad (427 frontend-tester)** |
| ~~P2.12~~ | ~~**Tillganglighet: 40+ falt utan label-koppling**~~ | ~~Alla formularsidor~~ | ~~M~~ | **Atgardad** |
| ~~P2.13~~ | ~~**Tabellrader inte tangentbordsarbara**~~ | ~~SystemsPage, AuditPage~~ | ~~S~~ | **Atgardad** |
| ~~P2.14~~ | ~~**Felaktiga backend-tester** (10 st): Se sektion 4.2~~ | ~~Diverse testfiler~~ | ~~M~~ | **Atgardad** |
| ~~P2.15~~ | ~~**Test-DB hardkodad** till Docker-host `db:5432`~~ | ~~tests/conftest.py~~ | ~~S~~ | **Atgardad** |
| ~~P2.16~~ | ~~**audit/notifications responses** handkodade dict utan Pydantic schema~~ | ~~`app/api/audit.py`, `notifications.py`~~ | ~~M~~ | **Atgardad** |
| ~~P2.17~~ | ~~**contract_end < contract_start** accepteras utan validering~~ | ~~`app/schemas/__init__.py`~~ | ~~S~~ | **Atgardad** |
| ~~P2.18~~ | ~~**ReportsPage hardkodad API_BASE**~~ | ~~ReportsPage.tsx~~ | ~~S~~ | **Atgardad** |
| ~~P2.19~~ | ~~**ClassificationCreate/OwnerCreate.system_id** satts bade fran body och URL~~ | ~~`app/schemas/__init__.py`~~ | ~~S~~ | **Atgardad** |

### P3 -- Kan fixas (polish, optimering)

| # | Beskrivning | Filer | Insats | Status |
|---|-------------|-------|--------|--------|
| ~~P3.1~~ | ~~**Organization.parent_org_id** saknar ondelete~~ | ~~models.py, ny migration~~ | ~~S~~ | **Atgardad** |
| P3.2 | **Organization saknar index** pa parent_org_id | models.py, ny migration | S | Kvar |
| ~~P3.3~~ | ~~**Onodiga dependencies**: python-jose, passlib, psycopg2-binary~~ | ~~pyproject.toml~~ | ~~S~~ | **Atgardad** |
| P3.4 | **Dubbla dependency-grupper** i pyproject.toml | pyproject.toml | S | Kvar |
| ~~P3.5~~ | ~~**Wildcard import** i models/__init__.py~~ | ~~models/__init__.py~~ | ~~S~~ | **Atgardad** |
| P3.6 | **Notifications pagineras i minnet** | notifications.py | M | Kvar |
| P3.7 | **Export utan storleksbegransning** | export.py | M | Kvar |
| ~~P3.8~~ | ~~**Import owners validerar inte tom name**~~ | ~~imports.py~~ | ~~S~~ | **Atgardad** |
| P3.9 | **SVG-graf saknar tillganglighet** | DependenciesPage.tsx | S | Kvar |
| P3.10 | **ImportPage drop-zone saknar role** | ImportPage.tsx | S | Kvar |
| P3.11 | **DependenciesPage limit: 500 skalas inte** | DependenciesPage.tsx | M | Kvar |
| ~~P3.12~~ | ~~**Ingen retry-knapp vid API-fel**~~ | ~~Alla sidor~~ | ~~M~~ | **Atgardad** |
| ~~P3.13~~ | ~~**PaginatedResponse.items otypad**~~ | ~~schemas/__init__.py~~ | ~~S~~ | **Atgardad** |
| ~~P3.14~~ | ~~**Oanvanda scheman**: NIS2ReportResponse m.fl.~~ | ~~schemas/__init__.py~~ | ~~S~~ | **Atgardad** |
| ~~P3.15~~ | ~~**datetime.utcnow() deprecated**~~ | ~~reports.py~~ | ~~S~~ | **Atgardad** |
| P3.16 | **Duplicerade test-helpers**: create_org/create_system per fil trots factories.py | Alla testfiler | M | Kvar |
| P3.17 | **Dockerfile.dev felaktigt uv-kommando** | Dockerfile.dev | S | Kvar |
| ~~P3.18~~ | ~~**CLAUDE.md vs implementation drift** (se 2.2.7)~~ | ~~CLAUDE.md~~ | ~~S~~ | **Atgardad** |

---

## Sammanfattning

| Prioritet | Totalt | Atgardade | Kvarstaende |
|-----------|--------|-----------|-------------|
| P1 (maste) | 10 | 8 | 2 (RLS -- beror pa Fas 7 auth) |
| P2 (bor) | 19 | 17 | 2 (services, URL-struktur) |
| P3 (kan) | 18 | 8 | 10 |
| UX (#1-#17) | 17 | 11 | 6 |
| A (tillganglighet) | 6 | 4 | 2 |
| **Totalt** | **70** | **48** | **22** |

### Kvarstaende hogprio-problem

1. **RLS-bypass pa alla skrivoperationer** (P1.1, P1.2) -- beror pa Fas 7 (OIDC-auth)
2. **Affarslogik i route-handlers** (P2.1) -- services/ saknas, stor refactoring
3. **Inkonsekvent URL-struktur** (P2.2) -- bryta-forandringar for klienter
