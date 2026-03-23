"""Logging configuration for cache analysis runs."""

from __future__ import annotations

import logging
import os
from logging import Logger


def configure_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """Configure root logger with console and optional file output."""

    normalized = level.upper().strip()
    if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError(f"Unsupported log level: {level}")

    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_file:
        parent = os.path.dirname(log_file)
        if parent:
            os.makedirs(parent, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, mode="w", encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, normalized),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )


def get_logger(name: str) -> Logger:
    return logging.getLogger(name)
