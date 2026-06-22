"""Generic paragraph-aware text chunking parser for unsupported languages and fallback scenarios."""

from src.ast_parser.models import CodeSymbol


class GenericParser:
    """Paragraph-aware text chunker that formats chunks as CodeSymbols."""

    def __init__(self, target_lines: int = 50, overlap: int = 5):
        self.target_lines = target_lines
        self.overlap = overlap

    def parse(
        self,
        content: str,
        repo: str,
        file_path: str,
        language: str,
    ) -> list[CodeSymbol]:
        """Chunks the content and returns a list of CodeSymbol objects.

        Args:
            content: The file text content.
            repo: The repository name.
            file_path: Relative path to the file.
            language: Detected language.

        Returns:
            A list of CodeSymbol instances of type 'chunk'.
        """
        chunks = self._chunk_content(content, language, file_path)
        symbols = []

        for idx, (start_line, end_line, chunk_content) in enumerate(chunks):
            symbol_name = f"chunk_{idx + 1}"
            # Unique chunk_id: repo::file::symbol_name::start_line
            chunk_id = f"{repo}::{file_path}::{symbol_name}::{start_line}"

            symbol = CodeSymbol(
                repo=repo,
                file=file_path,
                language=language,
                symbol_type="chunk",
                symbol_name=symbol_name,
                parent_symbol=None,
                start_line=start_line,
                end_line=end_line,
                content=chunk_content,
                imports=[],
                exports=[],
                docstring=None,
                chunk_id=chunk_id,
                metadata={
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                },
            )
            symbols.append(symbol)

        return symbols

    def _chunk_content(
        self, content: str, language: str, file_path_str: str
    ) -> list[tuple[int, int, str]]:
        """Groups lines into paragraph-aware or markdown heading-aware chunks."""
        lines = content.splitlines(keepends=True)
        if not lines:
            return [(1, 1, "")]

        # Determine file type
        is_markdown = language.lower() in ("markdown", "md") or file_path_str.endswith(
            (".md", ".markdown")
        )

        # Division points (0-indexed line numbers where a chunk boundary can occur)
        division_points = [0]

        if is_markdown:
            # Split on markdown headings
            for idx, line in enumerate(lines):
                if line.startswith(("# ", "## ", "### ", "#### ", "##### ", "###### ")):
                    if idx > 0 and idx not in division_points:
                        division_points.append(idx)
        else:
            # Split on double newline / empty line boundaries
            for idx in range(1, len(lines)):
                # If current line starts a paragraph (not empty) and previous line was empty/whitespace
                if lines[idx].strip() and not lines[idx - 1].strip():
                    if idx not in division_points:
                        division_points.append(idx)

        # Append final boundary
        division_points.append(len(lines))
        division_points = sorted(list(set(division_points)))

        chunks = []
        curr_start = 0
        i = 0
        while i < len(division_points) - 1:
            next_boundary = division_points[i + 1]

            # If a single division block is itself too large, chunk it with fixed size and overlap
            if next_boundary - curr_start > self.target_lines + 10:
                block_start = curr_start
                block_end_limit = next_boundary
                while block_start < block_end_limit:
                    block_end = min(block_start + self.target_lines, block_end_limit)
                    chunk_lines = lines[block_start:block_end]
                    chunks.append((block_start + 1, block_end, "".join(chunk_lines)))
                    if block_end == block_end_limit:
                        break
                    block_start += self.target_lines - self.overlap
                curr_start = next_boundary
                i += 1
            else:
                # Merge multiple smaller division blocks up to target_lines
                group_end = next_boundary
                j = i + 1
                while j < len(division_points) - 1:
                    potential_end = division_points[j + 1]
                    if potential_end - curr_start <= self.target_lines:
                        group_end = potential_end
                        j += 1
                    else:
                        break
                chunk_lines = lines[curr_start:group_end]
                chunks.append((curr_start + 1, group_end, "".join(chunk_lines)))
                curr_start = group_end
                i = j

        return chunks
