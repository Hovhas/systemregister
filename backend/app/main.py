import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.audit import register_audit_listeners
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

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    register_audit_listeners()
    yield
    # Shutdown


app = FastAPI(
    title="Systemregister — Sundsvalls kommunkoncern",
    description="IT-systemregister med stöd för NIS2/CSL, ISO 27001, MSB/MCF och GDPR.",
    version=settings.app_version,
    lifespan=lifespan,
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
