import contextvars
import logging
from datetime import datetime
from typing import Any

from pythonjsonlogger import json

trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id", default=None
)
session_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "session_id", default=None
)
user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id", default=None
)


class ContextualJsonFormatter(json.JsonFormatter):
    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        if not log_record.get("timestamp"):
            log_record["timestamp"] = datetime.utcnow().strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )

        log_record["level"] = record.levelname

        log_record["trace_id"] = trace_id_var.get()
        log_record["session_id"] = session_id_var.get()
        log_record["user_id"] = user_id_var.get()


def setup_logger(service_name: str) -> logging.Logger:
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    handler = logging.StreamHandler()

    formatter = ContextualJsonFormatter("%(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.propagate = False

    return logger
