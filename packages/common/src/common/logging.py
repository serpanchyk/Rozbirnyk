"""
Provides structured, context-aware JSON logging for all services.

This module configures a JSON logger that automatically includes
application-level context, such as trace, session, and user IDs,
into every log record. This is essential for observability and
request tracing across the distributed system.

Context is managed via contextvars, ensuring that contextual
information is available without needing to pass it explicitly
through the call stack.
"""

import contextvars
import logging
from datetime import UTC, datetime
from typing import Any

from pythonjsonlogger import json as jsonlogger

trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)
session_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "session_id", default=None
)
user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)


class ContextualJsonFormatter(jsonlogger.JsonFormatter):
    """
    A custom JSON log formatter that enriches log records with context.

    This formatter automatically injects `trace_id`, `session_id`, and
    `user_id` from contextvars into the JSON output. It also standardizes
    the timestamp and log level fields.
    """

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """
        Add service-specific and contextual fields to the log record.

        This method is called by the base formatter and is the correct
        place to add custom fields to the structured log output.

        Args:
            log_record: The log record dictionary to be updated.
            record: The original `logging.LogRecord` instance.
            message_dict: A dictionary containing the formatted message.
        """
        super().add_fields(log_record, record, message_dict)

        if not log_record.get("timestamp"):
            log_record["timestamp"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if not log_record.get("name"):
            log_record["name"] = record.name

        log_record["level"] = record.levelname

        log_record["trace_id"] = trace_id_var.get()
        log_record["session_id"] = session_id_var.get()
        log_record["user_id"] = user_id_var.get()


def setup_logger(service_name: str) -> logging.Logger:
    """
    Configure and return a logger for a specific service.

    Each service should call this function at startup to get a
    correctly configured logger instance. It ensures that all logs
    are formatted as JSON and include the necessary context.

    Args:
        service_name: The name of the service (e.g., 'news_service').

    Returns:
        A configured `logging.Logger` instance.
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    handler = logging.StreamHandler()

    formatter = ContextualJsonFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.propagate = False

    return logger
