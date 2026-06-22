"""Module for filtering files during repository ingestion."""

from pathlib import Path

# Set of supported file extensions (case-insensitive)
SUPPORTED_EXTENSIONS: set[str] = {
    ".py",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".txt",
}

# Set of ignored directory names
IGNORED_DIRECTORIES: set[str] = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
}


def is_supported_file(file_path: Path) -> bool:
    """Determines whether a file path points to a supported file for indexing.

    Args:
        file_path: The pathlib Path object of the file to check.

    Returns:
        True if the file is supported and not in any ignored directory,
        False otherwise.
    """
    if not file_path.is_file():
        return False

    # Check if any parent directory is in the ignored list
    for parent in file_path.parents:
        if parent.name in IGNORED_DIRECTORIES:
            return False

    # Check if the file suffix is supported
    suffix = file_path.suffix.lower()
    return suffix in SUPPORTED_EXTENSIONS
