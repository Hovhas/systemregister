"""
OIDC/JWT authentication module.

When oidc_enabled=True:
  - Validates Bearer tokens from Authorization header
  - Extracts user identity, org_id, and roles from JWT claims
  - Caches JWKS keys from the OIDC provider

When oidc_enabled=False (default):
  - No authentication required (development mode)
  - X-Organization-Id header used for RLS context (as before)
"""

import logging
import time
import uuid
from dataclasses import dataclass, field

import httpx
import jwt
from fastapi import HTTPException, Request, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CurrentUser:
    sub: str
    email: str | None = None
    name: str | None = None
    org_id: uuid.UUID | None = None
    roles: list[str] = field(default_factory=list)
    is_superadmin: bool = False


# JWKS cache
_jwks_cache: dict = {}
_jwks_fetched_at: float = 0
_JWKS_TTL = 3600  # 1 hour


async def _get_jwks(issuer_url: str) -> dict:
    """Fetch and cache JWKS from OIDC provider."""
    global _jwks_cache, _jwks_fetched_at

    if _jwks_cache and (time.time() - _jwks_fetched_at) < _JWKS_TTL:
        return _jwks_cache

    async with httpx.AsyncClient(timeout=10) as client:
        # Discover JWKS URI from .well-known
        discovery_url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
        resp = await client.get(discovery_url)
        resp.raise_for_status()
        jwks_uri = resp.json()["jwks_uri"]

        # Fetch JWKS
        resp = await client.get(jwks_uri)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = time.time()

    return _jwks_cache


def _decode_token(token: str, jwks: dict, settings) -> dict:
    """Decode and validate a JWT token using JWKS."""
    # Get the signing key
    public_keys = {}
    for key_data in jwks.get("keys", []):
        kid = key_data.get("kid")
        if kid:
            public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

    # Decode header to find kid
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    if kid not in public_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ogiltig token-signatur",
        )

    return jwt.decode(
        token,
        key=public_keys[kid],
        algorithms=["RS256"],
        audience=settings.oidc_audience or settings.oidc_client_id,
        issuer=settings.oidc_issuer_url,
    )


async def get_current_user(request: Request) -> CurrentUser:
    """FastAPI dependency: extract and validate user from Bearer token.
    Raises 401 if token is missing or invalid."""
    settings = get_settings()

    if not settings.oidc_enabled:
        # Dev mode: return a dummy user
        return CurrentUser(sub="dev-user", email="dev@localhost", is_superadmin=True)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header saknas eller är ogiltig",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]

    try:
        jwks = await _get_jwks(settings.oidc_issuer_url)
        claims = _decode_token(token, jwks, settings)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token har gått ut",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Ogiltig token: {e}",
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Kunde inte nå autentiseringstjänsten",
        )

    # Extract claims
    org_claim = settings.oidc_org_claim
    roles_claim = settings.oidc_roles_claim

    org_id = None
    raw_org = claims.get(org_claim)
    if raw_org:
        try:
            org_id = uuid.UUID(str(raw_org))
        except ValueError:
            pass

    roles = claims.get(roles_claim, [])
    if isinstance(roles, str):
        roles = [roles]

    return CurrentUser(
        sub=claims.get("sub", ""),
        email=claims.get("email"),
        name=claims.get("name") or claims.get("preferred_username"),
        org_id=org_id,
        roles=roles,
        is_superadmin=settings.oidc_superadmin_role in roles,
    )


async def get_current_user_optional(request: Request) -> CurrentUser | None:
    """Same as get_current_user but returns None instead of raising 401."""
    settings = get_settings()
    if not settings.oidc_enabled:
        return None

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    try:
        return await get_current_user(request)
    except HTTPException:
        return None
