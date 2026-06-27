"""
src/llm/prompt_builder.py

Builds the final RAG prompt that is sent to the LLM.
"""

from typing import Optional


class PromptBuilder:
    """
    Creates prompts for repository question answering.
    """

    DEFAULT_SYSTEM_PROMPT = """
You are Archon AI, an expert codebase and repository assistant.

Your job is to answer questions using ONLY the provided repository context.

Rules:
1. Use only the supplied context.
2. Do not invent code, functions, files, or classes.
3. If the answer is not present in the context, say:
   "I could not find enough information in the retrieved context."
4. Cite relevant functions, classes, or files when possible.
5. Be concise but technically accurate.
"""

    def __init__(
        self,
        system_prompt: Optional[str] = None,
    ):
        self.system_prompt = (
            system_prompt or self.DEFAULT_SYSTEM_PROMPT
        )

    def build_prompt(
        self,
        query: str,
        context: str,
    ) -> str:
        """
        Build the final prompt.

        Args:
            query: User question
            context: Retrieved context from ContextBuilder

        Returns:
            Complete prompt string
        """

        prompt = f"""
{self.system_prompt}

==================== RETRIEVED CONTEXT ====================

{context}

===========================================================

User Question:
{query}

Answer:
"""

        return prompt.strip()


if __name__ == "__main__":

    sample_query = "How are repositories cloned?"

    sample_context = """
Function: clone_repository

Purpose:
Clone GitHub repositories locally.

File:
src/ingestion/clone_repo.py
"""

    builder = PromptBuilder()

    prompt = builder.build_prompt(
        query=sample_query,
        context=sample_context,
    )

    print(prompt)