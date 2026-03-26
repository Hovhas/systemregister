from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.audit import register_audit_listeners
from app.api.organizations import router as org_router
from app.api.systems import router as sys_router

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
            "docs": "/docs",
        },
    }
