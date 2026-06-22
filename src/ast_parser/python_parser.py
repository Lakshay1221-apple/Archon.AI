"""Python AST parser to extract semantic symbols using Python's native `ast` library."""

import ast
from typing import Optional
from src.ast_parser.models import CodeSymbol


def extract_file_imports(tree: ast.AST) -> list[str]:
    """Helper to extract all file-level imports as list of strings."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imp_str = name.name
                if name.asname:
                    imp_str += f" as {name.asname}"
                imports.append(imp_str)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level
            prefix = "." * level if level > 0 else ""
            for name in node.names:
                imp_str = f"{prefix}{module}.{name.name}"
                if name.asname:
                    imp_str += f" as {name.asname}"
                imports.append(imp_str)
    return imports


class PythonParser:
    """Parser for Python source files using the native ast library."""

    def parse(
        self,
        content: str,
        repo: str,
        file_path: str,
        language: str = "python",
    ) -> list[CodeSymbol]:
        """Parses Python content and returns a list of CodeSymbol instances.

        Args:
            content: The file content.
            repo: The repository name.
            file_path: Relative path to the file.
            language: The language (defaults to 'python').

        Returns:
            A list of CodeSymbol instances.
        """
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            # Let the caller handle AST parsing errors via fallback generic parser
            raise ValueError(f"Python syntax error: {e}") from e

        file_imports = extract_file_imports(tree)
        visitor = PythonVisitor(content, repo, file_path, file_imports)

        # Traverse the AST starting from the root module node
        visitor.visit(tree)
        return visitor.symbols


class PythonVisitor:
    """Visitor helper to traverse Python AST and collect symbols."""

    def __init__(
        self, content: str, repo: str, file_path: str, file_imports: list[str]
    ):
        self.content = content
        self.lines = content.splitlines(keepends=True)
        self.repo = repo
        self.file_path = file_path
        self.file_imports = file_imports
        self.symbols: list[CodeSymbol] = []

    def visit(self, node: ast.AST, parent_symbol: Optional[str] = None) -> None:
        """Recursive traversal visitor."""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.visit_function(node, parent_symbol)
        elif isinstance(node, ast.ClassDef):
            self.visit_class(node)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            self.visit_import(node)
        elif isinstance(node, ast.Module):
            # Traverse root body items
            for child in node.body:
                self.visit(child, parent_symbol)
        else:
            # Continue traversal for control flows/blocks to find classes/functions
            for child in ast.iter_child_nodes(node):
                self.visit(child, parent_symbol)

    def visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent_symbol: Optional[str],
    ) -> None:
        """Visitor for function and method nodes."""
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        symbol_content = "".join(self.lines[start_line - 1 : end_line])

        is_async = isinstance(node, ast.AsyncFunctionDef)
        symbol_type = (
            "method"
            if parent_symbol
            else ("async_function" if is_async else "function")
        )
        symbol_name = f"{parent_symbol}.{node.name}" if parent_symbol else node.name
        docstring = ast.get_docstring(node)
        chunk_id = f"{self.repo}::{self.file_path}::{symbol_name}::{start_line}"

        symbol = CodeSymbol(
            repo=self.repo,
            file=self.file_path,
            language="python",
            symbol_type=symbol_type,
            symbol_name=symbol_name,
            parent_symbol=parent_symbol,
            start_line=start_line,
            end_line=end_line,
            content=symbol_content,
            imports=self.file_imports,
            exports=[],
            docstring=docstring,
            chunk_id=chunk_id,
            metadata={
                "is_async": is_async,
            },
        )
        self.symbols.append(symbol)

        # Do not recurse inside function body to avoid duplicate nested extraction

    def visit_class(self, node: ast.ClassDef) -> None:
        """Visitor for class nodes."""
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        symbol_content = "".join(self.lines[start_line - 1 : end_line])

        class_name = node.name
        docstring = ast.get_docstring(node)
        chunk_id = f"{self.repo}::{self.file_path}::{class_name}::{start_line}"

        symbol = CodeSymbol(
            repo=self.repo,
            file=self.file_path,
            language="python",
            symbol_type="class",
            symbol_name=class_name,
            parent_symbol=None,
            start_line=start_line,
            end_line=end_line,
            content=symbol_content,
            imports=self.file_imports,
            exports=[],
            docstring=docstring,
            chunk_id=chunk_id,
            metadata={},
        )
        self.symbols.append(symbol)

        # For methods, traverse the body of the ClassDef with class_name scope
        for child in node.body:
            self.visit(child, parent_symbol=class_name)

    def visit_import(self, node: ast.Import | ast.ImportFrom) -> None:
        """Visitor for imports to extract them as discrete import symbols."""
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        symbol_content = "".join(self.lines[start_line - 1 : end_line])

        imported_names = []
        if isinstance(node, ast.Import):
            for name in node.names:
                imported_names.append(name.name)
        else:
            module = node.module or ""
            for name in node.names:
                imported_names.append(f"{module}.{name.name}")

        symbol_name = ", ".join(imported_names)
        chunk_id = f"{self.repo}::{self.file_path}::import_{start_line}::{start_line}"

        symbol = CodeSymbol(
            repo=self.repo,
            file=self.file_path,
            language="python",
            symbol_type="import",
            symbol_name=symbol_name,
            parent_symbol=None,
            start_line=start_line,
            end_line=end_line,
            content=symbol_content,
            imports=self.file_imports,
            exports=[],
            docstring=None,
            chunk_id=chunk_id,
            metadata={},
        )
        self.symbols.append(symbol)
