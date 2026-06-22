"""Module for parsing repositories and extracting text content universally."""

import json
import logging
from pathlib import Path
from src.ingestion.file_filter import should_ignore_directory, is_text_file
from src.parsing.language_detector import detect_language
from src.utils.config import load_config

logger = logging.getLogger(__name__)


def parse_repository(repo_path: str, config: dict = None) -> tuple[list[dict], dict]:
    """Parses repository files, performs text detection, chunking, and language detection.

    Args:
        repo_path: The local directory path of the cloned repository.
        config: Optional configuration dictionary.

    Returns:
        A tuple containing:
            - A list of parsed record dictionaries following the schema.
            - A dictionary containing collection statistics.

    Raises:
        FileNotFoundError: If the repository path does not exist.
    """
    repo_path_obj = Path(repo_path)
    if not repo_path_obj.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    if config is None:
        config = load_config()

    repo_name = repo_path_obj.name
    records: list[dict] = []

    # Config parameters
    ignored_dirs = config.get("ignored_directories", [])
    binary_exts = config.get("binary_extensions", [])
    max_file_size_mb = config.get("max_file_size_mb", 5)
    max_file_size_bytes = max_file_size_mb * 1024 * 1024
    chunk_size_mb = config.get("chunk_size_mb", 1)
    chunk_size_chars = chunk_size_mb * 1024 * 1024

    # Statistics tracking
    files_found = 0
    files_processed = 0
    skipped_files = 0
    binary_skipped = 0
    large_skipped = 0
    large_chunked = 0
    ignored_directory_skips = 0
    languages_detected: set[str] = set()

    for path in repo_path_obj.rglob("*"):
        if not path.is_file():
            continue

        files_found += 1

        # 1. Ignore common directories
        if should_ignore_directory(path, repo_path_obj, ignored_dirs):
            ignored_directory_skips += 1
            skipped_files += 1
            continue

        # 2. Skip binary files
        if not is_text_file(path, binary_exts):
            binary_skipped += 1
            skipped_files += 1
            continue

        # 3. Check file size
        try:
            file_size = path.stat().st_size
        except Exception as e:
            logger.warning(f"Failed getting size for {path}: {e}")
            skipped_files += 1
            continue

        # Skip files that are excessively large to prevent memory depletion (> 50MB)
        if file_size > 50 * 1024 * 1024:
            logger.warning(f"Skipping excessively large file (>50MB): {path}")
            large_skipped += 1
            skipped_files += 1
            continue

        # 4. Safe read
        try:
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Failed reading file content for {path}: {e}")
            skipped_files += 1
            continue

        # 5. Language detection
        lang = detect_language(path, content)
        languages_detected.add(lang)

        # 6. Extract paths
        relative_path = str(path.relative_to(repo_path_obj))
        file_name = path.name
        suffix = path.suffix

        # Determine if file exceeds size limit and needs to be chunked
        is_large_file = file_size > max_file_size_bytes

        if is_large_file:
            large_chunked += 1
            num_chunks = (len(content) + chunk_size_chars - 1) // chunk_size_chars
            for i in range(num_chunks):
                chunk_content = content[
                    i * chunk_size_chars : (i + 1) * chunk_size_chars
                ]
                record = {
                    "repo": repo_name,
                    "path": f"{relative_path} [chunk {i + 1}]",
                    "file_name": f"{file_name} [chunk {i + 1}]",
                    "language": lang,
                    "extension": suffix,
                    "size_bytes": len(chunk_content.encode("utf-8", errors="ignore")),
                    "content": chunk_content,
                    "chunk_index": i,
                    "total_chunks": num_chunks,
                    # Placeholder for AST fields for backward compatibility
                    "imports": [],
                    "functions": [],
                    "classes": [],
                    "symbols": [],
                }
                records.append(record)
        else:
            record = {
                "repo": repo_name,
                "path": relative_path,
                "file_name": file_name,
                "language": lang,
                "extension": suffix,
                "size_bytes": file_size,
                "content": content,
                # Placeholder for AST fields for backward compatibility
                "imports": [],
                "functions": [],
                "classes": [],
                "symbols": [],
            }
            records.append(record)

        files_processed += 1

    stats = {
        "files_found": files_found,
        "files_processed": files_processed,
        "skipped_files": skipped_files,
        "binary_skipped": binary_skipped,
        "large_skipped": large_skipped,
        "large_chunked": large_chunked,
        "ignored_directory_skips": ignored_directory_skips,
        "ignored_directories": ignored_dirs,
        "languages_detected": sorted(list(languages_detected)),
        "records_generated": len(records),
    }

    return records, stats


def save_dataset(records: list[dict], output_path: str) -> None:
    """Saves generated dataset records to a JSON file.

    Args:
        records: A list of record dictionaries.
        output_path: The file path where the dataset should be saved.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=4, ensure_ascii=False)
    logger.info(f"Successfully saved {len(records)} records to {output_path}")
