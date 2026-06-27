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
    parser.add_argument(
        "--allow-self-indexing",
        action="store_true",
        help="Allow Archon to index its own codebase.",
    )
    parser.add_argument(
        "--force-reindex",
        action="store_true",
        help="Force reindexing by cleaning all previous data first.",
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

        # Self-indexing check
        def is_self_indexing(url: str, name: str) -> bool:
            if name in ("Archon.AI-", "Archon AI", "archon-ai"):
                return True
            try:
                target_path = Path(url).resolve()
                if target_path == Path.cwd().resolve():
                    return True
            except Exception:
                pass
            try:
                import git
                repo = git.Repo(Path.cwd())
                origin_url = repo.remote("origin").url
                def norm(u):
                    u = u.strip()
                    if u.endswith(".git"):
                        u = u[:-4]
                    return u.lower().rstrip("/")
                if norm(url) == norm(origin_url):
                    return True
            except Exception:
                pass
            return False

        if is_self_indexing(args.repo_url, repo_name) and not args.allow_self_indexing:
            raise ValueError(
                f"Ingestion blocked: Archon cannot index its own codebase ('{repo_name}') unless "
                "explicitly overridden with --allow-self-indexing."
            )

        # Registry check & re-index logic
        from src.repository.repository_manager import (
            list_repositories,
            register_repository,
            delete_repository,
            update_repository_metadata
        )

        if repo_name in list_repositories():
            if args.force_reindex:
                logger.info(f"Repository '{repo_name}' is already indexed. Cleaning up old data first...")
                delete_repository(repo_name)
            else:
                raise ValueError(
                    f"Repository '{repo_name}' is already indexed. Use --force-reindex to rebuild it."
                )

        # Register repository in 'indexing' status
        register_repository(args.repo_url)

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

        if args.output == "data/processed/ast_dataset.json":
            output_dir = Path("data/processed") / repo_name
        else:
            output_dir = Path(args.output).parent

        output_dir.mkdir(parents=True, exist_ok=True)
        ast_output_path = output_dir / "ast_dataset.json"
        embedding_output_path = output_dir / "embedding_dataset.json"

        # Save complete AST dataset
        save_dataset(records, str(ast_output_path))

        # Filter and save dedicated Embedding dataset
        embedding_records = [r for r in records if r.get("embedding_candidate")]
        save_dataset(embedding_records, str(embedding_output_path))

        save_duration = time.perf_counter() - save_start
        logger.info(f"Dataset saving phase complete in {save_duration:.2f}s.")

        # Update metadata stats in registry
        from collections import Counter
        from datetime import datetime
        
        languages = [r.get("language", "unknown") for r in records]
        language_breakdown = dict(Counter(languages))
        indexed_at = datetime.utcnow().isoformat() + "Z"

        update_repository_metadata(
            repo_name,
            status="indexed",
            symbol_count=len(records),
            file_count=stats.get("files_processed", 0),
            embedding_count=len(embedding_records),
            language_breakdown=language_breakdown,
            indexed_at=indexed_at
        )

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

