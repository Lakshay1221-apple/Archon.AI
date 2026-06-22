"""Main entry point for Archon AI Phase 1 Ingestion and Parsing."""

import argparse
import logging
import sys
from src.ingestion.clone_repo import clone_repository, extract_repo_name
from src.parsing.parser import parse_repository, save_dataset

# Configure standard logging to output cleanly
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("archon_ai")


def main() -> None:
    """Main execution function to ingest a repository and generate the dataset."""
    parser = argparse.ArgumentParser(
        description="Archon AI - Phase 1: Repository Ingestion and Dataset Generation"
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
        help="Output path for the generated repository dataset JSON file.",
    )

    args = parser.parse_args()

    try:
        # 1. Extract name and clone repository
        repo_name = extract_repo_name(args.repo_url)
        logger.info(f"Starting ingestion process for repository: {repo_name}")

        local_path = clone_repository(args.repo_url)

        # 2. Parse files and track metrics
        logger.info(f"Parsing files from directory: {local_path}")
        records, stats = parse_repository(local_path)

        # 3. Save dataset
        logger.info(f"Saving dataset to: {args.output}")
        save_dataset(records, args.output)

        # 4. Print clean statistics to stdout as requested
        print(f"\nRepository: {repo_name}\n")
        print(f"Files Found: {stats['files_found']}")
        print(f"Supported: {stats['supported_files']}")
        print(f"Skipped: {stats['skipped_files']}")
        print(f"\nRecords Generated: {stats['records_generated']}")

    except Exception as e:
        logger.error(f"Failed to complete ingestion pipeline: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
