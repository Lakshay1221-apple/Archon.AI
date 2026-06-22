"""JavaScript AST parser to extract semantic symbols using tree-sitter."""

from typing import Optional
from tree_sitter import Language, Parser
import tree_sitter_javascript as tsjs
from src.ast_parser.models import CodeSymbol

# Initialize JavaScript Language
JS_LANG = Language(tsjs.language())


def get_preceding_docstring(node, source_code: bytes) -> Optional[str]:
    """Helper to walk backwards and retrieve contiguous comment block nodes preceding the node.

    Walks up the parent chain (e.g. through variable declarators and export statements) to locate the comment.
    """
    curr_target = node
    while curr_target.parent is not None and curr_target.parent.type != "program":
        if curr_target.parent.type in (
            "export_statement",
            "export_declaration",
        ) or curr_target.parent.type.startswith("export"):
            curr_target = curr_target.parent
            break
        if curr_target.parent.type in (
            "lexical_declaration",
            "variable_declaration",
            "variable_declarator",
        ):
            curr_target = curr_target.parent
        else:
            break

    comments = []
    curr = curr_target.prev_sibling
    while curr is not None and curr.type == "comment":
        comment_text = (
            source_code[curr.start_byte : curr.end_byte]
            .decode("utf-8", errors="ignore")
            .strip()
        )
        comments.append(comment_text)
        curr = curr.prev_sibling

    if comments:
        comments.reverse()
        return "\n".join(comments)
    return None


def get_arrow_function_name(node, source_code: bytes) -> str:
    """Finds the name of an arrow function if assigned to a variable, property, etc."""
    parent = node.parent
    if parent is not None:
        if parent.type == "variable_declarator":
            for child in parent.children:
                if child.type == "identifier":
                    return source_code[child.start_byte : child.end_byte].decode(
                        "utf-8", errors="ignore"
                    )
        elif parent.type == "pair":
            key_node = parent.children[0]
            return source_code[key_node.start_byte : key_node.end_byte].decode(
                "utf-8", errors="ignore"
            )
        elif parent.type == "assignment_expression":
            left_node = parent.children[0]
            return source_code[left_node.start_byte : left_node.end_byte].decode(
                "utf-8", errors="ignore"
            )
    return "anonymous_arrow_function"


def extract_js_import_names(node, source_code: bytes) -> list[str]:
    """Extracts local imported names from an import_statement node."""
    names = []

    def traverse(curr):
        if curr.type == "import_specifier":
            ids = [c for c in curr.children if c.type == "identifier"]
            if ids:
                names.append(
                    source_code[ids[-1].start_byte : ids[-1].end_byte].decode(
                        "utf-8", errors="ignore"
                    )
                )
        elif curr.type == "namespace_import":
            ids = [c for c in curr.children if c.type == "identifier"]
            if ids:
                names.append(
                    source_code[ids[0].start_byte : ids[0].end_byte].decode(
                        "utf-8", errors="ignore"
                    )
                )
        elif curr.type == "import_clause":
            for child in curr.children:
                if child.type == "identifier":
                    names.append(
                        source_code[child.start_byte : child.end_byte].decode(
                            "utf-8", errors="ignore"
                        )
                    )
            for child in curr.children:
                traverse(child)
        else:
            for child in curr.children:
                traverse(child)

    traverse(node)
    return names


def extract_js_export_names(node, source_code: bytes) -> list[str]:
    """Extracts local exported names from export_statement / export_declaration nodes."""
    names = []

    def traverse(curr):
        if curr.type == "export_specifier":
            ids = [c for c in curr.children if c.type == "identifier"]
            if ids:
                names.append(
                    source_code[ids[-1].start_byte : ids[-1].end_byte].decode(
                        "utf-8", errors="ignore"
                    )
                )
        elif curr.type in ("class_declaration", "function_declaration"):
            for child in curr.children:
                if child.type == "identifier":
                    names.append(
                        source_code[child.start_byte : child.end_byte].decode(
                            "utf-8", errors="ignore"
                        )
                    )
        elif curr.type == "variable_declarator":
            for child in curr.children:
                if child.type == "identifier":
                    names.append(
                        source_code[child.start_byte : child.end_byte].decode(
                            "utf-8", errors="ignore"
                        )
                    )
        else:
            for child in curr.children:
                traverse(child)

    traverse(node)
    return names


class JavaScriptParser:
    """AST parser for JavaScript using tree-sitter."""

    def parse(
        self,
        content: str,
        repo: str,
        file_path: str,
        language: str = "javascript",
    ) -> list[CodeSymbol]:
        """Parses JavaScript content into CodeSymbol instances."""
        parser = Parser(JS_LANG)
        source_bytes = content.encode("utf-8")
        tree = parser.parse(source_bytes)

        visitor = JSVisitor(source_bytes, repo, file_path, language)
        visitor.collect_imports_exports(tree.root_node)
        visitor.visit(tree.root_node)
        return visitor.symbols


class JSVisitor:
    """Helper to traverse JavaScript AST tree and collect CodeSymbols."""

    def __init__(self, source_code: bytes, repo: str, file_path: str, language: str):
        self.source_code = source_code
        self.repo = repo
        self.file_path = file_path
        self.language = language
        self.symbols: list[CodeSymbol] = []
        self.file_imports: list[str] = []
        self.file_exports: list[str] = []

    def collect_imports_exports(self, node) -> None:
        """First-pass traversal to harvest file-wide imports and exports lists."""
        if not node.is_named:
            return

        if node.type == "import_statement":
            self.file_imports.extend(extract_js_import_names(node, self.source_code))
        elif node.type in (
            "export_statement",
            "export_declaration",
        ) or node.type.startswith("export"):
            self.file_exports.extend(extract_js_export_names(node, self.source_code))

        for child in node.children:
            self.collect_imports_exports(child)

    def visit(self, node, parent_symbol: Optional[str] = None) -> None:
        """Recursive traversal visitor."""
        if not node.is_named:
            return

        node_type = node.type

        if node_type in ("function_declaration", "generator_function_declaration"):
            self.visit_function(node, parent_symbol)
        elif node_type == "arrow_function":
            self.visit_arrow_function(node, parent_symbol)
        elif node_type in ("class_declaration", "class"):
            self.visit_class(node)
        elif node_type == "method_definition":
            self.visit_method(node, parent_symbol)
        elif node_type == "import_statement":
            self.visit_import(node)
        elif node_type in (
            "export_statement",
            "export_declaration",
        ) or node_type.startswith("export"):
            self.visit_export(node)
        else:
            for child in node.children:
                self.visit(child, parent_symbol)

    def visit_function(self, node, parent_symbol: Optional[str]) -> None:
        name = ""
        for child in node.children:
            if child.type == "identifier":
                name = self.source_code[child.start_byte : child.end_byte].decode(
                    "utf-8", errors="ignore"
                )
        if not name:
            name = "anonymous_function"

        symbol_name = f"{parent_symbol}.{name}" if parent_symbol else name
        self.add_symbol(node, "function", symbol_name, parent_symbol)

    def visit_arrow_function(self, node, parent_symbol: Optional[str]) -> None:
        name = get_arrow_function_name(node, self.source_code)
        if name == "anonymous_arrow_function":
            # Skip inline callbacks or anonymous closures
            return

        symbol_name = f"{parent_symbol}.{name}" if parent_symbol else name
        self.add_symbol(node, "function", symbol_name, parent_symbol)

    def visit_class(self, node) -> None:
        name = ""
        for child in node.children:
            if child.type == "identifier":
                name = self.source_code[child.start_byte : child.end_byte].decode(
                    "utf-8", errors="ignore"
                )
        if not name:
            name = "Class"

        self.add_symbol(node, "class", name, None)

        # Traverse methods inside the class body
        for child in node.children:
            self.visit(child, parent_symbol=name)

    def visit_method(self, node, parent_symbol: Optional[str]) -> None:
        name = ""
        for child in node.children:
            if child.type in ("property_identifier", "identifier"):
                name = self.source_code[child.start_byte : child.end_byte].decode(
                    "utf-8", errors="ignore"
                )
        if not name:
            name = "method"

        symbol_name = f"{parent_symbol}.{name}" if parent_symbol else name
        self.add_symbol(node, "method", symbol_name, parent_symbol)

    def visit_import(self, node) -> None:
        names = extract_js_import_names(node, self.source_code)
        symbol_name = ", ".join(names) if names else "import"
        self.add_symbol(node, "import", symbol_name, None)

    def visit_export(self, node) -> None:
        names = extract_js_export_names(node, self.source_code)
        symbol_name = ", ".join(names) if names else "export"
        self.add_symbol(node, "export", symbol_name, None)
        # RECURSE into the children of the export statement to extract nested function/class/etc.
        for child in node.children:
            self.visit(child, None)

    def add_symbol(
        self, node, symbol_type: str, symbol_name: str, parent_symbol: Optional[str]
    ) -> None:
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        content = self.source_code[node.start_byte : node.end_byte].decode(
            "utf-8", errors="ignore"
        )
        docstring = get_preceding_docstring(node, self.source_code)
        chunk_id = f"{self.repo}::{self.file_path}::{symbol_name}::{start_line}"

        symbol = CodeSymbol(
            repo=self.repo,
            file=self.file_path,
            language=self.language,
            symbol_type=symbol_type,
            symbol_name=symbol_name,
            parent_symbol=parent_symbol,
            start_line=start_line,
            end_line=end_line,
            content=content,
            imports=list(set(self.file_imports)),
            exports=list(set(self.file_exports)),
            docstring=docstring,
            chunk_id=chunk_id,
            metadata={},
        )
        self.symbols.append(symbol)
