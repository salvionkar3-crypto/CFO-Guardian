"""Structured Logging Configuration

Configures unified logging with ISO-8601 timestamps, log levels,
logger namespaces, and sanitized log output (masking secrets).
"""

import logging
import sys
from typing import Any, Dict


class SensitiveDataFilter(logging.Filter):
    """Filter that masks sensitive tokens, secrets, and auth headers from logs."""

    SENSITIVE_KEYS = ("authorization", "bearer", "paypal_secret", "client_secret", "api_key", "password", "token")

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        # Redact raw Bearer tokens or secret values if accidentally printed
        for key in self.SENSITIVE_KEYS:
            if key in message.lower():
                record.msg = "[REDACTED SENSITIVE LOG ENTRY]"
                record.args = ()
                break
        return True


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configures root and application loggers."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    log_format = (
        "%(asctime)s [%(levelname)s] [%(name)s] "
        "[line:%(lineno)d] - %(message)s"
    )

    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True,
    )

    app_logger = logging.getLogger("guardian_cfo")
    app_logger.setLevel(numeric_level)
    app_logger.addFilter(SensitiveDataFilter())

    # Quiet overly chatty external loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.INFO)

    return app_logger


logger = logging.getLogger("guardian_cfo")

