# Säkerhet — Systemregister

## OWASP Top 10 — mappning till implementation

### A01: Broken Access Control
- **Row-Level Security (RLS):** Multi-org-isolation via `organization_id` på alla system-relaterade tabeller
- **`get_rls_db` dependency:** Alla API-endpoints använder RLS-sessioner som filtrerar per organisation
- **Planerat:** OIDC-koppling (Fas 7) kopplar RLS till autentiserad organisation

### A02: Cryptographic Failures
- **`SECRET_KEY`:** Måste sättas till slumpmässigt 32-byte hex-värde i produktion (ALDRIG default)
- **JWT:** Placeholder under utveckling, OIDC (Authentik/Keycloak) planerad
- **Rotation:** SECRET_KEY bör roteras minst årligen

### A03: Injection
- **Parameteriserad SQL:** All databasaccess via SQLAlchemy ORM — inga rå SQL-strängar
- **Pydantic-validering:** Alla request bodies valideras mot Pydantic-schemas

### A04: Insecure Design
- **Hotmodellering:** `SafeStringMixin` för sanering av stränginput
- **Bekräftelse av destruktiva åtgärder:** Frontend kräver dialogbekräftelse vid radering

### A05: Security Misconfiguration
- **SecurityHeadersMiddleware:** CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- **CORS:** Explicit allowlist via `ALLOWED_ORIGINS`
- **Trusted proxies:** Konfigurerat via `TRUSTED_PROXY_HOSTS`

### A06: Vulnerable and Outdated Components
- **Backend:** `pip-audit` i CI-pipeline
- **Frontend:** `npm audit` i CI-pipeline
- **Pre-commit:** `detect-private-key` hook

### A07: Identification and Authentication Failures
- **Nuläge:** Placeholder JWT under utveckling
- **Planerat:** OIDC (Authentik/Keycloak) bakom feature flag (`OIDC_ENABLED`)
- **Session timeout:** Planerad implementation med OIDC

### A08: Software and Data Integrity Failures
- **IntegrityError handler:** Databasfel fångas och returnerar meningsfulla HTTP-svar
- **Immutable audit_log:** Alla ändringar loggas automatiskt via SQLAlchemy event listeners
- **Audit trail:** `old_values` och `new_values` sparas som JSONB

### A09: Security Logging and Monitoring Failures
- **structlog:** JSON-formaterad logging i produktion
- **audit_log:** Komplett ändringshistorik med `changed_by`, `changed_at`, `ip_address`
- **LOG_LEVEL:** Konfigurerbart via miljövariabel

### A10: Server-Side Request Forgery (SSRF)
- **Metakatalog:** Allowlist för URL via `METAKATALOG_BASE_URL`
- **Ingen godtycklig URL-hämtning:** Backend gör inte requests till användarstyrda URL:er

## ASVS nivå 2 — chapter-mapping

| ASVS Chapter | Område | Status |
|--------------|--------|--------|
| V1 | Architecture | RLS multi-org, separerade schemas |
| V2 | Authentication | Placeholder JWT, OIDC planerad |
| V3 | Session Management | Planerad med OIDC |
| V4 | Access Control | RLS + get_rls_db per request |
| V5 | Validation | Pydantic + SafeStringMixin |
| V6 | Cryptography | SECRET_KEY, TLS via Dokploy |
| V7 | Error Handling | Strukturerade felmeddelanden, ingen stack trace i prod |
| V8 | Data Protection | Klassning K/R/T, GDPR-behandlingsregister |
| V9 | Communication | HTTPS via Dokploy reverse proxy |
| V10 | Malicious Code | pip-audit, npm audit, pre-commit hooks |
| V11 | Business Logic | Godkännandeflöde (FK-15) |
| V12 | Files and Resources | Ingen filuppladdning (minimerar attack surface) |
| V13 | API | Rate limiting, CORS, SecurityHeaders |
| V14 | Configuration | Env vars via Dokploy, inga secrets i kod |

## Rapportera sårbarheter

Skapa INTE en publik GitHub issue for säkerhetsproblem. Kontakta projektansvarig direkt.

## Secret-hantering

- Inga secrets i repot (`.env` är gitignored)
- Produktion: miljövariabler via Dokploy Environment
- `.env.example` innehåller bara dummy-värden
- `SECRET_KEY` ska genereras med: `openssl rand -hex 32`
