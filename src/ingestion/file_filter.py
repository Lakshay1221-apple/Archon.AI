"""File filtering utilities for Archon AI, supporting universal codebases."""

import fnmatch
from pathlib import Path
from typing import Optional
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_ignore_pattern(
    file_path: Path,
    repo_path: Path = None,
    ignored_dirs: list[str] = None,
) -> Optional[str]:
    """Determines which ignore pattern (if any) matches the file path.

    Supports:
        - Archon's own output directories (data/processed/ and data/chroma_db/)
        - Suffix/extension checks (e.g. '.pyc', '.log')
        - Wildcard pattern matching (e.g. '*.log', '**/logs/*') using fnmatch
        - Exact directory segment matching (e.g. if segment '.git' is in path parts)
        - Subpath prefix matching (e.g. if path is inside 'coverage/' or 'htmlcov/')

    Args:
        file_path: Path of the file.
        repo_path: Optional repository root path.
        ignored_dirs: Optional list of ignored directories/patterns.

    Returns:
        The matching ignore pattern string, or None if the file should not be ignored.
    """
    # 1. Project-aware check: Ignore only Archon's own generated output directories.
    # We resolve the project root relative to this file's position (Archon/src/ingestion/file_filter.py).
    # Project root is 2 levels up from src/ingestion.
    project_root = Path(__file__).resolve().parents[2]
    archon_processed = project_root / "data" / "processed"
    archon_chroma = project_root / "data" / "chroma_db"

    try:
        abs_path = file_path.resolve()
        abs_processed = archon_processed.resolve()
        abs_chroma = archon_chroma.resolve()
        if abs_path.is_relative_to(abs_processed) or abs_path.is_relative_to(abs_chroma):
            return "archon_output_dir"
    except Exception:
        # Fallback comparison if resolution fails
        if file_path.is_relative_to(archon_processed) or file_path.is_relative_to(archon_chroma):
            return "archon_output_dir"

    if not ignored_dirs:
        return None

    # Get relative path to repo_path to perform subpath and wildcard checks
    if repo_path:
        try:
            rel_path = file_path.relative_to(repo_path)
        except ValueError:
            rel_path = file_path
    else:
        rel_path = file_path

    rel_path_str = str(rel_path).replace("\\", "/")
    file_name = file_path.name
    parts = rel_path.parts

    for pattern in ignored_dirs:
        if not pattern:
            continue

        pattern_clean = pattern.replace("\\", "/").strip()

        # A. Suffix/extension check (e.g. '.log', '.pyc')
        if pattern_clean.startswith(".") and "/" not in pattern_clean and "*" not in pattern_clean:
            if file_path.suffix.lower() == pattern_clean.lower():
                return pattern

        # B. Wildcard pattern matching (e.g. '*.log', 'data/processed/*')
        if "*" in pattern_clean or "?" in pattern_clean:
            # Check filename match
            if fnmatch.fnmatch(file_name.lower(), pattern_clean.lower()):
                return pattern
            # Check relative path match
            if fnmatch.fnmatch(rel_path_str.lower(), pattern_clean.lower()):
                return pattern
            # Check subfolders (e.g., if rel_path_str is "some/dir/file.log" and pattern is "*.log")
            if fnmatch.fnmatch(rel_path_str.lower(), f"**/{pattern_clean.lower()}"):
                return pattern
            continue

        # C. Exact segment or subpath prefix checks
        is_dir_pattern = pattern_clean.endswith("/")
        clean_pat = pattern_clean[:-1] if is_dir_pattern else pattern_clean

        if "/" not in clean_pat:
            # Segment matches directory exactly
            if clean_pat in parts:
                return pattern
        else:
            # Matches relative subpath prefix or is a subpath of segments
            if rel_path_str == clean_pat or rel_path_str.startswith(clean_pat + "/"):
                return pattern

            pat_parts = clean_pat.split("/")
            n_pat = len(pat_parts)
            n_parts = len(parts)
            for idx in range(n_parts - n_pat + 1):
                if list(parts[idx : idx + n_pat]) == pat_parts:
                    return pattern

    return None


def should_ignore_directory(
    file_path: Path,
    repo_path: Path = None,
    ignored_dirs: list[str] = None,
) -> bool:
    """Checks if a file path is inside any of the ignored directories or patterns.

    Args:
        file_path: Path of the file.
        repo_path: Optional repository root path.
        ignored_dirs: Optional list of ignored directories.

    Returns:
        True if the file is inside an ignored directory/pattern, False otherwise.
    """
    matched_pattern = get_ignore_pattern(file_path, repo_path, ignored_dirs)
    if matched_pattern is not None:
        logger.debug(
            f"Directory/File ignore match: File '{file_path}' skipped because "
            f"it matched ignore pattern '{matched_pattern}'."
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
