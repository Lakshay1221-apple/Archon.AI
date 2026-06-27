"""Main entry point for Archon AI universal repository ingestion with centralized logging."""

import argparse
import sys
import time
from pathlib import Path
from src.ingestion.clone_repo import clone_repository, extract_repo_name
from src.parsing.parser import parse_repository, save_dataset
from src.utils.config import load_config
from src.utils.logger import get_logger, SESSION_ID

# Initialize logger
logger = get_logger("main")


def main() -> None:
    """Orchestrates the universal repository ingestion, parsing, and execution timings logging."""
    parser = argparse.ArgumentParser(
        description="Archon AI: Universal Ingestion Pipeline with Tracing"
    )
    parser.add_argument(
        "repo_url",
        type=str,
        help="The GitHub/Git repository URL to ingest.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/processed/ast_dataset.json",
        help="Output path for the generated AST dataset JSON file.",
    )

    args = parser.parse_args()

    total_start = time.perf_counter()

    try:
        # Log Pipeline start and Session ID
        logger.info(
            f"Universal ingestion pipeline started. Session ID: [SESSION_ID={SESSION_ID}]"
        )

        # Load configurations
        config = load_config()

        # 1. Clone repository
        repo_name = extract_repo_name(args.repo_url)
        logger.info(f"Selected repository: '{repo_name}' from URL: '{args.repo_url}'")

        clone_start = time.perf_counter()
        local_path = clone_repository(args.repo_url)
        clone_duration = time.perf_counter() - clone_start
        logger.info(f"Cloning phase complete in {clone_duration:.2f}s.")

        # 2. Parse repository
        parse_start = time.perf_counter()
        records, stats = parse_repository(local_path, config=config)
        parse_duration = time.perf_counter() - parse_start
        logger.info(f"Parsing phase complete in {parse_duration:.2f}s.")

        # 3. Save datasets
        save_start = time.perf_counter()

        # Save complete AST dataset
        save_dataset(records, args.output)

        # Filter and save dedicated Embedding dataset
        embedding_records = [r for r in records if r.get("embedding_candidate")]
        embedding_output_path = str(Path(args.output).parent / "embedding_dataset.json")
        save_dataset(embedding_records, embedding_output_path)

        save_duration = time.perf_counter() - save_start
        logger.info(f"Dataset saving phase complete in {save_duration:.2f}s.")

        total_duration = time.perf_counter() - total_start

        # 4. Log timings (Performance Logging)
        logger.info(
            f"Performance Metrics:\n"
            f"  Clone Time: {clone_duration:.1f}s\n"
            f"  Parse Time: {parse_duration:.1f}s\n"
            f"  Dataset Save Time: {save_duration:.1f}s\n"
            f"  Total Runtime: {total_duration:.1f}s"
        )

        # 5. Print statistics to console
        print(f"\nFiles Parsed: {stats['files_processed']}")
        print(f"Files Ignored: {stats.get('files_ignored', 0)}\n")

        ignored_by_rule = stats.get("ignored_by_rule", {})
        if ignored_by_rule:
            print("Ignored:")
            for rule, count in sorted(ignored_by_rule.items(), key=lambda item: item[1], reverse=True):
                print(f"  {rule}: {count}")
            print()

        print("--- AST Optimization Report ---")
        print(f"Total AST records (raw): {stats['total_ast_records']}")
        print(f"Total embedding candidates: {stats['total_embedding_candidates']}")
        print(f"Number of imports removed: {stats['imports_removed']}")
        print(f"Number of exports removed: {stats['exports_removed']}")
        print(f"Duplicate symbols removed/merged: {stats['duplicates_removed']}")
        print(
            f"Parent-child relationships discovered: {stats['parent_child_relationships']}\n"
        )

        print("Symbol Type Distribution:")
        dist = stats.get("symbol_type_distribution", {})
        for stype, count in sorted(dist.items()):
            print(f"  - {stype}: {count}")

        print(f"\nFallback Chunks: {stats['fallback_chunks']}")
        print(f"Parse Failures: {stats['parse_failures']}")
        print(f"\nTotal Dataset Symbols: {stats['total_symbols']}")

    except Exception as e:
        logger.error(f"Pipeline failed in session {SESSION_ID}: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
