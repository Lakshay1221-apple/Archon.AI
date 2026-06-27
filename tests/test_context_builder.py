import pytest
from src.retrieval.context_builder import ContextBuilder


def test_build_context_empty():
    builder = ContextBuilder()
    context = builder.build_context([])
    assert context == "No relevant context found."


def test_build_context_success():
    builder = ContextBuilder(include_distance=True)
    sample_results = [
        {
            "symbol_name": "test_func",
            "symbol_type": "function",
            "file": "test_file.py",
            "language": "python",
            "distance": 0.25,
            "retrieval_text": "def test_func(): pass",
        }
    ]
    context = builder.build_context(sample_results)
    assert "==================== CONTEXT ====================" in context
    assert "Result Rank: 1" in context
    assert "Type: function" in context
    assert "Name: test_func" in context
    assert "File: test_file.py" in context
    assert "Language: python" in context
    assert "Distance: 0.25" in context
    assert "def test_func(): pass" in context
    assert "-" * 60 in context


def test_build_context_no_distance():
    builder = ContextBuilder(include_distance=False)
    sample_results = [
        {
            "symbol_name": "test_func",
            "symbol_type": "function",
            "file": "test_file.py",
            "language": "python",
            "distance": 0.25,
            "retrieval_text": "def test_func(): pass",
        }
    ]
    context = builder.build_context(sample_results)
    assert "Distance:" not in context


def test_build_context_max_chars():
    # Make max_context_chars just large enough for func_1's formatted string (around 182 chars)
    # but not enough for func_1 + func_2.
    builder = ContextBuilder(max_context_chars=200)
    sample_results = [
        {
            "symbol_name": "func_1",
            "symbol_type": "function",
            "file": "test_file.py",
            "language": "python",
            "retrieval_text": "def func_1(): pass",
        },
        {
            "symbol_name": "func_2",
            "symbol_type": "function",
            "file": "test_file.py",
            "language": "python",
            "retrieval_text": "def func_2(): pass",
        }
    ]
    context = builder.build_context(sample_results)
    assert "Name: func_1" in context
    # func_2 should be excluded because adding it exceeds 200 characters limit
    assert "Name: func_2" not in context


def test_build_context_missing_keys():
    builder = ContextBuilder()
    sample_results = [{}]
    context = builder.build_context(sample_results)
    assert "Name: Unknown" in context
    assert "Type: Unknown" in context
    assert "File: Unknown" in context
    assert "Language: Unknown" in context
    assert "Distance: N/A" in context
