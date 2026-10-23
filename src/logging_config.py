"""Structured JSON logging with correlation IDs and sensitive data sanitization."""
import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variables for request tracing
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
job_id_ctx: ContextVar[Optional[str]] = ContextVar("job_id", default=None)

# Patterns to sanitize in log records
SENSITIVE_PATTERNS = [
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE), r"\1***MASKED***"),
    (re.compile(r"(xi-api-key['\":\s=]+)[A-Za-z0-9_\-]{8,}", re.IGNORECASE), r"\1***MASKED***"),
    (re.compile(r"(sksoundverse_[A-Za-z0-9_\-]{6,})", re.IGNORECASE), r"sksoundverse_***MASKED***"),
    (re.compile(r"(api[_-]?key['\":\s=]+)[A-Za-z0-9_\-]{8,}", re.IGNORECASE), r"\1***MASKED***"),
    (re.compile(r"(password['\":\s=]+)[^\s,\"'\&]+", re.IGNORECASE), r"\1***MASKED***"),
]


def sanitize_text(text: str) -> str:
    """Mask credentials, tokens, and secrets from log strings."""
    if not isinstance(text, str):
        return str(text)
    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON per IncuBrix Integration Standard Point 8."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize_text(record.getMessage()),
        }

        # Include tracing context if present
        cid = correlation_id_ctx.get()
        if cid:
            log_entry["correlation_id"] = cid

        jid = getattr(record, "job_id", None) or job_id_ctx.get()
        if jid:
            log_entry["job_id"] = jid

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_structured_logging(log_level: str = "INFO"):
    """Configure the root logger with StructuredJsonFormatter."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(handler)

    # Silence overly verbose external loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("pyloudnorm").setLevel(logging.WARNING)
