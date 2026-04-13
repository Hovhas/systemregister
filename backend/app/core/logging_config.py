"""
Structured JSON logging för production observability.

Använd Python stdlib logging med JSONFormatter.
Loggar har korrelations-ID per request via context-var.
"""
import logging
import json
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

# Context vars per request
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
org_id_var: ContextVar[str | None] = ContextVar("org_id", default=None)


class JSONFormatter(logging.Formatter):
    """JSON formatter for production logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
            "org_id": org_id_var.get(),
        }
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


def configure_logging(level: str = "INFO", structured: bool = True) -> None:
    """Configure root logger."""
    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    if structured:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
