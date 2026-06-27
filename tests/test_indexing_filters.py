"""Unit and integration tests verifying retrieval noise reduction and indexing filters."""

import json
from pathlib import Path
from src.ingestion.file_filter import get_ignore_pattern, should_ignore_directory
from src.utils.config import load_config


def test_get_ignore_pattern_unit():
    """Verify that get_ignore_pattern correctly identifies ignored patterns across different rules."""
    config = load_config()
    ignored_dirs = config.get("ignored_directories", [])

    # Project root mock for repo matching
    repo_path = Path("/home/lakshay/Archon AI")

    # 1. Classic ignored directories (node_modules, .git, .venv)
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/node_modules/lodash/index.js"), repo_path, ignored_dirs) == "node_modules"
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/.venv/bin/python"), repo_path, ignored_dirs) == ".venv"
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/.git/config"), repo_path, ignored_dirs) == ".git"

    # 2. Log files
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/logs/archon.log"), repo_path, ignored_dirs) in ("logs", "*.log")
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/debug.log"), repo_path, ignored_dirs) == "*.log"

    # 3. Python cache
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/src/__pycache__/main.pyc"), repo_path, ignored_dirs) in ("__pycache__", "*.pyc")
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/src/main.pyc"), repo_path, ignored_dirs) == "*.pyc"

    # 4. Lock files
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/poetry.lock"), repo_path, ignored_dirs) == "*.lock"
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/package-lock.json"), repo_path, ignored_dirs) == "*lock.json"
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/pnpm-lock.yaml"), repo_path, ignored_dirs) == "*lock.yaml"

    # 5. Coverage reports
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/coverage/lcov.info"), repo_path, ignored_dirs) == "coverage"
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/htmlcov/index.html"), repo_path, ignored_dirs) == "htmlcov"

    # 6. Valid files should NOT be ignored
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/src/main.py"), repo_path, ignored_dirs) is None
    assert get_ignore_pattern(Path("/home/lakshay/Archon AI/README.md"), repo_path, ignored_dirs) is None


def test_archon_own_output_ignored():
    """Verify that only Archon's own generated directories are ignored, and ML subdirectories are not."""
    config = load_config()
    ignored_dirs = config.get("ignored_directories", [])

    # Archon's actual code/data directories
    project_root = Path(__file__).resolve().parents[1]
    archon_processed_file = project_root / "data" / "processed" / "ast_dataset.json"
    archon_chroma_file = project_root / "data" / "chroma_db" / "chroma.sqlite3"

    # These should be matched as archon_output_dir
    assert get_ignore_pattern(archon_processed_file, project_root, ignored_dirs) == "archon_output_dir"
    assert get_ignore_pattern(archon_chroma_file, project_root, ignored_dirs) == "archon_output_dir"
    assert should_ignore_directory(archon_processed_file, project_root, ignored_dirs) is True

    # Legitimate ML codebase folders with similar subpaths should NOT be ignored
    ml_repo_path = Path("/home/lakshay/Archon AI/data/repositories/ML-Project")
    ml_processed_file = ml_repo_path / "data" / "processed" / "valid_ml_dataset.csv"
    ml_chroma_file = ml_repo_path / "data" / "chroma_db" / "collection.bin"

    assert get_ignore_pattern(ml_processed_file, ml_repo_path, ignored_dirs) is None
    assert get_ignore_pattern(ml_chroma_file, ml_repo_path, ignored_dirs) is None
    assert should_ignore_directory(ml_processed_file, ml_repo_path, ignored_dirs) is False


def test_parsed_datasets_contain_no_noise():
    """Assert that if ast_dataset.json or embedding_dataset.json exist, they contain no log/cache/venv/lock paths."""
    project_root = Path(__file__).resolve().parents[1]
    ast_path = project_root / "data" / "processed" / "ast_dataset.json"
    emb_path = project_root / "data" / "processed" / "embedding_dataset.json"

    # We only run checks if files have been generated
    for path in (ast_path, emb_path):
        if not path.exists():
            continue

        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)

        for record in records:
            file_path = record["file"]
            file_name = Path(file_path).name

            # No log files
            assert "logs/" not in file_path, f"Found noise path: {file_path}"
            assert not file_path.endswith(".log"), f"Found log file: {file_path}"

            # No git metadata
            assert ".git/" not in file_path, f"Found git metadata: {file_path}"

            # No virtual environment
            assert ".venv/" not in file_path, f"Found virtual env: {file_path}"
            assert "venv/" not in file_path, f"Found virtual env: {file_path}"

            # No python cache
            assert "__pycache__/" not in file_path, f"Found python cache: {file_path}"
            assert not file_path.endswith(".pyc"), f"Found compiled python: {file_path}"

            # No lock files
            assert not file_path.endswith(".lock"), f"Found lock file: {file_path}"
            assert "package-lock.json" not in file_name, f"Found lock file: {file_path}"
            assert "pnpm-lock.yaml" not in file_name, f"Found lock file: {file_path}"

            # No coverage folders
            assert "coverage/" not in file_path, f"Found coverage folder: {file_path}"
            assert "htmlcov/" not in file_path, f"Found coverage folder: {file_path}"
