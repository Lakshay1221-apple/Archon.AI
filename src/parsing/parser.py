"""Module for parsing repositories and extracting file content."""

import json
import logging
from pathlib import Path

from src.ingestion.file_filter import is_supported_file

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 1
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".txt": "text",
    ".sh": "bash",
    ".sql": "sql",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".go": "go",
    ".rs": "rust",
}


def get_language(suffix: str) -> str:
    """
    Returns language name from extension.
    """
    return EXTENSION_TO_LANGUAGE.get(
        suffix.lower(),
        "unknown",
    )


def parse_repository(repo_path: str):
    """
    Parse repository files and generate dataset records.

    Returns:
        records, stats
    """

    repo_path_obj = Path(repo_path)

    if not repo_path_obj.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {repo_path}"
        )

    repo_name = repo_path_obj.name

    records = []

    files_found = 0
    supported_files = 0
    skipped_files = 0

    for path in repo_path_obj.rglob("*"):

        if not path.is_file():
            continue

        files_found += 1

        if not is_supported_file(path):
            skipped_files += 1
            continue

        try:
            file_size = path.stat().st_size
        except Exception as e:
            logger.warning(
                f"Failed getting size for {path}: {e}"
            )
            skipped_files += 1
            continue

        if file_size > MAX_FILE_SIZE_BYTES:
            logger.warning(
                f"Skipping large file: {path}"
            )
            skipped_files += 1
            continue

        try:

            try:
                content = path.read_text(
                    encoding="utf-8"
                )
            except UnicodeDecodeError:
                content = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

            record = {
                "repo": repo_name,
                "path": str(
                    path.relative_to(repo_path_obj)
                ),
                "file_name": path.name,
                "language": get_language(
                    path.suffix
                ),
                "extension": path.suffix,
                "size_bytes": file_size,
                "content": content,
            }

            records.append(record)
            supported_files += 1

        except Exception as e:
            logger.warning(
                f"Failed reading {path}: {e}"
            )
            skipped_files += 1

    stats = {
        "files_found": files_found,
        "supported_files": supported_files,
        "skipped_files": skipped_files,
        "records_generated": len(records),
    }

    return records, stats


def save_dataset(
    records: list[dict],
    output_path: str,
) -> None:
    """
    Save dataset records as JSON.
    """

    output = Path(output_path)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            records,
            f,
            indent=4,
            ensure_ascii=False,
        )

    logger.info(
        f"Successfully saved {len(records)} records "
        f"to {output_path}"
    )