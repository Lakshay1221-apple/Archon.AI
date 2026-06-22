"""Main entry point for Archon AI universal repository ingestion."""

import argparse
import logging
import sys
from src.ingestion.clone_repo import clone_repository, extract_repo_name
from src.parsing.parser import parse_repository, save_dataset
from src.utils.config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("archon_ai")


def main() -> None:
    """Orchestrates the universal repository ingestion and parsing pipeline."""
    parser = argparse.ArgumentParser(
        description="Archon AI: Universal Repository Ingestion & Parsing"
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
        default="data/processed/repository_dataset.json",
        help="Output path for the generated dataset JSON file.",
    )

    args = parser.parse_args()

    try:
        # Load ingestion configuration
        config = load_config()

        # 1. Clone or pull the repository
        repo_name = extract_repo_name(args.repo_url)
        logger.info(f"Starting ingestion process for repository: {repo_name}")
        local_path = clone_repository(args.repo_url)

        # 2. Parse the repository using config settings
        logger.info(f"Parsing files universally from: {local_path}")
        records, stats = parse_repository(local_path, config=config)

        # 3. Save generated dataset
        logger.info(f"Saving generated dataset to: {args.output}")
        save_dataset(records, args.output)

        # 4. Print detailed statistics to console
        print(f"\nRepository: {repo_name}\n")
        print(f"Files Found: {stats['files_found']}")
        print(f"Files Processed: {stats['files_processed']}")
        print(f"Files Skipped: {stats['skipped_files']}")
        print(f"Binary Files Skipped: {stats['binary_skipped']}")
        print(f"Large Files Skipped: {stats['large_skipped']}")
        print(f"Large Files Chunked: {stats['large_chunked']}")
        print(f"Ignored Directories Checked: {len(stats['ignored_directories'])}")
        print(
            f"Languages Detected: {', '.join(stats['languages_detected']) if stats['languages_detected'] else 'None'}"
        )
        print(f"Records Generated: {stats['records_generated']}")

    except Exception as e:
        logger.error(
            f"Failed to complete universal ingestion pipeline: {e}", exc_info=True
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
