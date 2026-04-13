"""
Delad rate limiter för slowapi.

Flyttad ur main.py för att undvika cirkulär import när API-moduler
behöver dekorera specifika endpoints (tunga rapporter/export).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

_settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[_settings.rate_limit_default],
)
