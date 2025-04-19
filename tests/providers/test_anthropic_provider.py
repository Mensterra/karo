import pytest
from unittest.mock import patch, MagicMock, ANY
import os
import json

# Import necessary components
from karo.providers.anthropic_provider import AnthropicProvider, AnthropicProviderConfig
from karo.schemas.base_schemas import BaseOutputSchema
from pydantic import SecretStr, BaseModel

# Define a simple output schema for testing
class SimpleOutput(BaseOutputSchema):
    response_message: str

# --- Fixtures ---

@pytest.fixture
def anthropic_config():
    """Provides a basic AnthropicProviderConfig."""
    # Set dummy key in env var for initialization test
    os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key-env"
    config = AnthropicProviderConfig(
        # api_key=SecretStr("test-anthropic-key-direct"), # Test direct key passing if needed
        model="claude-3-sonnet-20240229"
    )
    yield config # Use yield to allow cleanup
    # Clean up env var
    if "ANTHROPIC_API_KEY" in os.environ and os.environ["ANTHROPIC_API_KEY"] == "test-anthropic-key-env":
        del os.environ["ANTHROPIC_API_KEY"]

# --- Test Class ---

@patch('karo.providers.anthropic_provider.instructor.from_anthropic')
@patch('karo.providers.anthropic_provider.anthropic.Anthropic')
class TestAnthropicProvider:

    def test_initialization_success(self, mock_anthropic_client_class, mock_from_anthropic, anthropic_config):
        """Tests successful initialization and client patching."""
        mock_patched_client = MagicMock()
        mock_from_anthropic.return_value = mock_patched_client
        mock_raw_client_instance = MagicMock()
        mock_anthropic_client_class.return_value = mock_raw_client_instance

        provider = AnthropicProvider(config=anthropic_config)

        # Assert client was called, allowing it to handle env var internally if api_key is None
        mock_anthropic_client_class.assert_called_once_with(api_key=None) # Provider passes None if not in config
        mock_from_anthropic.assert_called_once_with(mock_raw_client_instance)
        assert provider.client == mock_patched_client
        assert provider.raw_client == mock_raw_client_instance
        assert provider.get_model_name() == anthropic_config.model

    def test_initialization_no_api_key(self, mock_anthropic_client_class, mock_from_anthropic):
        """Tests initialization failure when API key is missing."""
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        config = AnthropicProviderConfig(model="claude-3-haiku-20240307", api_key=None)

        # Anthropic client init might raise its own error or just proceed
        # Let's assume it proceeds and instructor patching might fail, or usage fails later
        # For now, just test that init doesn't immediately raise *our* ValueError
        try:
            AnthropicProvider(config=config)
        except Exception as e:
            pytest.fail(f"Initialization raised unexpected error with missing key: {e}")
        # A better test might mock the client's internal key check if possible

    def test_generate_response_simple(self, mock_anthropic_client_class, mock_from_anthropic, anthropic_config):
        """Tests generate_response for a simple case without tools."""
        mock_patched_client = MagicMock()
        mock_from_anthropic.return_value = mock_patched_client
        mock_anthropic_client_class.return_value = MagicMock() # Raw client mock

        provider = AnthropicProvider(config=anthropic_config)

        prompt = [
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": "Hello"}
        ]
        expected_output = SimpleOutput(response_message="Hi")
        # Mock the patched client's messages.create method
        provider.client.messages.create.return_value = expected_output

        result = provider.generate_response(prompt=prompt, output_schema=SimpleOutput, temperature=0.5, max_tokens=50)

        assert result == expected_output
        provider.client.messages.create.assert_called_once()
        call_args = provider.client.messages.create.call_args
        # Check args passed to messages.create
        assert call_args.kwargs['model'] == anthropic_config.model
        assert call_args.kwargs['system'] == "Be brief."
        assert call_args.kwargs['messages'] == [{"role": "user", "content": "Hello"}] # Check formatted prompt
        assert call_args.kwargs['response_model'] == SimpleOutput
        assert call_args.kwargs['temperature'] == 0.5
        assert call_args.kwargs['max_tokens'] == 50
        assert 'tools' not in call_args.kwargs # No tools passed

    def test_generate_response_with_tools(self, mock_anthropic_client_class, mock_from_anthropic, anthropic_config):
        """Tests generate_response when tools are provided."""
        mock_patched_client = MagicMock()
        mock_from_anthropic.return_value = mock_patched_client
        mock_anthropic_client_class.return_value = MagicMock()

        provider = AnthropicProvider(config=anthropic_config)

        prompt = [{"role": "user", "content": "Use a tool"}]
        # Simulate OpenAI-style tool format passed from BaseAgent
        tools_input = [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}
            }
        }]
        # Simulate a raw response indicating a tool call (structure might vary)
        mock_raw_tool_response = MagicMock() # Simulate Anthropic's response object
        # Add attributes to mimic a tool call response if possible/needed for BaseAgent handling
        # For now, just return the mock object

        provider.client.messages.create.return_value = mock_raw_tool_response

        result = provider.generate_response(prompt=prompt, output_schema=SimpleOutput, tools=tools_input, tool_choice="auto")

        # Assert that the raw response is returned when tools are involved
        assert result == mock_raw_tool_response
        provider.client.messages.create.assert_called_once()
        call_args = provider.client.messages.create.call_args
        # Check that formatted tools were passed
        assert call_args.kwargs['tools'] is not None
        assert len(call_args.kwargs['tools']) == 1
        assert call_args.kwargs['tools'][0]['name'] == "get_weather" # Check Anthropic format
        assert call_args.kwargs['tools'][0]['input_schema'] is not None
        # assert call_args.kwargs['tool_choice'] == "auto" # Anthropic handles tool choice differently, often implicitly or via specific params not mocked here
        assert call_args.kwargs['response_model'] == SimpleOutput # Still pass response_model

    # Add tests for error handling (API errors, validation errors) later
    # Add tests for prompt formatting with tool results