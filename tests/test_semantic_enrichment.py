"""Unit tests validating the Semantic Enrichment Layer functionality."""

from src.ast_parser.models import CodeSymbol
from src.enrichment.semantic_builder import SemanticBuilder
from src.ast_parser.python_parser import PythonParser
from src.ast_parser.javascript_parser import JavaScriptParser
from src.ast_parser.rust_parser import RustParser


def test_semantic_builder_docstring_cleaning():
    """Verify that SemanticBuilder correctly strips comment markers and normalizes docstrings."""
    builder = SemanticBuilder()

    # JS/TS Block comment
    js_comment = "/**\n * Processes payment transactions.\n * @param {number} amount\n */"
    assert builder.clean_docstring(js_comment) == "Processes payment transactions.\n@param {number} amount"

    # Rust Doc comment
    rust_comment = "/// Clones repositories locally.\n/// Support github and gitlab."
    assert builder.clean_docstring(rust_comment) == "Clones repositories locally.\nSupport github and gitlab."

    # Python/Shell Comment
    py_comment = "# Helper class to log details.\n# Keep tracking session ID."
    assert builder.clean_docstring(py_comment) == "Helper class to log details.\nKeep tracking session ID."


def test_semantic_builder_keyword_generation():
    """Verify that keyword generation splits names, incorporates docs/sigs, filters stop words, and keeps >= 3 words."""
    builder = SemanticBuilder()

    keywords = builder.generate_keywords(
        symbol_name="clone_repository",
        signature="def clone_repository(repo_url: str) -> str",
        docstring="Clones github git repository locally.",
        imports=["import git", "from pathlib import Path"],
    )

    assert len(keywords) >= 3
    assert "clone" in keywords
    assert "repository" in keywords
    assert "git" in keywords
    assert "github" in keywords
    # Stop words shouldn't be here
    assert "def" not in keywords
    assert "str" not in keywords


def test_full_python_parser_enrichment():
    """Test Python parsing + semantic enrichment end-to-end."""
    parser = PythonParser()
    builder = SemanticBuilder()

    code = (
        "import os\n"
        "from git import Repo\n"
        "\n"
        "class Downloader:\n"
        '    """Downloads remote items to directory."""\n'
        "\n"
        "    def download_repo(self, repo_url):\n"
        '        """Downloads Git repo from url."""\n'
        "        Repo.clone_from(repo_url, '/tmp/target')\n"
        "        return '/tmp/target'\n"
    )

    symbols = parser.parse(
        content=code,
        repo="Archon AI",
        file_path="src/downloader.py",
        language="python",
    )

    # Enrich symbols
    enriched = builder.enrich_symbols(symbols)

    # 1. Class Symbol validation
    class_sym = [s for s in enriched if s.symbol_type == "class"][0]
    assert class_sym.keywords is not None
    assert len(class_sym.keywords) >= 3
    assert class_sym.related_symbols == ["download_repo"]
    assert "downloader" in class_sym.keywords
    assert "Downloader" in class_sym.retrieval_text
    assert "src/downloader.py" in class_sym.retrieval_text
    assert "download_repo" in class_sym.retrieval_text  # as a child method
    assert len(class_sym.retrieval_text) > 50

    # 2. Method Symbol validation
    method_sym = [s for s in enriched if s.symbol_type == "method"][0]
    assert method_sym.keywords is not None
    assert len(method_sym.keywords) >= 3
    assert "download_repo" in method_sym.retrieval_text
    assert "Downloader" in method_sym.retrieval_text  # parent symbol context
    assert "src/downloader.py" in method_sym.retrieval_text
    assert "repo_url" in method_sym.retrieval_text  # input parameters
    assert "/tmp/target" in method_sym.retrieval_text  # return values
    assert len(method_sym.retrieval_text) > 50


def test_full_javascript_parser_enrichment():
    """Test JS/TS parsing + semantic enrichment end-to-end."""
    parser = JavaScriptParser()
    builder = SemanticBuilder()

    code = (
        "import { helper } from 'utils';\n"
        "\n"
        "/**\n"
        " * Fetches transaction log status.\n"
        " */\n"
        "export function getTransactionStatus(txId) {\n"
        "    return 'success';\n"
        "}\n"
    )

    symbols = parser.parse(
        content=code,
        repo="Archon AI",
        file_path="src/payment.js",
        language="javascript",
    )

    enriched = builder.enrich_symbols(symbols)
    func_sym = [s for s in enriched if s.symbol_type == "function"][0]

    assert func_sym.keywords is not None
    assert len(func_sym.keywords) >= 3
    assert "transaction" in func_sym.keywords
    assert "getTransactionStatus" in func_sym.retrieval_text
    assert "src/payment.js" in func_sym.retrieval_text
    assert "txId" in func_sym.retrieval_text
    assert "success" in func_sym.retrieval_text
    assert len(func_sym.retrieval_text) > 50


def test_full_rust_parser_enrichment():
    """Test Rust parsing + semantic enrichment end-to-end."""
    parser = RustParser()
    builder = SemanticBuilder()

    code = (
        "use std::fs::File;\n"
        "\n"
        "/// Configures storage path.\n"
        "pub struct StorageConfig {\n"
        "    path: String,\n"
        "}\n"
    )

    symbols = parser.parse(
        content=code,
        repo="Archon AI",
        file_path="src/config.rs",
        language="rust",
    )

    enriched = builder.enrich_symbols(symbols)
    struct_sym = [s for s in enriched if s.symbol_type == "struct"][0]

    assert struct_sym.keywords is not None
    assert len(struct_sym.keywords) >= 3
    assert "storage" in struct_sym.keywords
    assert "StorageConfig" in struct_sym.retrieval_text
    assert "src/config.rs" in struct_sym.retrieval_text
    assert len(struct_sym.retrieval_text) > 50
