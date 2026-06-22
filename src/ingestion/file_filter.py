"""File filtering utilities for Archon AI, supporting universal codebases."""

from pathlib import Path
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


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
                    logger.debug(
                        f"Directory ignore match: File '{file_path}' skipped because "
                        f"it matched subpath pattern '{ignored}' relative to repo root."
                    )
                    return True
        else:
            if ignored in parts:
                logger.debug(
                    f"Directory ignore match: File '{file_path}' skipped because "
                    f"parent directory segment '{ignored}' is in ignored list."
                )
                return True

    # Absolute parent check in case repo_path wasn't provided or file_path is absolute
    if not repo_path:
        for parent in file_path.parents:
            if parent.name in ignored_dirs:
                logger.debug(
                    f"Directory ignore match: File '{file_path}' skipped because "
                    f"absolute parent segment '{parent.name}' is in ignored list."
                )
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
        logger.debug(
            f"Binary detection: File '{file_path}' skipped because "
            f"its extension '{suffix}' is in the binary extensions blocklist."
        )
        return False

    try:
        # Read the first 8KB of the file
        with file_path.open("rb") as f:
            chunk = f.read(8192)

        if not chunk:
            logger.debug(
                f"File '{file_path}' accepted (empty file is treated as text)."
            )
            return True

        # Check for null byte
        if b"\x00" in chunk:
            logger.debug(
                f"Binary detection: File '{file_path}' skipped because "
                f"it contains null bytes (indicates binary data)."
            )
            return False

        # Try decoding as UTF-8
        try:
            text_chunk = chunk.decode("utf-8")
        except UnicodeDecodeError:
            # If UTF-8 fails, check density of non-printable control bytes
            control_bytes = sum(1 for b in chunk if b < 32 and b not in (9, 10, 13))
            ratio = control_bytes / len(chunk)
            if ratio > 0.3:
                logger.debug(
                    f"Binary detection: File '{file_path}' skipped because "
                    f"control character ratio {ratio:.2f} exceeds threshold 0.30."
                )
                return False
            # Check decode as latin-1 to perform printability checks
            text_chunk = chunk.decode("latin-1", errors="ignore")

        # Check ratio of non-printable control characters in decoded text
        control_chars = sum(
            1 for c in text_chunk if ord(c) < 32 and c not in ("\t", "\n", "\r")
        )
        ratio = control_chars / len(text_chunk)
        if len(text_chunk) > 0 and ratio > 0.3:
            logger.debug(
                f"Binary detection: File '{file_path}' skipped because "
                f"decoded control character ratio {ratio:.2f} exceeds threshold 0.30."
            )
            return False

        return True
    except Exception as e:
        logger.debug(
            f"Binary detection error: File '{file_path}' skipped due to error: {e}"
        )
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
    if not is_text_file(file_path, binary_exts):
        return False

    logger.debug(f"File filter: File '{file_path}' is supported and accepted.")
    return True
