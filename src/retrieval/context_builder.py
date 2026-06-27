"""
src/retrieval/context_builder.py

Builds an LLM-ready context string from retrieval results.
"""

from typing import List, Dict


class ContextBuilder:
    """
    Converts retrieved symbols into a structured context block
    suitable for prompt injection into an LLM.
    """

    def __init__(
        self,
        max_context_chars: int = 12000,
        include_distance: bool = True,
    ):
        self.max_context_chars = max_context_chars
        self.include_distance = include_distance

    def build_context(self, results: List[Dict]) -> str:
        """
        Build a formatted context string from retriever results.

        Args:
            results: List of retrieval results.

        Returns:
            Formatted context string.
        """

        if not results:
            return "No relevant context found."

        sections = []
        current_size = 0

        for rank, result in enumerate(results, start=1):

            section = self._format_result(
                result=result,
                rank=rank,
            )

            if current_size + len(section) > self.max_context_chars:
                break

            sections.append(section)
            current_size += len(section)

        header = (
            "==================== CONTEXT ====================\n"
            "The following information was retrieved from the codebase.\n"
            "Use it to answer the user's question.\n\n"
        )

        footer = (
            "\n=================================================\n"
        )

        return header + "\n".join(sections) + footer

    def _format_result(
        self,
        result: Dict,
        rank: int,
    ) -> str:
        """
        Format a single retrieval result.
        """

        symbol_name = result.get("symbol_name", "Unknown")
        symbol_type = result.get("symbol_type", "Unknown")
        file_path = result.get("file", "Unknown")
        language = result.get("language", "Unknown")
        retrieval_text = result.get("retrieval_text", "")

        distance_line = ""

        if self.include_distance:
            distance = result.get("distance", "N/A")
            distance_line = f"Distance: {distance}\n"

        section = (
            f"Result Rank: {rank}\n"
            f"Type: {symbol_type}\n"
            f"Name: {symbol_name}\n"
            f"File: {file_path}\n"
            f"Language: {language}\n"
            f"{distance_line}"
            f"\n"
            f"{retrieval_text}\n"
            f"\n"
            f"{'-' * 60}\n"
        )

        return section


if __name__ == "__main__":

    sample_results = [
        {
            "symbol_name": "clone_repository",
            "symbol_type": "function",
            "file": "src/ingestion/clone_repo.py",
            "language": "python",
            "distance": 0.3386,
            "retrieval_text": (
                "Function: clone_repository\n"
                "Purpose: Clone a GitHub repository locally."
            ),
        },
        {
            "symbol_name": "parse_repository",
            "symbol_type": "function",
            "file": "src/parsing/parser.py",
            "language": "python",
            "distance": 0.5597,
            "retrieval_text": (
                "Function: parse_repository\n"
                "Purpose: Parse repository files and build symbols."
            ),
        },
    ]

    builder = ContextBuilder()

    context = builder.build_context(sample_results)

    print(context)