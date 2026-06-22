"""Module for parsing repositories and extracting file content for the dataset."""

import json
import logging
from pathlib import Path
from src.ingestion.file_filter import is_supported_file

logger = logging.getLogger(__name__)

# File size limit in megabytes
MAX_FILE_SIZE_MB = 1
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Mapping from file extension to language name
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".txt": "text",
}


def get_language(suffix: str) -> str:
    """Returns the language name corresponding to the file suffix.

    Args:
        suffix: The file suffix/extension (e.g., '.py').

    Returns:
        The matching language string, or 'unknown'.
    """
    return EXTENSION_TO_LANGUAGE.get(suffix.lower(), "unknown")


def parse_repository(repo_path: str) -> tuple[list[dict], dict]:
    """Walks the repository, filters supported files, reads content, and builds the dataset.

    Args:
        repo_path: The local directory path of the cloned repository.

    Returns:
        A tuple containing:
            - A list of parsed record dictionaries following the schema.
            - A dictionary containing collection statistics:
                - 'files_found': Total files discovered in the directory tree.
                - 'supported_files': Number of files that match filters.
                - 'skipped_files': Number of files skipped (ignored, too large, read error).
                - 'records_generated': Number of successfully parsed records.

    Raises:
        FileNotFoundError: If the repository path does not exist.
    """
    repo_path_obj = Path(repo_path)
    if not repo_path_obj.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    # Repository name is the folder name
    repo_name = repo_path_obj.name

    records: list[dict] = []
    files_found = 0
    supported_files = 0
    skipped_files = 0

    # Walk the directory recursively
    for path in repo_path_obj.rglob("*"):
        if path.is_file():
            files_found += 1
            if is_supported_file(path):
                # Check size
                try:
                    file_size = path.stat().st_size
                except Exception as e:
                    logger.warning(f"Could not get file size for {path}: {e}")
                    skipped_files += 1
                    continue

                if file_size > MAX_FILE_SIZE_BYTES:
                    logger.warning(
                        f"Skipping {path} as it exceeds the size limit "
                        f"({file_size} bytes > {MAX_FILE_SIZE_BYTES} bytes)"
                    )
                    skipped_files += 1
                    continue

                supported_files += 1
                try:
                    # UTF-8 read
                    content = path.read_text(encoding="utf-8")
                    records.append(
                        {
                            "repo": repo_name,
                            "path": str(path.relative_to(repo_path_obj)),
                            "language": get_language(path.suffix),
                            "file_name": path.name,
                            "content": content,
                        }
                    )
                except (UnicodeDecodeError, PermissionError, IOError) as e:
                    logger.warning(f"Skipping file {path} due to read error: {e}")
                    skipped_files += 1
            else:
                skipped_files += 1

    stats = {
        "files_found": files_found,
        "supported_files": supported_files,
        "skipped_files": skipped_files,
        "records_generated": len(records),
    }

    return records, stats


def save_dataset(records: list[dict], output_path: str) -> None:
    """Saves the generated dataset records to a JSON file.

    Creates any parent directories of output_path if they do not exist.

    Args:
        records: A list of record dictionaries.
        output_path: The file path where the dataset should be saved.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=4, ensure_ascii=False)
    logger.info(
        f"Successfully saved dataset containing {len(records)} records to {output_path}."
    )
