"""Structured logging configuration for Soni Framework."""

import logging
import logging.config
from typing import Any

try:
    from pythonjsonlogger import jsonlogger  # noqa: F401
except ImportError:
    jsonlogger = None  # Optional dependency


def setup_logging(level: str = "INFO") -> None:
    """
    Configure structured logging for Soni.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structured",
                "level": level,
            },
        },
        "loggers": {
            "soni": {
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    }

    # Add file handler with rotation if jsonlogger is available
    if jsonlogger is not None:
        config["formatters"]["json"] = {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        }
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "soni.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json",
            "level": level,
        }
        soni_logger_config = config["loggers"]["soni"]
        if isinstance(soni_logger_config, dict) and "handlers" in soni_logger_config:
            handlers = soni_logger_config["handlers"]
            if isinstance(handlers, list):
                handlers.append("file")

    logging.config.dictConfig(config)


class ContextLogger:
    """Logger with contextual information."""

    def __init__(self, name: str):
        """
        Initialize context logger.

        Args:
            name: Logger name (typically __name__)
        """
        self.logger = logging.getLogger(name)

    def with_context(self, **context: Any) -> logging.LoggerAdapter:
        """
        Add context to log messages.

        Args:
            **context: Context key-value pairs

        Returns:
            LoggerAdapter with context
        """
        return logging.LoggerAdapter(self.logger, context)
