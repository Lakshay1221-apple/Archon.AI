"""Rust AST parser to extract semantic symbols using tree-sitter."""

from typing import Optional
from tree_sitter import Language, Parser
import tree_sitter_rust as tsrust
from src.ast_parser.models import CodeSymbol
from src.ast_parser.javascript_parser import (
    is_embedding_candidate,
    construct_retrieval_text,
)

# Initialize Rust Language
RUST_LANG = Language(tsrust.language())


def get_preceding_docstring(node, source_code: bytes) -> Optional[str]:
    """Helper to walk backwards and retrieve contiguous comment/doc-comment nodes preceding the node."""
    comments = []
    curr = node.prev_sibling
    while curr is not None and curr.type in (
        "comment",
        "line_comment",
        "block_comment",
    ):
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


def get_impl_name(node, source_code: bytes) -> str:
    """Extracts a readable header representing the implementation block name (e.g. 'impl Bar' or 'impl Qux for Bar')."""
    text = (
        source_code[node.start_byte : node.end_byte]
        .decode("utf-8", errors="ignore")
        .strip()
    )
    if "{" in text:
        header = text.split("{", 1)[0].strip()
        return " ".join(header.split())
    return "impl"


def get_rust_node_name(node, source_code: bytes) -> str:
    """Helper to find the identifier or type identifier child of the Rust node."""
    if node.type == "impl_item":
        return get_impl_name(node, source_code)

    for child in node.children:
        if child.type in ("identifier", "type_identifier"):
            return source_code[child.start_byte : child.end_byte].decode(
                "utf-8", errors="ignore"
            )

    # Fallback to header splitting
    text = (
        source_code[node.start_byte : node.end_byte]
        .decode("utf-8", errors="ignore")
        .strip()
    )
    for delim in ("{", ";", "("):
        if delim in text:
            header = text.split(delim, 1)[0].strip()
            return " ".join(header.split())
    return node.type


def get_rust_signature(node, source_code: bytes) -> str:
    """Extracts functional signature block from Rust nodes."""
    body_node = None
    for child in node.children:
        if child.type in (
            "declaration_list",
            "enum_variant_list",
            "field_declaration_list",
            "block",
            "impl_body",
        ):
            body_node = child
            break

    if body_node is not None:
        sig_bytes = source_code[node.start_byte : body_node.start_byte]
    else:
        text = source_code[node.start_byte : node.end_byte].decode(
            "utf-8", errors="ignore"
        )
        sig_bytes = text.splitlines()[0].encode("utf-8")

    return sig_bytes.decode("utf-8", errors="ignore").strip()


def extract_rust_import_names(node, source_code: bytes) -> list[str]:
    """Extracts imported names from a Rust use_declaration statement."""
    names = []
    text = (
        source_code[node.start_byte : node.end_byte]
        .decode("utf-8", errors="ignore")
        .strip()
    )

    if text.startswith("use "):
        text = text[4:].strip()
    if text.endswith(";"):
        text = text[:-1].strip()

    if "as " in text:
        parts = text.split("as ")
        names.append(parts[-1].strip())
    elif "{" in text:
        prefix = text.split("{")[0]
        list_part = text.split("{")[1].split("}")[0]
        for item in list_part.split(","):
            item_strip = item.strip()
            if item_strip == "self":
                prefix_clean = prefix.rstrip("::")
                names.append(prefix_clean.split("::")[-1])
            elif item_strip:
                names.append(item_strip)
    else:
        parts = text.split("::")
        names.append(parts[-1].strip())

    return [n for n in names if n]


def is_rust_exported(node) -> bool:
    """Checks if a Rust item has a public visibility modifier."""
    for child in node.children:
        if child.type == "visibility_modifier":
            return True
    return False


class RustParser:
    """AST parser for Rust using tree-sitter."""

    def parse(
        self,
        content: str,
        repo: str,
        file_path: str,
        language: str = "rust",
    ) -> list[CodeSymbol]:
        """Parses Rust content into CodeSymbol instances."""
        parser = Parser(RUST_LANG)
        source_bytes = content.encode("utf-8")
        tree = parser.parse(source_bytes)

        visitor = RustVisitor(source_bytes, repo, file_path, language)
        visitor.collect_imports_exports(tree.root_node)
        visitor.visit(tree.root_node)
        return visitor.symbols


class RustVisitor:
    """Helper to traverse Rust AST and collect CodeSymbols."""

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
        if node.type == "use_declaration":
            self.file_imports.extend(extract_rust_import_names(node, self.source_code))
        elif is_rust_exported(node):
            name = get_rust_node_name(node, self.source_code)
            if name and name not in (node.type, "impl"):
                self.file_exports.append(name)

        for child in node.children:
            self.collect_imports_exports(child)

    def visit(self, node, parent_symbol: Optional[str] = None) -> None:
        """Recursive traversal visitor."""
        node_type = node.type

        if node_type == "function_item":
            self.visit_function(node, parent_symbol)
        elif node_type == "struct_item":
            self.visit_struct(node, parent_symbol)
        elif node_type == "enum_item":
            self.visit_enum(node, parent_symbol)
        elif node_type == "trait_item":
            self.visit_trait(node, parent_symbol)
        elif node_type == "impl_item":
            self.visit_impl(node, parent_symbol)
        elif node_type == "mod_item":
            self.visit_mod(node, parent_symbol)
        elif node_type == "use_declaration":
            self.visit_use(node, parent_symbol)
        else:
            for child in node.children:
                self.visit(child, parent_symbol)

    def visit_function(self, node, parent_symbol: Optional[str]) -> None:
        name = get_rust_node_name(node, self.source_code)
        symbol_type = "method" if parent_symbol else "function"
        symbol_name = f"{parent_symbol}.{name}" if parent_symbol else name
        self.add_symbol(node, symbol_type, symbol_name, parent_symbol)

    def visit_struct(self, node, parent_symbol: Optional[str]) -> None:
        name = get_rust_node_name(node, self.source_code)
        self.add_symbol(node, "struct", name, parent_symbol)

    def visit_enum(self, node, parent_symbol: Optional[str]) -> None:
        name = get_rust_node_name(node, self.source_code)
        self.add_symbol(node, "enum", name, parent_symbol)

    def visit_trait(self, node, parent_symbol: Optional[str]) -> None:
        name = get_rust_node_name(node, self.source_code)
        self.add_symbol(node, "trait", name, parent_symbol)

    def visit_impl(self, node, parent_symbol: Optional[str]) -> None:
        name = get_impl_name(node, self.source_code)
        self.add_symbol(node, "impl", name, parent_symbol)

        for child in node.children:
            self.visit(child, parent_symbol=name)

    def visit_mod(self, node, parent_symbol: Optional[str]) -> None:
        name = get_rust_node_name(node, self.source_code)
        self.add_symbol(node, "module", name, parent_symbol)
        for child in node.children:
            self.visit(child, parent_symbol=name)

    def visit_use(self, node, parent_symbol: Optional[str]) -> None:
        names = extract_rust_import_names(node, self.source_code)
        symbol_name = ", ".join(names) if names else "use"
        self.add_symbol(node, "import", symbol_name, parent_symbol)

    def add_symbol(
        self,
        node,
        symbol_type: str,
        symbol_name: str,
        parent_symbol: Optional[str],
    ) -> None:
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        content = self.source_code[node.start_byte : node.end_byte].decode(
            "utf-8", errors="ignore"
        )
        docstring = get_preceding_docstring(node, self.source_code)
        chunk_id = f"{self.repo}::{self.file_path}::{symbol_name}::{start_line}"
        symbol_id = f"{self.repo}::{self.file_path}::{symbol_name}"

        signature = get_rust_signature(node, self.source_code)
        candidate = is_embedding_candidate(symbol_type)
        exported = is_rust_exported(node)

        retrieval_text = construct_retrieval_text(
            language=self.language,
            symbol_type=symbol_type,
            symbol_name=symbol_name,
            file_path=self.file_path,
            docstring=docstring,
            parent_symbol=parent_symbol,
        )

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
            exported=exported,
            embedding_candidate=candidate,
            signature=signature,
            retrieval_text=retrieval_text,
            symbol_id=symbol_id,
        )
        self.symbols.append(symbol)
