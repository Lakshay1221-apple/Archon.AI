"""Centralized logging framework for Archon AI."""

import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Unique session ID generated per execution run
SESSION_ID = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Global variables to ensure logger setup occurs only once
_logging_setup_complete = False
_logging_config = {}


class SessionFilter(logging.Filter):
    """Logging filter to inject the global session ID and format module names."""

    def filter(self, record):
        record.session_id = SESSION_ID
        # Extract the short module name from full package name (e.g. src.ingestion.clone_repo -> clone_repo)
        parts = record.name.split(".")
        record.short_name = parts[-1]
        return True


def setup_logging() -> None:
    """Configures centralized log handlers, formatters, and target log files."""
    global _logging_setup_complete, _logging_config
    if _logging_setup_complete:
        return

    # Determine project root paths
    project_root = Path(__file__).resolve().parents[2]
    config_file = project_root / "configs" / "logging_config.json"
    logs_dir = project_root / "logs"

    # Fallback configuration defaults
    _logging_config = {
        "log_level": "INFO",
        "console_logging": True,
        "file_logging": True,
        "enable_debug_file_filter": False,
    }

    # Load custom configurations if file exists
    if config_file.exists():
        try:
            with config_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                _logging_config.update(data)
        except Exception as e:
            # Print to stdout as logging is not configured yet
            print(f"Warning: Failed to load logging config: {e}. Using defaults.")

    # Parse and set logging level
    level_name = _logging_config["log_level"].upper()
    log_level = getattr(logging, level_name, logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear pre-existing handlers to prevent duplicate entries
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Log formatters
    console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
    file_formatter = logging.Formatter(
        "%(asctime)s | [%(session_id)s] | %(levelname)s | %(short_name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    session_filter = SessionFilter()

    # 1. Console Ingestion Handler
    if _logging_config["console_logging"]:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(session_filter)
        root_logger.addHandler(console_handler)

    # 2. File-Based Handlers (if enabled)
    if _logging_config["file_logging"]:
        logs_dir.mkdir(parents=True, exist_ok=True)

        def create_rotating_handler(
            filename: str, handler_level: int
        ) -> RotatingFileHandler:
            handler = RotatingFileHandler(
                logs_dir / filename,
                maxBytes=10_000_000,
                backupCount=5,
                encoding="utf-8",
            )
            handler.setLevel(handler_level)
            handler.setFormatter(file_formatter)
            handler.addFilter(session_filter)
            return handler

        # Unified execution log
        archon_handler = create_rotating_handler("archon.log", log_level)
        root_logger.addHandler(archon_handler)

        # Isolated error and critical log
        errors_handler = create_rotating_handler("errors.log", logging.ERROR)
        root_logger.addHandler(errors_handler)

        # Module-specific routing for Ingestion branch
        ingestion_logger = logging.getLogger("src.ingestion")
        ingestion_handler = create_rotating_handler("ingestion.log", log_level)
        ingestion_logger.addHandler(ingestion_handler)

        # Module-specific routing for Parsing branch
        parsing_logger = logging.getLogger("src.parsing")
        parsing_handler = create_rotating_handler("parser.log", log_level)
        parsing_logger.addHandler(parsing_handler)

    # 3. Handle File Filter Debug Override
    file_filter_logger = logging.getLogger("src.ingestion.file_filter")
    if _logging_config["enable_debug_file_filter"]:
        file_filter_logger.setLevel(logging.DEBUG)
    else:
        file_filter_logger.setLevel(logging.INFO)

    _logging_setup_complete = True


def get_logger(name: str) -> logging.Logger:
    """Retrieves or creates a logger instance, initializing setup if necessary.

    Args:
        name: Name of the logger (typically __name__).

    Returns:
        The configured logging.Logger instance.
    """
    setup_logging()
    return logging.getLogger(name)


def set_session_id(session_id: str) -> None:
    """Updates the global session ID for tracing the current run.

    Args:
        session_id: The unique run session string.
    """
    global SESSION_ID
    SESSION_ID = session_id
