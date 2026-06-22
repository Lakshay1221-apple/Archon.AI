"""Parser registry mapping programming languages to their AST parser implementations."""

from typing import Any
from src.ast_parser.generic_parser import GenericParser
from src.ast_parser.python_parser import PythonParser
from src.ast_parser.javascript_parser import JavaScriptParser
from src.ast_parser.typescript_parser import TypeScriptParser
from src.ast_parser.rust_parser import RustParser

# Map normalized language names to parser classes
_PARSERS = {
    "python": PythonParser,
    "javascript": JavaScriptParser,
    "typescript": TypeScriptParser,
    "tsx": TypeScriptParser,
    "jsx": JavaScriptParser,
    "rust": RustParser,
}


def get_parser(language: str) -> Any:
    """Retrieves the parser instance for a given programming language.

    Falls back to GenericParser if no specialized parser is registered.

    Args:
        language: The language name (e.g., 'python', 'javascript').

    Returns:
        An instance of a parser that implements the .parse() method.
    """
    lang_lower = language.lower().strip()
    parser_cls = _PARSERS.get(lang_lower, GenericParser)
    return parser_cls()
