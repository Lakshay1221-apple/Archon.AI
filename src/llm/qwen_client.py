"""
src/llm/qwen_client.py

Local Qwen inference client using Ollama.
"""

from typing import Optional

import ollama


class QwenClient:
    """
    Wrapper around a local Qwen model served by Ollama.
    """

    def __init__(
        self,
        model_name: str = "qwen2.5:3b",
        temperature: float = 0.1,
        max_tokens: int = 512,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(
        self,
        prompt: str,
    ) -> str:
        """
        Generate a response from Qwen.

        Args:
            prompt: Fully constructed RAG prompt.

        Returns:
            Generated answer.
        """

        response = ollama.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            options={
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        )

        return response["message"]["content"].strip()


if __name__ == "__main__":
    # Determine model to use based on local availability
    model_name = "qwen2.5:3b"
    try:
        models_response = ollama.list()
        available_models = []
        if hasattr(models_response, "models"):
            available_models = [m.model for m in models_response.models]
        elif isinstance(models_response, dict) and "models" in models_response:
            available_models = [m.get("model") for m in models_response["models"]]

        if model_name not in available_models and "qwen2.5:1.5b" in available_models:
            print("Model 'qwen2.5:3b' not found locally. Falling back to 'qwen2.5:1.5b'.")
            model_name = "qwen2.5:1.5b"
    except Exception as e:
        print(f"Error checking available Ollama models: {e}")

    client = QwenClient(model_name=model_name)

    prompt = """
You are Archon AI.

Question:
How are repositories cloned?

Answer:
"""

    response = client.generate(prompt)

    print("\n=== RESPONSE ===\n")
    print(response)