"""Small structured logging helpers shared by the API and worker."""

import json
import logging
from typing import Any


def configure_structured_logging() -> None:
    """Ensure application JSON events are visible under Uvicorn's log setup."""
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False
    if app_logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    app_logger.addHandler(handler)


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit one JSON log line without accidentally logging request contents."""
    logger.info(json.dumps({"event": event, **fields}, sort_keys=True, default=str))
