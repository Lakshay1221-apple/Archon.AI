"""Unit tests for universal repository ingestion, filtering, and parsing."""

from pathlib import Path
import pytest
from src.ingestion.file_filter import is_supported_file, should_ignore_directory
from src.parsing.language_detector import detect_language
from src.parsing.parser import parse_repository
from src.utils.config import load_config


@pytest.fixture
def mock_repo(tmp_path: Path) -> Path:
    """Sets up a temporary directory structure mimicking a mixed-language repository."""
    repo_dir = tmp_path / "mock-universal-repo"
    repo_dir.mkdir()

    # 1. Python ecosystem
    (repo_dir / "src").mkdir(parents=True, exist_ok=True)
    python_file = repo_dir / "src" / "main.py"
    python_file.write_text(
        "def my_func():\n    print('Hello World')\n", encoding="utf-8"
    )

    # Ignore python cache
    (repo_dir / "src" / "__pycache__").mkdir(exist_ok=True)
    (repo_dir / "src" / "__pycache__" / "main.cpython-312.pyc").write_bytes(
        b"\x00\x01\x02\x03binarydata"
    )

    # Ignore virtualenv
    (repo_dir / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
    (repo_dir / ".venv" / "bin" / "activate").write_text(
        "#!/bin/sh\nexport PATH\n", encoding="utf-8"
    )

    # 2. C/C++ ecosystem
    c_file = repo_dir / "src" / "helper.c"
    c_file.write_text("#include <stdio.h>\nvoid help() {}\n", encoding="utf-8")

    cpp_file = repo_dir / "src" / "core.cpp"
    cpp_file.write_text("#include <iostream>\n", encoding="utf-8")

    # Ignore binary object files
    o_file = repo_dir / "src" / "helper.o"
    o_file.write_bytes(b"\x7fELFbinaryo")

    # 3. Rust ecosystem
    (repo_dir / "rust-module" / "src").mkdir(parents=True, exist_ok=True)
    rust_file = repo_dir / "rust-module" / "src" / "lib.rs"
    rust_file.write_text("pub fn run() {}\n", encoding="utf-8")

    cargo_file = repo_dir / "rust-module" / "Cargo.toml"
    cargo_file.write_text('[package]\nname = "rust-module"\n', encoding="utf-8")

    # Ignore rust build artifacts
    (repo_dir / "rust-module" / "target" / "debug").mkdir(parents=True, exist_ok=True)
    (repo_dir / "rust-module" / "target" / "debug" / "rust-module").write_bytes(
        b"\x7fELFbinaryrust"
    )

    # 4. Java ecosystem
    java_file = repo_dir / "src" / "App.java"
    java_file.write_text("public class App {\n}\n", encoding="utf-8")

    # Ignore binary class files
    class_file = repo_dir / "src" / "App.class"
    class_file.write_bytes(b"\xca\xfe\xba\xbebinaryclass")

    # 5. JS/TS ecosystem
    (repo_dir / "frontend").mkdir(exist_ok=True)
    js_file = repo_dir / "frontend" / "app.js"
    js_file.write_text("const a = 10;\n", encoding="utf-8")

    ts_file = repo_dir / "frontend" / "index.ts"
    ts_file.write_text("let b: number = 20;\n", encoding="utf-8")

    # Ignore dependency dirs & build targets
    (repo_dir / "frontend" / "node_modules" / "some-pkg").mkdir(
        parents=True, exist_ok=True
    )
    (repo_dir / "frontend" / "node_modules" / "some-pkg" / "index.js").write_text(
        "console.log()", encoding="utf-8"
    )

    (repo_dir / "frontend" / "dist").mkdir(parents=True, exist_ok=True)
    (repo_dir / "frontend" / "dist" / "bundle.js").write_text(
        "dist-bundle-content", encoding="utf-8"
    )

    # 6. Mixed configurations & repository metadata
    dockerfile = repo_dir / "Dockerfile"
    dockerfile.write_text("FROM python:3.12\nCOPY . /app\n", encoding="utf-8")

    makefile = repo_dir / "Makefile"
    makefile.write_text("build:\n\tpython -m build\n", encoding="utf-8")

    readme = repo_dir / "README.md"
    readme.write_text("# Mock Universal Ingestion Repository\n", encoding="utf-8")

    license_file = repo_dir / "LICENSE"
    license_file.write_text("MIT License\n", encoding="utf-8")

    # 7. Subdirectory ignore check (e.g. .github/cache)
    (repo_dir / ".github" / "cache").mkdir(parents=True, exist_ok=True)
    cached_file = repo_dir / ".github" / "cache" / "cache_data.json"
    cached_file.write_text('{"cached": true}', encoding="utf-8")

    # 8. Obvious binary extensions to block
    image_file = repo_dir / "src" / "logo.png"
    image_file.write_bytes(b"\x89PNG\r\n\x1a\nimagebytes")

    # 9. Large file for chunking check (e.g. write > 2MB text to trigger chunking if size is lowered)
    # Write a 2.5MB file and we can configure config override
    large_file = repo_dir / "large_file.txt"
    large_file.write_text("A" * (2 * 1024 * 1024 + 100), encoding="utf-8")

    return repo_dir


def test_directory_ignores(mock_repo: Path) -> None:
    """Verifies that common dependency, cache, and build folders are correctly ignored."""
    config = load_config()
    ignored_dirs = config.get("ignored_directories", [])

    # Pruned directories
    assert (
        should_ignore_directory(
            mock_repo / "frontend" / "node_modules" / "some-pkg" / "index.js",
            mock_repo,
            ignored_dirs,
        )
        is True
    )
    assert (
        should_ignore_directory(
            mock_repo / "frontend" / "dist" / "bundle.js", mock_repo, ignored_dirs
        )
        is True
    )
    assert (
        should_ignore_directory(
            mock_repo / ".venv" / "bin" / "activate", mock_repo, ignored_dirs
        )
        is True
    )
    assert (
        should_ignore_directory(
            mock_repo / "src" / "__pycache__" / "main.cpython-312.pyc",
            mock_repo,
            ignored_dirs,
        )
        is True
    )
    assert (
        should_ignore_directory(
            mock_repo / "rust-module" / "target" / "debug" / "rust-module",
            mock_repo,
            ignored_dirs,
        )
        is True
    )

    # Subpath ignore patterns (.github/cache)
    assert (
        should_ignore_directory(
            mock_repo / ".github" / "cache" / "cache_data.json", mock_repo, ignored_dirs
        )
        is True
    )

    # Valid files should NOT be ignored
    assert (
        should_ignore_directory(mock_repo / "src" / "main.py", mock_repo, ignored_dirs)
        is False
    )
    assert (
        should_ignore_directory(mock_repo / "Dockerfile", mock_repo, ignored_dirs)
        is False
    )


def test_binary_exclusions(mock_repo: Path) -> None:
    """Verifies that binary extensions and binary contents are excluded."""
    config = load_config()

    # Blocklisted extension (.png)
    assert is_supported_file(mock_repo / "src" / "logo.png", mock_repo, config) is False

    # Blocklisted extension (.o, .class, .pyc)
    assert is_supported_file(mock_repo / "src" / "helper.o", mock_repo, config) is False
    assert (
        is_supported_file(mock_repo / "src" / "App.class", mock_repo, config) is False
    )
    assert (
        is_supported_file(
            mock_repo / "src" / "__pycache__" / "main.cpython-312.pyc",
            mock_repo,
            config,
        )
        is False
    )

    # Valid text files should pass
    assert is_supported_file(mock_repo / "src" / "main.py", mock_repo, config) is True
    assert is_supported_file(mock_repo / "Dockerfile", mock_repo, config) is True


def test_language_detection(mock_repo: Path) -> None:
    """Verifies automatic language detection using Pygments and signature heuristics."""
    # Custom shebang/signature heuristics
    assert detect_language(mock_repo / "Dockerfile", "FROM python") == "dockerfile"
    assert detect_language(mock_repo / "Makefile", "build:\n") == "makefile"
    assert (
        detect_language(mock_repo / "rust-module" / "Cargo.toml", "[package]") == "toml"
    )

    # Pygments/Fallback mappings
    assert detect_language(mock_repo / "src" / "main.py", "print('hi')") == "python"
    assert detect_language(mock_repo / "src" / "helper.c", "void help() {}") == "c"
    assert detect_language(mock_repo / "src" / "core.cpp", "") == "cpp"
    assert (
        detect_language(mock_repo / "rust-module" / "src" / "lib.rs", "fn lib() {}")
        == "rust"
    )
    assert detect_language(mock_repo / "src" / "App.java", "class App {}") == "java"
    assert (
        detect_language(mock_repo / "frontend" / "app.js", "let x = 1;") == "javascript"
    )
    assert (
        detect_language(mock_repo / "frontend" / "index.ts", "let y: number = 2;")
        == "typescript"
    )
    assert detect_language(mock_repo / "LICENSE", "MIT License") == "text"


def test_parsing_and_chunking(mock_repo: Path) -> None:
    """Tests the parsing pipeline, chunking logic, and backward-compatible schema."""
    # Create configuration where max size is 1MB and chunk size is 1MB to trigger chunking on our 2.5MB file
    custom_config = {
        "max_file_size_mb": 1,
        "chunk_size_mb": 1,
        "binary_extensions": [".png", ".o", ".class", ".pyc"],
        "ignored_directories": [
            ".git",
            "node_modules",
            "dist",
            "target",
            ".venv",
            "__pycache__",
            ".github/cache",
        ],
    }

    records, stats = parse_repository(str(mock_repo), config=custom_config)

    # Verify that skipped directories are pruned
    paths_parsed = [r["path"] for r in records]
    assert not any("node_modules" in p for p in paths_parsed)
    assert not any("dist" in p for p in paths_parsed)
    assert not any("target" in p for p in paths_parsed)
    assert not any(".venv" in p for p in paths_parsed)
    assert not any("__pycache__" in p for p in paths_parsed)
    assert not any(".github/cache" in p for p in paths_parsed)

    # Verify binary extensions are excluded
    assert not any(p.endswith(".png") for p in paths_parsed)
    assert not any(p.endswith(".o") for p in paths_parsed)
    assert not any(p.endswith(".class") for p in paths_parsed)

    # Check for chunking of 2.5MB file
    chunked_parts = [r for r in records if "large_file.txt" in r["path"]]
    assert len(chunked_parts) == 3  # 2.5MB chunked into pieces of 1MB (1MB, 1MB, 0.5MB)
    assert chunked_parts[0]["path"] == "large_file.txt [chunk 1]"
    assert chunked_parts[0]["chunk_index"] == 0
    assert chunked_parts[0]["total_chunks"] == 3

    # Check backward compatibility fields (AST structures, sizes, etc.)
    for r in records:
        assert "repo" in r
        assert "path" in r
        assert "language" in r
        assert "content" in r
        assert "file_name" in r
        assert "extension" in r
        assert "size_bytes" in r
        assert "imports" in r
        assert "functions" in r
        assert "classes" in r
        assert "symbols" in r
        assert isinstance(r["imports"], list)
        assert isinstance(r["functions"], list)
        assert isinstance(r["classes"], list)
        assert isinstance(r["symbols"], list)

    # Assert statistics accuracy
    assert stats["files_found"] > 0
    assert stats["files_processed"] > 0
    assert stats["large_chunked"] == 1
    assert stats["binary_skipped"] > 0
    assert stats["ignored_directory_skips"] > 0
    assert stats["records_generated"] == len(records)
