"""JavaScript AST parser to extract semantic symbols using tree-sitter."""

from typing import Optional
from tree_sitter import Language, Parser
import tree_sitter_javascript as tsjs
from src.ast_parser.models import CodeSymbol

# Initialize JavaScript Language
JS_LANG = Language(tsjs.language())


def is_embedding_candidate(symbol_type: str) -> bool:
    """Checks if a symbol type is eligible for embedding."""
    return symbol_type in (
        "function",
        "method",
        "class",
        "interface",
        "enum",
        "struct",
        "trait",
        "type_alias",
        "chunk",
        "documentation_chunk",
    )


def construct_retrieval_text(
    language: str,
    symbol_type: str,
    symbol_name: str,
    file_path: str,
    docstring: Optional[str] = None,
    parent_symbol: Optional[str] = None,
) -> str:
    """Constructs a semantically rich natural language sentence for retrieval."""
    lang_str = language.capitalize()
    parent_str = f" in class '{parent_symbol}'" if parent_symbol else ""
    desc_str = f" Description: {docstring.strip()}" if docstring else ""
    desc_str = " ".join(desc_str.split())
    return f"{lang_str} {symbol_type} '{symbol_name}'{parent_str} defined in {file_path}.{desc_str}".strip()


def get_preceding_docstring(node, source_code: bytes) -> Optional[str]:
    """Helper to walk backwards and retrieve contiguous comment block nodes preceding the node."""
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


def is_node_exported(node) -> bool:
    """Checks if a node is defined inside an export statement."""
    curr = node.parent
    while curr is not None:
        if curr.type in (
            "export_statement",
            "export_declaration",
        ) or curr.type.startswith("export"):
            return True
        curr = curr.parent
    return False


def get_js_signature(node, source_code: bytes) -> str:
    """Extracts a definition signature header from the tree-sitter node."""
    body_node = None
    for child in node.children:
        if child.type in (
            "statement_block",
            "block",
            "class_body",
            "object",
            "enum_body",
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

    sig_str = sig_bytes.decode("utf-8", errors="ignore").strip()
    # Strip any trailing assignment or braces if they remain
    if sig_str.endswith("="):
        sig_str = sig_str[:-1].strip()
    return sig_str


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
    """Extracts local exported names from export_statement / export_declaration nodes.

    Cleans up default exports and function calls like defineConfig.
    """
    names = []

    # Check for default export
    is_default = False
    for child in node.children:
        if child.type == "default":
            is_default = True
            break

    if is_default:
        default_idx = -1
        for idx, child in enumerate(node.children):
            if child.type == "default":
                default_idx = idx
                break

        if default_idx != -1 and default_idx + 1 < len(node.children):
            val_node = node.children[default_idx + 1]
            if val_node.type == "identifier":
                return [
                    source_code[val_node.start_byte : val_node.end_byte].decode(
                        "utf-8", errors="ignore"
                    )
                ]
            elif val_node.type == "call_expression":
                fn_node = val_node.children[0]
                return [
                    source_code[fn_node.start_byte : fn_node.end_byte].decode(
                        "utf-8", errors="ignore"
                    )
                ]
            elif val_node.type in ("class_declaration", "function_declaration"):
                for c in val_node.children:
                    if c.type == "identifier":
                        return [
                            source_code[c.start_byte : c.end_byte].decode(
                                "utf-8", errors="ignore"
                            )
                        ]
        return ["default_export"]

    # Non-default exports
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
        symbol_id = f"{self.repo}::{self.file_path}::{symbol_name}"

        # Signature and candidates
        signature = get_js_signature(node, self.source_code)
        candidate = is_embedding_candidate(symbol_type)
        exported = is_node_exported(node)

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
