"""File filtering utilities for Archon AI."""

from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".sh",
    ".sql",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".go",
    ".rs",
}

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".cache",
    "coverage",
}

BINARY_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".mp4",
    ".mp3",
}


def is_supported_file(file_path: Path) -> bool:
    """
    Determines whether a file should be indexed.

    Args:
        file_path: Path to file.

    Returns:
        True if supported, False otherwise.
    """

    if not file_path.is_file():
        return False

    for parent in file_path.parents:
        if parent.name in IGNORED_DIRECTORIES:
            return False

    suffix = file_path.suffix.lower()

    if suffix in BINARY_EXTENSIONS:
        return False

    return suffix in SUPPORTED_EXTENSIONS