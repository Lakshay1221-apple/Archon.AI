"""File filtering utilities for Archon AI, supporting universal codebases."""

import logging
from pathlib import Path
from src.utils.config import load_config

logger = logging.getLogger(__name__)


def should_ignore_directory(
    file_path: Path,
    repo_path: Path = None,
    ignored_dirs: list[str] = None,
) -> bool:
    """Checks if a file path is inside any of the ignored directories.

    Supports simple directory names (e.g. 'node_modules') and specific
    subdirectories relative to the repo root (e.g. '.github/cache').

    Args:
        file_path: Path of the file.
        repo_path: Optional repository root path.
        ignored_dirs: Optional list of ignored directories.

    Returns:
        True if the file is inside an ignored directory, False otherwise.
    """
    if not ignored_dirs:
        return False

    # Get relative path components to match paths like .github/cache
    if repo_path:
        try:
            rel_path = file_path.relative_to(repo_path)
        except ValueError:
            rel_path = file_path
    else:
        rel_path = file_path

    parts = rel_path.parts[:-1]  # Exclude the filename itself

    for ignored in ignored_dirs:
        if "/" in ignored or "\\" in ignored:
            # Check if this ignored path exists as a contiguous sub-sequence of parts
            ignored_parts = Path(ignored).parts
            n_ignored = len(ignored_parts)
            n_parts = len(parts)
            for idx in range(n_parts - n_ignored + 1):
                if parts[idx : idx + n_ignored] == ignored_parts:
                    return True
        else:
            if ignored in parts:
                return True

    # Absolute parent check in case repo_path wasn't provided or file_path is absolute
    if not repo_path:
        for parent in file_path.parents:
            if parent.name in ignored_dirs:
                return True

    return False


def is_text_file(file_path: Path, binary_extensions: list[str]) -> bool:
    """Determines whether a file contains text content.

    Uses blocklist extension checks, null-byte checks, and character density
    heuristics.

    Args:
        file_path: Path object of the file to check.
        binary_extensions: List of extensions classified as binary.

    Returns:
        True if file is identified as a text file, False otherwise.
    """
    suffix = file_path.suffix.lower()
    if suffix in binary_extensions:
        return False

    try:
        # Read the first 8KB of the file
        with file_path.open("rb") as f:
            chunk = f.read(8192)

        if not chunk:
            return True  # Empty file is considered text

        # Check for null byte
        if b"\x00" in chunk:
            return False

        # Try decoding as UTF-8
        try:
            text_chunk = chunk.decode("utf-8")
        except UnicodeDecodeError:
            # If UTF-8 fails, check density of non-printable control bytes
            control_bytes = sum(1 for b in chunk if b < 32 and b not in (9, 10, 13))
            if control_bytes / len(chunk) > 0.3:
                return False
            # Check decode as latin-1 to perform printability checks
            text_chunk = chunk.decode("latin-1", errors="ignore")

        # Check ratio of non-printable control characters in decoded text
        control_chars = sum(
            1 for c in text_chunk if ord(c) < 32 and c not in ("\t", "\n", "\r")
        )
        if len(text_chunk) > 0 and (control_chars / len(text_chunk)) > 0.3:
            return False

        return True
    except Exception as e:
        logger.debug(f"Error checking text type for {file_path}: {e}")
        return False


def is_supported_file(
    file_path: Path,
    repo_path: Path = None,
    config: dict = None,
) -> bool:
    """Determines whether a file path points to a file suitable for indexing.

    Filters out files in ignored directories, binary files, and non-files.

    Args:
        file_path: Path object of the file to check.
        repo_path: Optional repository root path to match subdirectories.
        config: Optional configuration dictionary.

    Returns:
        True if the file is a text file and not ignored, False otherwise.
    """
    if not file_path.is_file():
        return False

    if config is None:
        config = load_config()

    ignored_dirs = config.get("ignored_directories", [])
    binary_exts = config.get("binary_extensions", [])

    # 1. Check ignored directories
    if should_ignore_directory(file_path, repo_path, ignored_dirs):
        return False

    # 2. Check if text file (handles binary blocklist + null-byte/control heuristics)
    return is_text_file(file_path, binary_exts)
