"""Configuration loader for Archon AI ingestion and parsing."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Fallback default values
DEFAULT_BINARY_EXTENSIONS: set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".ico",
    ".svg",
    ".pdf",
    ".mp4",
    ".mov",
    ".avi",
    ".mp3",
    ".wav",
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
    ".exe",
    ".dll",
    ".so",
    ".o",
    ".a",
    ".class",
    ".jar",
    ".pyc",
}

DEFAULT_IGNORED_DIRECTORIES: set[str] = {
    ".git",
    ".github/cache",
    "node_modules",
    "dist",
    "build",
    "target",
    "coverage",
    "htmlcov",
    ".next",
    ".nuxt",
    ".cache",
    "venv",
    ".venv",
    "__pycache__",
    ".idea",
    ".vscode",
    "logs",
    "*.log",
    "*.pyc",
    "*.lock",
    "*lock.json",
    "*lock.yaml",
    ".pytest_cache",
    ".mypy_cache",
}

DEFAULT_MAX_FILE_SIZE_MB = 5
DEFAULT_CHUNK_SIZE_MB = 1


def load_config() -> dict:
    """Loads configuration from configs/ingestion_config.json if it exists.

    Otherwise, returns default values.
    """
    # Project root is the grandparent of src/utils
    project_root = Path(__file__).resolve().parents[2]
    config_file = project_root / "configs" / "ingestion_config.json"

    defaults = {
        "max_file_size_mb": DEFAULT_MAX_FILE_SIZE_MB,
        "chunk_size_mb": DEFAULT_CHUNK_SIZE_MB,
        "binary_extensions": list(DEFAULT_BINARY_EXTENSIONS),
        "ignored_directories": list(DEFAULT_IGNORED_DIRECTORIES),
    }

    if config_file.exists():
        try:
            with config_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # Safely merge loaded data with defaults
            config = {
                "max_file_size_mb": data.get(
                    "max_file_size_mb", defaults["max_file_size_mb"]
                ),
                "chunk_size_mb": data.get("chunk_size_mb", defaults["chunk_size_mb"]),
                "binary_extensions": list(
                    set(data.get("binary_extensions", defaults["binary_extensions"]))
                ),
                "ignored_directories": list(
                    set(
                        data.get(
                            "ignored_directories",
                            defaults["ignored_directories"],
                        )
                    )
                ),
            }
            logger.info(f"Loaded custom ingestion configuration from {config_file}")
            return config
        except Exception as e:
            logger.warning(f"Error loading {config_file}: {e}. Using defaults.")

    return defaults
