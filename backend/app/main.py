import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
            "docs": "/docs",
        },
    }


# Serve frontend static files (built React SPA copied to /app/static by Dockerfile)
# Mounts static assets on /assets, then uses exception handler for SPA fallback
STATIC_DIR = Path("/app/static")
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="static-assets")

    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(404)
    async def spa_fallback(request, exc):
        # API-requests ska ge JSON 404
        if request.url.path.startswith("/api/"):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        # Allt annat → SPA index.html
        return FileResponse(STATIC_DIR / "index.html")
