"""
Tests for the logging configuration and utilities.
"""

import json
import logging
import unittest
from unittest.mock import MagicMock, patch

from common.logging import (
    ContextualJsonFormatter,
    session_id_var,
    setup_logger,
    trace_id_var,
    user_id_var,
)


class TestLogging(unittest.TestCase):
    """
    Test suite for the logging system.
    """

    def test_setup_logger(self) -> None:
        """
        Verify that setup_logger correctly configures a logger instance.
        """
        logger = setup_logger("test_service")
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test_service")
        self.assertEqual(logger.level, logging.INFO)
        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)
        self.assertIsInstance(logger.handlers[0].formatter, ContextualJsonFormatter)
        self.assertFalse(logger.propagate)

    def test_contextual_json_formatter(self) -> None:
        """
        Verify that ContextualJsonFormatter adds basic fields correctly.
        """
        formatter = ContextualJsonFormatter()
        record = logging.LogRecord(
            "test", logging.INFO, "/path", 1, "message", (), None
        )
        log_record: dict[str, str | None] = {}
        formatter.add_fields(log_record, record, {})
        self.assertIn("timestamp", log_record)
        self.assertEqual(log_record["level"], "INFO")
        self.assertIsNone(log_record["trace_id"])
        self.assertIsNone(log_record["session_id"])
        self.assertIsNone(log_record["user_id"])

    def test_contextual_json_formatter_with_context_vars(self) -> None:
        """
        Verify that ContextualJsonFormatter includes values from context variables.
        """
        trace_id_var.set("test_trace_id")
        session_id_var.set("test_session_id")
        user_id_var.set("test_user_id")

        formatter = ContextualJsonFormatter()
        record = logging.LogRecord(
            "test", logging.INFO, "/path", 1, "message", (), None
        )
        log_record: dict[str, str | None] = {}
        formatter.add_fields(log_record, record, {})

        self.assertEqual(log_record["trace_id"], "test_trace_id")
        self.assertEqual(log_record["session_id"], "test_session_id")
        self.assertEqual(log_record["user_id"], "test_user_id")

        trace_id_var.set(None)
        session_id_var.set(None)
        user_id_var.set(None)

    @patch("logging.StreamHandler.handle")
    def test_log_output(self, mock_handle: MagicMock) -> None:
        """
        Verify the final JSON output of a log record.
        """
        logger = setup_logger("output_test_service")
        trace_id_var.set("output_trace_id")
        session_id_var.set("output_session_id")
        user_id_var.set("output_user_id")

        logger.info("This is a test message")

        self.assertEqual(mock_handle.call_count, 1)
        log_record = mock_handle.call_args[0][0]
        log_output = logger.handlers[0].formatter.format(log_record)
        log_record_dict = json.loads(log_output)

        self.assertEqual(log_record_dict["name"], "output_test_service")
        self.assertEqual(log_record_dict["message"], "This is a test message")
        self.assertEqual(log_record_dict["level"], "INFO")
        self.assertEqual(log_record_dict["trace_id"], "output_trace_id")
        self.assertEqual(log_record_dict["session_id"], "output_session_id")
        self.assertEqual(log_record_dict["user_id"], "output_user_id")

        trace_id_var.set(None)
        session_id_var.set(None)
        user_id_var.set(None)


if __name__ == "__main__":
    unittest.main()
