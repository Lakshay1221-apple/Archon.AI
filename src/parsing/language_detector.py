"""Module for automatically detecting the programming or markup language of files."""

import logging
from pathlib import Path
from pygments.lexers import get_lexer_for_filename, guess_lexer
from pygments.util import ClassNotFound

logger = logging.getLogger(__name__)

# Complete fallback mapping for major ecosystems
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".rs": "rust",
    ".go": "go",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".pl": "perl",
    ".pm": "perl",
    ".r": "r",
    ".scala": "scala",
    ".ml": "ocaml",
    ".mli": "ocaml",
    ".hs": "haskell",
    ".erl": "erlang",
    ".hrl": "erlang",
    ".ex": "elixir",
    ".exs": "elixir",
    ".sol": "solidity",
    ".tf": "terraform",
    ".tfvars": "terraform",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".prisma": "prisma",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "sass",
    ".sass": "sass",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".md": "markdown",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "ini",
    ".txt": "text",
    ".dockerfile": "dockerfile",
    ".makefile": "makefile",
}


def detect_language(file_path: Path, content: str = "") -> str:
    """Automatically detects the programming/markup language of a file.

    Combines filename checks, Pygments lexer matching, shebang heuristics,
    and a fallback extension dictionary.

    Args:
        file_path: Path object of the file.
        content: String content of the file.

    Returns:
        The detected language name as a lowercase string.
    """
    name_lower = file_path.name.lower()

    # 1. Custom heuristics for standard files/configs
    if name_lower == "dockerfile" or file_path.suffix.lower() == ".dockerfile":
        return "dockerfile"
    if name_lower in ("makefile", "gnumakefile"):
        return "makefile"
    if name_lower in ("jenkinsfile", "vagrantfile"):
        return "groovy"
    if name_lower == "cmakelists.txt":
        return "cmake"
    if name_lower == "cargo.toml":
        return "toml"
    if name_lower == "package.json":
        return "json"
    if name_lower == "go.mod":
        return "go"
    if name_lower in ("license", "copying", "readme"):
        return "text"

    # 2. Check shebang if content is available
    if content.startswith("#!"):
        first_line = content.split("\n", 1)[0]
        if "python" in first_line:
            return "python"
        if "bash" in first_line or "sh" in first_line or "zsh" in first_line:
            return "bash"
        if "node" in first_line:
            return "javascript"
        if "ruby" in first_line:
            return "ruby"
        if "perl" in first_line:
            return "perl"

    # 3. Use Pygments get_lexer_for_filename
    try:
        lexer = get_lexer_for_filename(file_path.name, code=content)
        if lexer.aliases:
            return lexer.aliases[0].lower()
        return lexer.name.lower()
    except ClassNotFound:
        pass

    # 4. Use Pygments guess_lexer as a heuristic if content is substantial
    if content and len(content.strip()) > 50:
        try:
            lexer = guess_lexer(content)
            if lexer.aliases:
                return lexer.aliases[0].lower()
            return lexer.name.lower()
        except ClassNotFound:
            pass

    # 5. Extension fallback (defaulting to 'text' for any unrecognized text file)
    ext = file_path.suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(ext, "text")
