"""TypeScript and TSX AST parser to extract semantic symbols using tree-sitter."""

from typing import Optional
from tree_sitter import Language, Parser
import tree_sitter_typescript as tsts
from src.ast_parser.models import CodeSymbol
from src.ast_parser.javascript_parser import JSVisitor


class TSVisitor(JSVisitor):
    """Visitor helper to traverse TypeScript AST and collect symbols."""

    def visit(self, node, parent_symbol: Optional[str] = None) -> None:
        """Adds handling for interfaces and enums to the base JavaScript visitor."""
        node_type = node.type

        if node_type == "interface_declaration":
            self.visit_interface(node)
        elif node_type == "enum_declaration":
            self.visit_enum(node)
        else:
            super().visit(node, parent_symbol)

    def visit_interface(self, node) -> None:
        """Visitor for interface declarations."""
        name = ""
        for child in node.children:
            if child.type in ("type_identifier", "identifier"):
                name = self.source_code[child.start_byte : child.end_byte].decode(
                    "utf-8", errors="ignore"
                )
        if not name:
            name = "interface"

        self.add_symbol(node, "interface", name, None)

    def visit_enum(self, node) -> None:
        """Visitor for enum declarations."""
        name = ""
        for child in node.children:
            if child.type in ("type_identifier", "identifier"):
                name = self.source_code[child.start_byte : child.end_byte].decode(
                    "utf-8", errors="ignore"
                )
        if not name:
            name = "enum"

        self.add_symbol(node, "enum", name, None)


class TypeScriptParser:
    """AST parser for TypeScript and TSX using tree-sitter-typescript."""

    def parse(
        self,
        content: str,
        repo: str,
        file_path: str,
        language: str = "typescript",
    ) -> list[CodeSymbol]:
        """Parses TypeScript/TSX content into CodeSymbol instances."""
        # Determine language grammar (TS vs TSX)
        if language.lower() in ("tsx", "jsx") or file_path.endswith((".tsx", ".jsx")):
            lang_capsule = tsts.language_tsx()
        else:
            lang_capsule = tsts.language_typescript()

        ts_lang = Language(lang_capsule)
        parser = Parser(ts_lang)
        source_bytes = content.encode("utf-8")
        tree = parser.parse(source_bytes)

        visitor = TSVisitor(source_bytes, repo, file_path, language)
        visitor.collect_imports_exports(tree.root_node)
        visitor.visit(tree.root_node)
        return visitor.symbols
