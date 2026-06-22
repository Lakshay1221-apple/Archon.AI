"""Module for parsing repositories and extracting semantic symbols universally."""

import json
from pathlib import Path
from src.ingestion.file_filter import should_ignore_directory, is_text_file
from src.parsing.language_detector import detect_language
from src.utils.config import load_config
from src.utils.logger import get_logger
from src.ast_parser.parser import parse_file

logger = get_logger(__name__)


def parse_repository(repo_path: str, config: dict = None) -> tuple[list[dict], dict]:
    """Parses repository files, performs text detection, and extracts semantic AST symbols.

    Args:
        repo_path: The local directory path of the cloned repository.
        config: Optional configuration dictionary.

    Returns:
        A tuple containing:
            - A list of parsed record dictionaries following the CodeSymbol schema.
            - A dictionary containing collection and parsing statistics.

    Raises:
        FileNotFoundError: If the repository path does not exist.
    """
    repo_path_obj = Path(repo_path)
    if not repo_path_obj.exists():
        logger.error(f"Failed to parse repository: path '{repo_path}' does not exist.")
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    if config is None:
        config = load_config()

    repo_name = repo_path_obj.name
    records: list[dict] = []

    # Config parameters
    ignored_dirs = config.get("ignored_directories", [])
    binary_exts = config.get("binary_extensions", [])

    # Statistics tracking
    files_found = 0
    files_processed = 0
    skipped_files = 0
    binary_skipped = 0
    large_skipped = 0
    ignored_directory_skips = 0
    languages_detected: set[str] = set()

    # Symbol counts (for final dataset)
    functions_count = 0
    classes_count = 0
    methods_count = 0
    structs_count = 0
    enums_count = 0
    traits_count = 0
    fallback_chunks_count = 0
    parse_failures_count = 0
    total_symbols_count = 0

    # Optimization/Validation metrics
    total_ast_records_count = 0
    total_embedding_candidates_count = 0
    imports_removed_count = 0
    exports_removed_count = 0
    duplicates_removed_count = 0
    parent_child_relationships_count = 0
    symbol_type_distribution: dict[str, int] = {}

    logger.info(f"Parsing repository '{repo_name}' recursively at '{repo_path}'...")

    for path in repo_path_obj.rglob("*"):
        if not path.is_file():
            continue

        files_found += 1
        logger.debug(f"File discovered: {path}")

        # 1. Ignore common directories
        if should_ignore_directory(path, repo_path_obj, ignored_dirs):
            logger.debug(f"File skipped: '{path}' matches ignored directories list.")
            ignored_directory_skips += 1
            skipped_files += 1
            continue

        # 2. Skip binary files
        if not is_text_file(path, binary_exts):
            logger.info(f"File skipped: '{path}' is classified as a binary file.")
            binary_skipped += 1
            skipped_files += 1
            continue

        # 3. Check file size
        try:
            file_size = path.stat().st_size
        except Exception as e:
            logger.warning(f"File skipped: Failed getting size for '{path}': {e}")
            skipped_files += 1
            continue

        # Skip files that are excessively large to prevent memory depletion (> 50MB)
        if file_size > 50 * 1024 * 1024:
            logger.warning(
                f"File skipped: '{path}' exceeds absolute safety limit of 50MB (size: {file_size} bytes)."
            )
            large_skipped += 1
            skipped_files += 1
            continue

        # 4. Safe read
        try:
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                logger.warning(
                    f"Unicode decoding issue in '{path}'. Retrying read with characters ignored."
                )
                content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.error(
                f"File skipped: Failed to read content of '{path}': {e}",
                exc_info=True,
            )
            skipped_files += 1
            continue

        # 5. Language detection
        lang = detect_language(path, content)
        languages_detected.add(lang)
        logger.info(f"File accepted: '{path}' (Detected language: {lang})")

        # 6. Extract paths
        relative_path = str(path.relative_to(repo_path_obj))

        # 7. Extract semantic symbols using AST parser orchestrator
        try:
            symbols = parse_file(
                repo_name=repo_name,
                file_path=path,
                relative_path=relative_path,
                language=lang,
                content=content,
            )

            total_ast_records_count += len(symbols)

            # Deduplication and filtering pass for imports and exports
            file_imports_removed = 0
            file_exports_removed = 0
            file_duplicates_removed = 0

            # Collect export names to match with candidate symbols in the same file
            file_export_names = set()
            for sym in symbols:
                if sym.symbol_type == "export":
                    file_exports_removed += 1
                    # Clean/resolve export names
                    names = [n.strip() for n in sym.symbol_name.split(",") if n.strip()]
                    for name in names:
                        file_export_names.add(name)
                elif sym.symbol_type == "import":
                    file_imports_removed += 1

            # Build final candidate symbols list (excluding standalone imports/exports)
            final_file_symbols = []
            for sym in symbols:
                if sym.symbol_type in ("import", "export"):
                    continue

                # Set exported = True if it matches any clean export name
                base_name = sym.symbol_name.split(".")[0]
                if (
                    sym.symbol_name in file_export_names
                    or base_name in file_export_names
                ):
                    if not sym.exported:
                        sym.exported = True
                        file_duplicates_removed += 1

                final_file_symbols.append(sym)

            # Save processed symbols
            file_had_failure = False
            for sym in final_file_symbols:
                records.append(sym.to_dict())

                if sym.metadata.get("ast_parse_failure"):
                    file_had_failure = True

                # Stats reporting aggregation
                stype = sym.symbol_type
                symbol_type_distribution[stype] = (
                    symbol_type_distribution.get(stype, 0) + 1
                )

                if stype in ("function", "async_function", "arrow_function"):
                    functions_count += 1
                elif stype in ("class", "interface"):
                    classes_count += 1
                elif stype == "method":
                    methods_count += 1
                elif stype == "struct":
                    structs_count += 1
                elif stype == "enum":
                    enums_count += 1
                elif stype == "trait":
                    traits_count += 1
                elif stype == "chunk":
                    fallback_chunks_count += 1

                if sym.parent_symbol is not None:
                    parent_child_relationships_count += 1

                if sym.embedding_candidate:
                    total_embedding_candidates_count += 1

            if file_had_failure:
                parse_failures_count += 1

            total_symbols_count += len(final_file_symbols)

            # Aggregate validation counters
            imports_removed_count += file_imports_removed
            exports_removed_count += file_exports_removed
            duplicates_removed_count += file_duplicates_removed

        except Exception as e:
            logger.error(
                f"Unexpected exception running AST orchestrator on '{relative_path}': {e}",
                exc_info=True,
            )
            parse_failures_count += 1

        files_processed += 1

    stats = {
        "files_found": files_found,
        "files_processed": files_processed,
        "skipped_files": skipped_files,
        "binary_skipped": binary_skipped,
        "large_skipped": large_skipped,
        "ignored_directory_skips": ignored_directory_skips,
        "ignored_directories": ignored_dirs,
        "languages_detected": sorted(list(languages_detected)),
        # AST statistics
        "functions": functions_count,
        "classes": classes_count,
        "methods": methods_count,
        "structs": structs_count,
        "enums": enums_count,
        "traits": traits_count,
        "fallback_chunks": fallback_chunks_count,
        "parse_failures": parse_failures_count,
        "total_symbols": total_symbols_count,
        "records_generated": total_symbols_count,
        "large_chunked": 1 if fallback_chunks_count > 0 else 0,
        # Optimization/Validation metrics
        "total_ast_records": total_ast_records_count,
        "total_embedding_candidates": total_embedding_candidates_count,
        "imports_removed": imports_removed_count,
        "exports_removed": exports_removed_count,
        "duplicates_removed": duplicates_removed_count,
        "parent_child_relationships": parent_child_relationships_count,
        "symbol_type_distribution": symbol_type_distribution,
    }

    return records, stats


def save_dataset(records: list[dict], output_path: str) -> None:
    """Saves generated dataset records to a JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=4, ensure_ascii=False)
    logger.info(f"Successfully saved {len(records)} records to {output_path}")
