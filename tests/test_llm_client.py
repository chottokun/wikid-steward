from unittest.mock import MagicMock, patch

from wikid_steward.core.llm_client import LLMConfig, OpenAICompatibleLLMClient


def test_llm_config_custom_values():
    config = LLMConfig(
        base_url="http://localhost:11434/v1",
        api_key="test-key",
        model="test-model",
        temperature=0.5,
        max_tokens=1024,
    )
    assert config.base_url == "http://localhost:11434/v1"
    assert config.api_key == "test-key"
    assert config.model == "test-model"
    assert config.temperature == 0.5
    assert config.max_tokens == 1024


@patch("wikid_steward.core.llm_client.get_config")
def test_llm_config_fallback_to_global_config(mock_get_config):
    mock_global_cfg = MagicMock()
    mock_global_cfg.llm.base_url = "http://global-url/v1"
    mock_global_cfg.llm.api_key = "global-key"
    mock_global_cfg.llm.model = "global-model"
    mock_get_config.return_value = mock_global_cfg

    config = LLMConfig()
    assert config.base_url == "http://global-url/v1"
    assert config.api_key == "global-key"
    assert config.model == "global-model"


def test_generate_delegates_to_generate_chat_completion():
    config = LLMConfig(base_url="http://dummy", model="dummy-model")
    client = OpenAICompatibleLLMClient(config=config)

    with patch.object(
        client, "generate_chat_completion", return_value="generated response"
    ) as mock_gcc:
        result = client.generate(
            prompt="Tell me a joke",
            system_prompt="Be funny",
            model_override="funny-model",
            temperature=0.9,
        )

        assert result == "generated response"
        mock_gcc.assert_called_once_with(
            messages=[{"role": "user", "content": "Tell me a joke"}],
            system_prompt="Be funny",
            model_override="funny-model",
            temperature=0.9,
        )


def test_generate_default_parameters():
    config = LLMConfig(base_url="http://dummy", model="dummy-model")
    client = OpenAICompatibleLLMClient(config=config)

    with patch.object(
        client, "generate_chat_completion", return_value="default response"
    ) as mock_gcc:
        result = client.generate(prompt="Hello")

        assert result == "default response"
        mock_gcc.assert_called_once_with(
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt=None,
            model_override=None,
            temperature=None,
        )


def test_generate_chat_completion_success():
    config = LLMConfig(
        base_url="http://dummy",
        model="default-model",
        temperature=0.2,
        max_tokens=2048,
    )
    client = OpenAICompatibleLLMClient(config=config)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "   Response text with spaces.  \n"
    client.client.chat.completions.create = MagicMock(return_value=mock_response)

    messages = [{"role": "user", "content": "Hi"}]
    result = client.generate_chat_completion(
        messages=messages,
        system_prompt="You are helpful.",
        model_override="override-model",
        temperature=0.8,
    )

    assert result == "Response text with spaces."
    client.client.chat.completions.create.assert_called_once_with(
        model="override-model",
        messages=[
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ],
        temperature=0.8,
        max_tokens=2048,
    )


def test_generate_chat_completion_defaults_and_null_content():
    config = LLMConfig(
        base_url="http://dummy",
        model="default-model",
        temperature=0.2,
        max_tokens=100,
    )
    client = OpenAICompatibleLLMClient(config=config)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    client.client.chat.completions.create = MagicMock(return_value=mock_response)

    messages = [{"role": "user", "content": "Hi"}]
    result = client.generate_chat_completion(messages=messages)

    assert result == ""
    client.client.chat.completions.create.assert_called_once_with(
        model="default-model",
        messages=[{"role": "user", "content": "Hi"}],
        temperature=0.2,
        max_tokens=100,
    )
