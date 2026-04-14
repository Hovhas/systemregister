import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.audit import register_audit_listeners
from app.core.events import register_listener
from app.core.logging_config import configure_logging, request_id_var, user_id_var, org_id_var
from app.services.metakatalog_service import sync_to_metakatalog
from app.api.organizations import router as org_router
from app.api.systems import router as sys_router
from app.api.classifications import router as classification_router
from app.api.owners import router as owner_router
from app.api.integrations import router as integration_router, system_router as integration_system_router
from app.api.export import router as export_router
from app.api.imports import router as import_router
from app.api.gdpr import router as gdpr_router
from app.api.contracts import router as contracts_router
from app.api.reports import router as reports_router
from app.api.audit import router as audit_router
from app.api.notifications import router as notifications_router
from app.api.objekt import router as objekt_router
from app.api.components import router as components_router
from app.api.modules import router as modules_router
from app.api.information_assets import router as information_assets_router
from app.api.approvals import router as approvals_router
from app.api.sbom import router as sbom_router
from app.api.me import router as me_router
from app.api.webhooks import router as webhooks_router
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.metrics import http_requests_total, http_request_duration_seconds

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — säkerhetskontroller (OWASP A02/A05)
    if settings.environment == "production":
        _weak_secret_keys = (
            "change-me-in-production",
            "dev-secret-key-change-in-prod",
            "",
        )
        if settings.secret_key in _weak_secret_keys:
            raise RuntimeError(
                "SECRET_KEY måste roteras i produktion. "
                "Sätt env var SECRET_KEY=<slumpmässig 32-byte hex-sträng>."
            )
    configure_logging(
        level=settings.log_level,
        structured=settings.environment != "development",
    )
    register_audit_listeners()
    register_listener(sync_to_metakatalog)
    yield
    # Shutdown


app = FastAPI(
    title="Systemregister — Sundsvalls kommunkoncern",
    description="IT-systemregister med stöd för NIS2/CSL, ISO 27001, MSB/MCF och GDPR.",
    version=settings.app_version,
    lifespan=lifespan,
)

# --- Rate Limiting (ASVS V13) ---
# Limitern flyttad till app.core.rate_limit för delning mellan moduler
from app.core.rate_limit import limiter  # noqa: E402
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- IntegrityError → 422/409, ProgrammingError → 403 (OWASP A08 / API-kontrakt) ---
from sqlalchemy.exc import IntegrityError, ProgrammingError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    pg_code = getattr(exc.orig, "pgcode", None) if exc.orig else None
    if pg_code == "23505":
        # Unique violation
        return JSONResponse(
            status_code=409,
            content={"detail": "En post med dessa unika värden finns redan"},
        )
    if pg_code == "23503":
        # FK violation
        return JSONResponse(
            status_code=422,
            content={"detail": "Refererad resurs finns inte (ogiltig FK-referens)"},
        )
    # Fallback for other constraint violations
    return JSONResponse(
        status_code=422,
        content={"detail": "Databas-constraint överträdd"},
    )


@app.exception_handler(ProgrammingError)
async def programming_error_handler(request: Request, exc: ProgrammingError):
    msg = str(exc).lower()
    if "row-level security" in msg or "insufficient_privilege" in msg:
        return JSONResponse(
            status_code=403,
            content={"detail": "Åtkomst nekad: resursen tillhör en annan organisation"},
        )
    # Non-RLS ProgrammingError → 500
    return JSONResponse(
        status_code=500,
        content={"detail": "Internt serverfel"},
    )

# --- OWASP Security Headers Middleware (ASVS V14) ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.environment != "development":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )
        return response

app.add_middleware(SecurityHeadersMiddleware)


# --- Request Context Middleware (korrelations-ID per request) ---
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_var.set(req_id)
        # Set user_id, org_id from headers if available (will come from JWT later)
        org_id_var.set(request.headers.get("X-Organization-Id"))
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

app.add_middleware(RequestContextMiddleware)


# --- Prometheus Metrics Middleware ---
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        endpoint = request.url.path
        # Skip /metrics itself to avoid recursion
        if endpoint != "/metrics":
            http_requests_total.labels(
                method=request.method, endpoint=endpoint, status=response.status_code
            ).inc()
            http_request_duration_seconds.labels(
                method=request.method, endpoint=endpoint
            ).observe(duration)
        return response

app.add_middleware(MetricsMiddleware)

# Trusted proxy headers (Traefik sätter X-Forwarded-Proto)
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.trusted_proxy_hosts)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Organization-Id"],
)

# Routers
app.include_router(org_router, prefix="/api/v1")
app.include_router(sys_router, prefix="/api/v1")
app.include_router(classification_router, prefix="/api/v1")
app.include_router(owner_router, prefix="/api/v1")
app.include_router(integration_router, prefix="/api/v1")
app.include_router(integration_system_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(import_router, prefix="/api/v1")
app.include_router(gdpr_router, prefix="/api/v1")
app.include_router(contracts_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(objekt_router, prefix="/api/v1")
app.include_router(components_router, prefix="/api/v1")
app.include_router(modules_router, prefix="/api/v1")
app.include_router(information_assets_router, prefix="/api/v1")
app.include_router(approvals_router, prefix="/api/v1")
app.include_router(sbom_router, prefix="/api/v1")
app.include_router(me_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")

# --- Deprecated flat routes → 308 Permanent Redirect to nested ---
# Kept for one release cycle so existing API clients that follow redirects
# continue to work. Remove these after clients have migrated.
@app.api_route("/api/v1/owners/{owner_id}", methods=["PATCH", "DELETE"], include_in_schema=False)
async def deprecated_owner_redirect(request: Request, owner_id: str):
    # Clients must include system_id — we can't infer it without a DB lookup.
    # Return 308 with Location hint; body explains migration.
    return JSONResponse(
        status_code=422,
        content={
            "detail": (
                "Denna endpoint är borttagen. "
                "Använd /api/v1/systems/{system_id}/owners/{owner_id} istället."
            )
        },
    )


@app.api_route("/api/v1/gdpr/{treatment_id}", methods=["PATCH", "DELETE"], include_in_schema=False)
async def deprecated_gdpr_redirect(request: Request, treatment_id: str):
    return JSONResponse(
        status_code=422,
        content={
            "detail": (
                "Denna endpoint är borttagen. "
                "Använd /api/v1/systems/{system_id}/gdpr/{treatment_id} istället."
            )
        },
    )


@app.api_route("/api/v1/contracts/{contract_id}", methods=["PATCH", "DELETE"], include_in_schema=False)
async def deprecated_contract_redirect(request: Request, contract_id: str):
    return JSONResponse(
        status_code=422,
        content={
            "detail": (
                "Denna endpoint är borttagen. "
                "Använd /api/v1/systems/{system_id}/contracts/{contract_id} istället."
            )
        },
    )


# Health check — ingen /api/v1-prefix (för Docker HEALTHCHECK + load balancer)
app.include_router(health_router)

# Metrics — ingen /api/v1-prefix (för Prometheus scraping)
app.include_router(metrics_router)


# --- OWASP A05: Suppress stack traces in production (ASVS V7) ---
if settings.environment != "development":
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(500)
    async def suppress_internal_errors(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"detail": "Internt serverfel"})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": "Valideringsfel i indata"})


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


@app.get("/api/v1")
async def api_root():
    return {
        "service": "Systemregister",
        "version": settings.app_version,
        "endpoints": {
            "organizations": "/api/v1/organizations",
            "systems": "/api/v1/systems",
            "system_stats": "/api/v1/systems/stats/overview",
            "classifications": "/api/v1/systems/{system_id}/classifications",
            "owners": "/api/v1/systems/{system_id}/owners",
            "integrations": "/api/v1/integrations",
            "export_xlsx": "/api/v1/export/systems.xlsx",
            "export_csv": "/api/v1/export/systems.csv",
            "export_json": "/api/v1/export/systems.json",
            "import_systems": "/api/v1/import/systems",
            "objekt": "/api/v1/objekt",
            "components": "/api/v1/components",
            "modules": "/api/v1/modules",
            "information_assets": "/api/v1/information-assets",
            "docs": "/docs",
        },
    }


# Serve frontend static files (built React SPA copied to /app/static by Dockerfile)
# Mounts static assets on /assets, then uses exception handler for SPA fallback
STATIC_DIR = Path("/app/static")
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="static-assets")

    @app.exception_handler(404)
    async def spa_fallback(request, exc):
        path = request.url.path
        # API-requests → JSON 404
        if path.startswith("/api/"):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        # Statiska filer som inte finns → riktig 404 (inte index.html)
        if path.startswith("/assets/") or "." in path.split("/")[-1]:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        # SPA-routes → index.html
        response = FileResponse(STATIC_DIR / "index.html")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
