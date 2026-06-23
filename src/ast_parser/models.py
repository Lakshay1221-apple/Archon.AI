"""Data model for representing semantic code symbols."""

from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass
class CodeSymbol:
    """Represents a parsed semantic code symbol (function, class, method, struct, chunk, etc.)."""

    repo: str
    file: str
    language: str
    symbol_type: str
    symbol_name: str
    parent_symbol: Optional[str]
    start_line: int
    end_line: int
    content: str
    imports: list[str]
    exports: list[str]
    docstring: Optional[str]
    chunk_id: str
    metadata: dict[str, Any]
    exported: bool = False
    embedding_candidate: bool = False
    signature: Optional[str] = None
    retrieval_text: Optional[str] = None
    symbol_id: str = ""
    keywords: Optional[list[str]] = None
    related_symbols: Optional[list[str]] = None

    def to_dict(self) -> dict[str, Any]:
        """Converts the CodeSymbol instance to a standard dictionary."""
        return asdict(self)
