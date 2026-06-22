"""Unit tests for AST-based code parsers."""

from src.ast_parser.generic_parser import GenericParser
from src.ast_parser.python_parser import PythonParser
from src.ast_parser.javascript_parser import JavaScriptParser
from src.ast_parser.typescript_parser import TypeScriptParser
from src.ast_parser.rust_parser import RustParser


def test_generic_parser_paragraph_splitting():
    """Verify that GenericParser successfully splits text based on double-newlines."""
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
    assert "Para one" in symbols[0].content
    assert "Para two" in symbols[1].content
    assert symbols[0].parent_symbol is None
    assert symbols[0].docstring is None
    assert symbols[0].chunk_id == "test-repo::src/test.txt::chunk_1::1"


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
    # Should detect boundaries on the #/##/### headings
    assert len(symbols) >= 3
    assert "# Main Title" in symbols[0].content
    assert "## Section 1" in symbols[1].content
    assert "### Subsection 1.1" in symbols[2].content


def test_python_parser():
    """Verify that PythonParser extracts functions, classes, methods, and imports with docstrings/metadata."""
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
        "def top_level_func():\n"
        "    return 42\n"
    )

    symbols = parser.parse(
        content=code,
        repo="test-repo",
        file_path="src/calc.py",
        language="python",
    )

    # 1. Imports check
    import_symbols = [s for s in symbols if s.symbol_type == "import"]
    assert len(import_symbols) == 2
    # Verify that global imports are stored inside each symbol
    expected_imports = ["os", "math.sin", "math.cos"]
    for s in symbols:
        assert s.imports == expected_imports

    # 2. Class check
    class_symbols = [s for s in symbols if s.symbol_type == "class"]
    assert len(class_symbols) == 1
    cls_symbol = class_symbols[0]
    assert cls_symbol.symbol_name == "Calculator"
    assert cls_symbol.parent_symbol is None
    assert cls_symbol.docstring == "Docstring for Calculator class."
    assert cls_symbol.start_line == 4
    assert cls_symbol.end_line == 12

    # 3. Methods check
    method_symbols = [s for s in symbols if s.symbol_type == "method"]
    assert len(method_symbols) == 2

    init_method = [s for s in method_symbols if s.symbol_name == "Calculator.__init__"][
        0
    ]
    assert init_method.parent_symbol == "Calculator"
    assert init_method.docstring is None

    add_method = [s for s in method_symbols if s.symbol_name == "Calculator.add"][0]
    assert add_method.parent_symbol == "Calculator"
    assert add_method.docstring == "Adds two numbers asynchronously."
    assert add_method.metadata.get("is_async") is True

    # 4. Top-level functions check
    func_symbols = [
        s for s in symbols if s.symbol_type in ("function", "async_function")
    ]
    assert len(func_symbols) == 1
    func_sym = func_symbols[0]
    assert func_sym.symbol_name == "top_level_func"
    assert func_sym.parent_symbol is None
    assert func_sym.start_line == 14
    assert func_sym.end_line == 15


def test_javascript_parser():
    """Verify that JavaScriptParser extracts functions, arrow functions, classes, methods, imports, and exports."""
    parser = JavaScriptParser()
    code = (
        "// Get helper from utils\n"
        "import { helper } from 'utils';\n"
        "import defaultVal from 'module';\n"
        "\n"
        "// Class representing payment service\n"
        "export class PaymentService {\n"
        "    constructor() {\n"
        "        this.status = 'idle';\n"
        "    }\n"
        "\n"
        "    // Process payments\n"
        "    process(amount) {\n"
        "        return amount;\n"
        "    }\n"
        "}\n"
        "\n"
        "// Arrow function helper\n"
        "export const calculate = (a, b) => {\n"
        "    return a + b;\n"
        "};\n"
    )
    symbols = parser.parse(
        content=code,
        repo="test-repo",
        file_path="src/payment.js",
        language="javascript",
    )

    # 1. Check imports and exports on all symbols
    for s in symbols:
        assert "helper" in s.imports
        assert "defaultVal" in s.imports
        assert "PaymentService" in s.exports
        assert "calculate" in s.exports

    # 2. Check classes
    classes = [s for s in symbols if s.symbol_type == "class"]
    assert len(classes) == 1
    assert classes[0].symbol_name == "PaymentService"
    assert classes[0].docstring == "// Class representing payment service"

    # 3. Check methods
    methods = [s for s in symbols if s.symbol_type == "method"]
    assert len(methods) == 2
    assert methods[0].symbol_name == "PaymentService.constructor"
    assert methods[1].symbol_name == "PaymentService.process"
    assert methods[1].docstring == "// Process payments"

    # 4. Check arrow functions
    funcs = [
        s
        for s in symbols
        if s.symbol_type == "function" and s.symbol_name == "calculate"
    ]
    assert len(funcs) == 1
    assert funcs[0].docstring == "// Arrow function helper"


def test_typescript_parser():
    """Verify that TypeScriptParser handles TypeScript features like interfaces and enums."""
    parser = TypeScriptParser()
    code = (
        "import { Config } from 'config';\n"
        "\n"
        "export interface User {\n"
        "    id: string;\n"
        "    name: string;\n"
        "}\n"
        "\n"
        "export enum Role {\n"
        "    Admin,\n"
        "    User\n"
        "}\n"
    )
    symbols = parser.parse(
        content=code,
        repo="test-repo",
        file_path="src/types.ts",
        language="typescript",
    )

    # 1. Interface check
    interfaces = [s for s in symbols if s.symbol_type == "interface"]
    assert len(interfaces) == 1
    assert interfaces[0].symbol_name == "User"

    # 2. Enum check
    enums = [s for s in symbols if s.symbol_type == "enum"]
    assert len(enums) == 1
    assert enums[0].symbol_name == "Role"


def test_rust_parser():
    """Verify that RustParser extracts structs, enums, traits, impls, methods, and use statements."""
    parser = RustParser()
    code = (
        "use std::collections::HashMap;\n"
        "use crate::payment::{self, PaymentService};\n"
        "\n"
        "/// Struct representing a user\n"
        "pub struct User {\n"
        "    id: u64,\n"
        "}\n"
        "\n"
        "impl User {\n"
        "    /// Create new user\n"
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

    # 1. Imports and exports
    for s in symbols:
        assert "HashMap" in s.imports
        assert "payment" in s.imports
        assert "PaymentService" in s.imports
        assert "User" in s.exports

    # 2. Struct check
    structs = [s for s in symbols if s.symbol_type == "struct"]
    assert len(structs) == 1
    assert structs[0].symbol_name == "User"
    assert structs[0].docstring == "/// Struct representing a user"

    # 3. Impl check
    impls = [s for s in symbols if s.symbol_type == "impl"]
    assert len(impls) == 1
    assert impls[0].symbol_name == "impl User"

    # 4. Method check
    methods = [s for s in symbols if s.symbol_type == "method"]
    assert len(methods) == 1
    assert methods[0].symbol_name == "impl User.new"
    assert methods[0].docstring == "/// Create new user"
