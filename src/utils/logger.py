"""Structured logging for PharmaAgent Pro."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def _setup_logging(level: str = "INFO") -> None:
    """Configure root logging once."""
    global _configured
    if _configured:
        return

    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    root = logging.getLogger("pharma_agent")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(console)

    # File handler
    file_handler = logging.FileHandler(log_dir / "pharma_agent.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Get a named logger under the pharma_agent namespace."""
    _setup_logging(level)
    return logging.getLogger(f"pharma_agent.{name}")
