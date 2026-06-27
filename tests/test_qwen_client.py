import pytest
from unittest.mock import patch, MagicMock
from src.llm.qwen_client import QwenClient


def test_qwen_client_init_defaults():
    client = QwenClient()
    assert client.model_name == "qwen2.5:3b"
    assert client.temperature == 0.1
    assert client.max_tokens == 512


def test_qwen_client_init_custom():
    client = QwenClient(model_name="qwen2.5:1.5b", temperature=0.5, max_tokens=100)
    assert client.model_name == "qwen2.5:1.5b"
    assert client.temperature == 0.5
    assert client.max_tokens == 100


@patch("src.llm.qwen_client.ollama.chat")
def test_qwen_client_generate(mock_chat):
    # Setup mock response
    mock_chat.return_value = {
        "message": {
            "content": "  This is a mocked response.  "
        }
    }

    client = QwenClient(model_name="test-model", temperature=0.2, max_tokens=256)
    prompt = "Hello Qwen"
    response = client.generate(prompt)

    # Assert correct return value and stripping
    assert response == "This is a mocked response."

    # Assert ollama.chat was called with correct parameters
    mock_chat.assert_called_once_with(
        model="test-model",
        messages=[
            {
                "role": "user",
                "content": "Hello Qwen",
            }
        ],
        options={
            "temperature": 0.2,
            "num_predict": 256,
        }
    )


@patch("src.llm.qwen_client.ollama.chat")
def test_qwen_client_generate_error(mock_chat):
    mock_chat.side_effect = Exception("Ollama connection failed")

    client = QwenClient()
    with pytest.raises(Exception) as exc_info:
        client.generate("Hello")
    
    assert "Ollama connection failed" in str(exc_info.value)
