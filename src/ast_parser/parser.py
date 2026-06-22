"""Orchestrates parsing of individual files using registered AST parsers with safe fallback logic."""

from pathlib import Path
from src.ast_parser.models import CodeSymbol
from src.ast_parser.registry import get_parser
from src.ast_parser.generic_parser import GenericParser
from src.utils.logger import get_logger

logger = get_logger(__name__)


def parse_file(
    repo_name: str,
    file_path: Path,
    relative_path: str,
    language: str,
    content: str,
) -> list[CodeSymbol]:
    """Parses a single file's content into a list of CodeSymbol objects.

    Uses registry lookup and automatically falls back to GenericParser upon failure.

    Args:
        repo_name: The name of the repository.
        file_path: Absolute Path object of the file.
        relative_path: Relative path string of the file inside the repo.
        language: Detected language string.
        content: The text content of the file.

    Returns:
        A list of extracted CodeSymbol instances.
    """
    parser = get_parser(language)
    logger.info(
        f"Selected parser {parser.__class__.__name__} for file '{relative_path}' (Detected language: {language})"
    )

    try:
        symbols = parser.parse(
            content=content,
            repo=repo_name,
            file_path=relative_path,
            language=language,
        )
        return symbols
    except Exception as e:
        logger.warning(
            f"AST parse failure for '{relative_path}' using {parser.__class__.__name__}: {e}. "
            f"Falling back to GenericParser.",
            exc_info=True,
        )
        # Fallback to GenericParser
        fallback_parser = GenericParser()
        try:
            symbols = fallback_parser.parse(
                content=content,
                repo=repo_name,
                file_path=relative_path,
                language=language,
            )
            for sym in symbols:
                sym.metadata["ast_parse_failure"] = True
            return symbols
        except Exception as fallback_err:
            logger.error(
                f"Generic fallback parser failed for '{relative_path}': {fallback_err}",
                exc_info=True,
            )
            return []
