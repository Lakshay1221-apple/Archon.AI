import pytest
from src.llm.prompt_builder import PromptBuilder


def test_default_system_prompt():
    builder = PromptBuilder()
    assert builder.system_prompt == PromptBuilder.DEFAULT_SYSTEM_PROMPT


def test_custom_system_prompt():
    custom_sys = "You are a helpful assistant."
    builder = PromptBuilder(system_prompt=custom_sys)
    assert builder.system_prompt == custom_sys


def test_build_prompt():
    builder = PromptBuilder()
    query = "What is love?"
    context = "Baby don't hurt me"
    prompt = builder.build_prompt(query=query, context=context)

    # Check that system prompt is in there
    assert builder.system_prompt.strip() in prompt
    # Check that retrieved context header/footer are in there
    assert "==================== RETRIEVED CONTEXT ====================" in prompt
    assert context in prompt
    # Check query and footer
    assert "User Question:\nWhat is love?" in prompt
    assert "Answer:" in prompt
