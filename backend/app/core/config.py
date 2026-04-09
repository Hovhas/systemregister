from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Systemregister"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://systemregister:devpassword@localhost:5432/systemregister"
    database_url_sync: str = "postgresql://systemregister:devpassword@localhost:5432/systemregister"

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # Rate limiting (ASVS V13)
    rate_limit_default: str = "200/minute"

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Betrodda proxy-hostar som tillåts sätta X-Forwarded-For (Traefik, intern LB)
    trusted_proxy_hosts: list[str] = ["127.0.0.1", "10.0.0.0/8", "172.16.0.0/12"]

    # OIDC
    oidc_issuer_url: str = ""
    oidc_client_id: str = ""
    oidc_audience: str = ""
    oidc_org_claim: str = "org_id"
    oidc_roles_claim: str = "groups"
    oidc_superadmin_role: str = "systemregister_admin"
    oidc_enabled: bool = False

    # Metakatalog
    metakatalog_base_url: str = ""
    metakatalog_api_key: str = ""
    metakatalog_webhook_secret: str = ""
    metakatalog_enabled: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
