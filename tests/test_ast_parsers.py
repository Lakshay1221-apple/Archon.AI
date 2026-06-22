"""Unit tests for AST-based code parsers."""

from src.ast_parser.generic_parser import GenericParser
from src.ast_parser.python_parser import PythonParser
from src.ast_parser.javascript_parser import JavaScriptParser
from src.ast_parser.typescript_parser import TypeScriptParser
from src.ast_parser.rust_parser import RustParser


def test_generic_parser_paragraph_splitting():
    """Verify that GenericParser successfully splits text based on double-newlines and populates new fields."""
    parser = GenericParser(target_lines=2, overlap=1)
    content = (
        "Para one line one\nPara one line two\n\nPara two line one\nPara two line two"
    )
    symbols = parser.parse(
        content=content,
        repo="test-repo",
        file_path="src/test.txt",
        language="text",
    )
    assert len(symbols) == 2
    assert symbols[0].symbol_type == "chunk"
    assert symbols[0].symbol_name == "chunk_1"
    assert symbols[0].embedding_candidate is True
    assert symbols[0].exported is False
    assert symbols[0].signature == "Para one line one"
    assert "text chunk" in symbols[0].retrieval_text
    assert symbols[0].symbol_id == "test-repo::src/test.txt::chunk_1"


def test_generic_parser_markdown_splitting():
    """Verify that GenericParser splits markdown documents on headings."""
    parser = GenericParser(target_lines=2, overlap=1)
    content = (
        "# Main Title\n"
        "Introduction text here.\n"
        "\n"
        "## Section 1\n"
        "Section one content.\n"
        "\n"
        "### Subsection 1.1\n"
        "Sub content."
    )
    symbols = parser.parse(
        content=content,
        repo="test-repo",
        file_path="README.md",
        language="markdown",
    )
    assert len(symbols) >= 3
    assert "# Main Title" in symbols[0].content
    assert "## Section 1" in symbols[1].content
    assert "### Subsection 1.1" in symbols[2].content


def test_python_parser():
    """Verify that PythonParser extracts signature, retrieval_text, and candidate flags."""
    parser = PythonParser()
    code = (
        "import os\n"
        "from math import sin, cos\n"
        "\n"
        "class Calculator:\n"
        '    """Docstring for Calculator class."""\n'
        "\n"
        "    def __init__(self):\n"
        "        pass\n"
        "\n"
        "    async def add(self, x, y):\n"
        '        """Adds two numbers asynchronously."""\n'
        "        return x + y\n"
        "\n"
        "def _private_func():\n"
        "    return 42\n"
    )

    symbols = parser.parse(
        content=code,
        repo="test-repo",
        file_path="src/calc.py",
        language="python",
    )

    # 1. Class checks
    class_symbols = [s for s in symbols if s.symbol_type == "class"]
    assert len(class_symbols) == 1
    cls = class_symbols[0]
    assert cls.symbol_name == "Calculator"
    assert cls.signature == "class Calculator"
    assert cls.embedding_candidate is True
    assert cls.exported is True
    assert "Calculator" in cls.retrieval_text
    assert cls.symbol_id == "test-repo::src/calc.py::Calculator"

    # 2. Methods checks
    method_symbols = [s for s in symbols if s.symbol_type == "method"]
    assert len(method_symbols) == 2

    add_method = [s for s in method_symbols if s.symbol_name == "Calculator.add"][0]
    assert add_method.signature == "async def add(self, x, y)"
    assert add_method.embedding_candidate is True
    assert add_method.exported is True
    assert "Adds two numbers asynchronously" in add_method.retrieval_text
    assert add_method.symbol_id == "test-repo::src/calc.py::Calculator.add"

    # 3. Private check
    private_func = [s for s in symbols if s.symbol_name == "_private_func"][0]
    assert private_func.exported is False
    assert private_func.embedding_candidate is True


def test_javascript_parser():
    """Verify that JavaScriptParser cleans default export naming and populates fields."""
    parser = JavaScriptParser()
    code = (
        "// Get helper from utils\n"
        "import { helper } from 'utils';\n"
        "\n"
        "// Class representing payment service\n"
        "export class PaymentService {\n"
        "    constructor() {\n"
        "        this.status = 'idle';\n"
        "    }\n"
        "\n"
        "    process(amount) {\n"
        "        return amount;\n"
        "    }\n"
        "}\n"
        "\n"
        "export default App;\n"
    )
    symbols = parser.parse(
        content=code,
        repo="test-repo",
        file_path="src/payment.js",
        language="javascript",
    )

    # Check export resolution
    assert "App" in symbols[0].exports
    assert "PaymentService" in symbols[0].exports

    # Class signature & exported checks
    classes = [s for s in symbols if s.symbol_type == "class"]
    assert len(classes) == 1
    assert classes[0].symbol_name == "PaymentService"
    assert classes[0].signature == "class PaymentService"
    assert classes[0].exported is True
    assert classes[0].embedding_candidate is True
    assert classes[0].symbol_id == "test-repo::src/payment.js::PaymentService"


def test_typescript_parser():
    """Verify TypeScriptParser handles interfaces and enums as candidates."""
    parser = TypeScriptParser()
    code = (
        "import { Config } from 'config';\n"
        "\n"
        "export interface User {\n"
        "    id: string;\n"
        "    name: string;\n"
        "}\n"
    )
    symbols = parser.parse(
        content=code,
        repo="test-repo",
        file_path="src/types.ts",
        language="typescript",
    )

    interfaces = [s for s in symbols if s.symbol_type == "interface"]
    assert len(interfaces) == 1
    assert interfaces[0].symbol_name == "User"
    assert interfaces[0].embedding_candidate is True
    assert interfaces[0].exported is True


def test_rust_parser():
    """Verify RustParser extracts signatures and candidate flags."""
    parser = RustParser()
    code = (
        "use std::collections::HashMap;\n"
        "\n"
        "/// Struct representing a user\n"
        "pub struct User {\n"
        "    id: u64,\n"
        "}\n"
        "\n"
        "impl User {\n"
        "    pub fn new(id: u64) -> Self {\n"
        "        User { id }\n"
        "    }\n"
        "}\n"
    )
    symbols = parser.parse(
        content=code,
        repo="test-repo",
        file_path="src/user.rs",
        language="rust",
    )

    # Struct check
    structs = [s for s in symbols if s.symbol_type == "struct"]
    assert len(structs) == 1
    assert structs[0].symbol_name == "User"
    assert structs[0].signature == "pub struct User"
    assert structs[0].embedding_candidate is True
    assert structs[0].exported is True

    # Method check
    methods = [s for s in symbols if s.symbol_type == "method"]
    assert len(methods) == 1
    assert methods[0].symbol_name == "impl User.new"
    assert methods[0].signature == "pub fn new(id: u64) -> Self"
    assert methods[0].embedding_candidate is True
    assert methods[0].exported is True
