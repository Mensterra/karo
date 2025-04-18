import pytest
from unittest.mock import MagicMock, patch, ANY
from pydantic import ValidationError
from typing import Any, Type, List, Dict, Optional
from typing import Any, Type, List, Dict, Optional, Union # Added Union
import json

# Assuming pytest is installed as a dev dependency
# Need to ensure karo package is discoverable (e.g., by running pytest from the root karo/ directory)
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema
from karo.providers.base_provider import BaseProvider
from karo.tools.base_tool import BaseTool
from karo.tools.calculator_tool import CalculatorTool, CalculatorInput, CalculatorOutput # Import example tool
from karo.prompts.system_prompt_builder import SystemPromptBuilder # Import builder

# --- Mock Provider for Testing ---
class MockProvider(BaseProvider):
    """A simple mock provider for testing BaseAgent."""
    def __init__(self, config: Any = None, return_value: Any = None):
        self._model_name = "mock-model"
        # Mock the generate_response method directly on the instance
        # Allow setting a default return value for simple cases
        self.generate_response = MagicMock(return_value=return_value)

    def get_client(self) -> Any:
        return None # No real client needed

    def get_model_name(self) -> str:
        return self._model_name

    def generate_response(
        self,
        prompt: List[Dict[str, str]],
        output_schema: Type[BaseOutputSchema],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> Union[BaseOutputSchema, Any]: # Match updated signature
        """Abstract method implementation (will be replaced by MagicMock)."""
        # This method's body is irrelevant because we replace it with a MagicMock
        # in __init__. We just need it defined to satisfy the ABC.
        # The actual mock behavior is set via self.generate_response in tests.
        raise NotImplementedError("This should be mocked on the instance.")

@pytest.fixture
def mock_provider():
    """Provides an instance of the MockProvider."""
    # Pass a default response for simple tests
    return MockProvider(return_value=BaseOutputSchema(response_message="Default mock response"))

@pytest.fixture
def mock_prompt_builder():
    """Provides a mock SystemPromptBuilder."""
    builder = MagicMock(spec=SystemPromptBuilder)
    # Configure the mock build method to return a predictable string
    builder.build.return_value = "Mock System Prompt Built"
    return builder

@pytest.fixture
def agent_config(mock_provider, mock_prompt_builder):
    """Provides a BaseAgentConfig instance using mocks."""
    calculator = CalculatorTool()
    return BaseAgentConfig(
        provider=mock_provider,
        prompt_builder=mock_prompt_builder, # Use the mock builder
        tools=[calculator]
    )

@pytest.fixture
def base_agent(agent_config):
    """Provides a BaseAgent instance initialized with the mock config."""
    return BaseAgent(config=agent_config)

def test_base_agent_initialization(agent_config, mock_provider, mock_prompt_builder):
    """Tests if BaseAgent initializes correctly with provider and builder."""
    agent = BaseAgent(config=agent_config)
    assert agent.config == agent_config
    assert agent.provider == mock_provider
    assert agent.prompt_builder == mock_prompt_builder # Check builder is stored
    assert agent.config.input_schema == BaseInputSchema
    assert agent.config.output_schema == BaseOutputSchema
    assert len(agent.tools) == 1
    assert agent.tools[0].get_name() == "calculator"
    assert agent.llm_tools is not None
    assert len(agent.llm_tools) == 1
    assert agent.llm_tools[0]["function"]["name"] == "calculator"

def test_base_agent_run_success(base_agent, mock_provider):
    """Tests the run method calls the provider's generate_response."""
    input_message = "Hello Test"
    input_data = BaseInputSchema(chat_message=input_message)
    expected_response = BaseOutputSchema(response_message="Mocked response")
    # Expected prompt now uses the builder's output
    expected_system_content = base_agent.prompt_builder.build.return_value
    expected_prompt = [
        {"role": "system", "content": expected_system_content},
        {"role": "user", "content": input_message},
    ]

    # Configure the mock provider's generate_response to return the expected output
    mock_provider.generate_response.return_value = expected_response

    # Run the agent
    result = base_agent.run(input_data, temperature=0.5) # Pass extra kwarg

    # Assertions
    assert result == expected_response
    # Check that the provider's method was called correctly
    mock_provider.generate_response.assert_called_once_with(
        prompt=expected_prompt,
        output_schema=BaseOutputSchema,
        tools=base_agent.llm_tools, # Check tools are passed (Fix: use base_agent)
        tool_choice="auto",    # Check tool_choice is passed
        temperature=0.5        # Check that kwargs are passed through
    )

def test_base_agent_run_input_validation_error(base_agent, mock_provider):
    """Tests the run method's input validation."""
    # Create input data that does NOT match the expected BaseInputSchema
    # For example, pass a dictionary instead of a Pydantic model instance
    invalid_input_data = {"wrong_field": "some value"}

    result = base_agent.run(invalid_input_data) # type: ignore

    assert isinstance(result, AgentErrorSchema)
    assert result.error_type == "InputValidationError"
    assert "Input data does not conform to the expected schema" in result.error_message
    # Ensure the provider was NOT called
    mock_provider.generate_response.assert_not_called()

def test_base_agent_config_type_error(mock_provider):
    """Tests that BaseAgent raises TypeError if config is not BaseAgentConfig."""
    # Test initialization with invalid config type
    with pytest.raises(TypeError):
        BaseAgent(config={"provider": mock_provider}) # Pass dict instead of config object

    # Test initialization with valid config type but invalid provider type
    invalid_config_data = {"provider": "not_a_provider_instance"}
    with pytest.raises(ValidationError): # Pydantic validation error
         BaseAgentConfig(**invalid_config_data)


# Add more tests later for:
# - Provider raising exceptions (APIError, RateLimitError, etc.)
# - Output validation errors (mock generate_response to return invalid data)
# - Runtime errors during LLM call (when LLM mocking is more detailed)
# - Custom input/output schemas
# - System prompt usage
# - Memory integration alongside tools


# --- Tests for Tool Execution ---

# Helper to create a mock OpenAI-like response object with tool calls
def create_mock_tool_call_response(tool_calls: List[Dict]):
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_choice = MagicMock()

    # Structure mimics OpenAI's ChatCompletion object
    mock_tool_call_objects = []
    for tc in tool_calls:
        mock_func = MagicMock()
        # Fix: Access name/arguments within the 'function' dict
        mock_func.name = tc["function"]["name"]
        mock_func.arguments = tc["function"]["arguments"] # JSON string
        mock_tc_obj = MagicMock()
        mock_tc_obj.id = tc["id"]
        mock_tc_obj.function = mock_func
        mock_tool_call_objects.append(mock_tc_obj)

    mock_message.tool_calls = mock_tool_call_objects
    mock_message.role = "assistant"
    # We need to be able to dump this message later
    mock_message.model_dump.return_value = {"role": "assistant", "tool_calls": tool_calls}


    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    return mock_response

def test_base_agent_run_with_tool_call_success(base_agent, mock_provider, mock_prompt_builder): # Add builder fixture
    """Tests the full tool execution loop: LLM -> Tool -> LLM -> Response."""
    input_message = "What is 5 * 3?"
    input_data = BaseInputSchema(chat_message=input_message)
    # Define expected system prompt from builder for assertion checks
    expected_system_content = mock_prompt_builder.build.return_value
    tool_name = "calculator"
    tool_id = "call_123"
    tool_args_json = json.dumps({"operand1": 5.0, "operand2": 3.0, "operator": "*"})
    tool_result_value = 15.0
    final_response_text = "5 times 3 is 15."

    # --- Mock Setup ---
    # 1. Mock first LLM call to return a tool call request
    mock_tool_call_resp = create_mock_tool_call_response([{
        "id": tool_id,
        "type": "function",
        "function": {"name": tool_name, "arguments": tool_args_json}
    }])

    # 2. Mock the actual tool's run method (assuming CalculatorTool is in agent.tools)
    calculator_tool = base_agent.tool_map[tool_name]
    mock_tool_run = MagicMock(return_value=CalculatorOutput(success=True, result=tool_result_value))
    calculator_tool.run = mock_tool_run # Directly mock the instance's method

    # 3. Mock the second LLM call (after tool execution) to return the final answer
    mock_final_response = BaseOutputSchema(response_message=final_response_text)

    # Set up the provider mock to return responses sequentially
    mock_provider.generate_response.side_effect = [
        mock_tool_call_resp, # First call returns tool request
        mock_final_response  # Second call returns final answer
    ]

    # --- Run Agent ---
    result = base_agent.run(input_data)

    # --- Assertions ---
    # Final result should be the final response schema
    assert isinstance(result, BaseOutputSchema)
    assert result.response_message == final_response_text

    # Check tool was called correctly
    mock_tool_run.assert_called_once()
    # Check the input passed to the tool run method (it's a Pydantic model)
    call_args, _ = mock_tool_run.call_args
    assert isinstance(call_args[0], CalculatorInput)
    assert call_args[0].operand1 == 5.0
    assert call_args[0].operand2 == 3.0
    assert call_args[0].operator == "*"

    # Check provider was called twice
    assert mock_provider.generate_response.call_count == 2

    # Check first provider call arguments
    first_call_args = mock_provider.generate_response.call_args_list[0]
    assert first_call_args.kwargs['tools'] == base_agent.llm_tools
    assert first_call_args.kwargs['tool_choice'] == "auto"
    # Verify user message is present in the first call prompt
    prompt_sent_first_call = first_call_args.kwargs['prompt']
    user_message_found = False
    for msg in prompt_sent_first_call:
        if msg.get("role") == "user":
            assert msg.get("content") == input_message
            user_message_found = True
            break
    assert user_message_found, "User message not found in the prompt for the first call"
    # Check system prompt was generated by builder
    assert prompt_sent_first_call[0]['role'] == 'system'
    assert prompt_sent_first_call[0]['content'] == expected_system_content
    # Verify builder was called correctly for the first LLM call
    mock_prompt_builder.build.assert_called_with(tools=base_agent.llm_tools, memories=[]) # Assuming no memories retrieved here

    # Check second provider call arguments
    second_call_args = mock_provider.generate_response.call_args_list[1] # Get the second call
    assert second_call_args.kwargs['tool_choice'] == "none" # Verify tool_choice is 'none' for the second call
    # Check prompt includes original messages + assistant tool call + tool result
    prompt_history = second_call_args.kwargs['prompt'] # Prompt sent in the second call
    assert len(prompt_history) >= 4 # System, User, Assistant (tool call), Tool (result)
    assert prompt_history[-2]['role'] == 'assistant'
    assert prompt_history[-2]['tool_calls'] is not None # Check assistant message had tool calls
    assert prompt_history[-1]['role'] == 'tool'
    assert prompt_history[-1]['tool_call_id'] == tool_id
    # Content should be the JSON dump of the CalculatorOutput
    tool_result_content = json.loads(prompt_history[-1]['content'])
    assert tool_result_content['success'] is True
    assert tool_result_content['result'] == tool_result_value


def test_base_agent_run_with_tool_call_tool_not_found(base_agent, mock_provider, mock_prompt_builder): # Add builder
    """Tests handling when LLM requests a tool not available to the agent."""
    input_message = "Use the unknown tool."
    input_data = BaseInputSchema(chat_message=input_message)
    tool_name = "unknown_tool"
    tool_id = "call_456"
    tool_args_json = json.dumps({"arg": "value"})
    final_response_text = "Sorry, I cannot use that tool."

    # Mock first LLM call to return unknown tool request
    mock_tool_call_resp = create_mock_tool_call_response([{
        "id": tool_id,
        "type": "function",
        "function": {"name": tool_name, "arguments": tool_args_json}
    }])
    # Mock second LLM call
    mock_final_response = BaseOutputSchema(response_message=final_response_text)
    mock_provider.generate_response.side_effect = [mock_tool_call_resp, mock_final_response]

    result = base_agent.run(input_data)

    assert isinstance(result, BaseOutputSchema)
    assert result.response_message == final_response_text
    assert mock_provider.generate_response.call_count == 2
    # Check the tool message sent back in the second call
    second_call_args = mock_provider.generate_response.call_args_list[1]
    prompt_history = second_call_args.kwargs['prompt']
    assert prompt_history[-1]['role'] == 'tool'
    assert prompt_history[-1]['tool_call_id'] == tool_id
    tool_result_content = json.loads(prompt_history[-1]['content'])
    assert tool_result_content['success'] is False
    assert "Tool 'unknown_tool' not found" in tool_result_content['error_message']


def test_base_agent_run_with_tool_call_invalid_args(base_agent, mock_provider, mock_prompt_builder): # Add builder
    """Tests handling when LLM provides invalid arguments for a tool."""
    input_message = "Calculate 5 plus ?"
    input_data = BaseInputSchema(chat_message=input_message)
    tool_name = "calculator"
    tool_id = "call_789"
    # Invalid JSON
    # tool_args_json = '{"operand1": 5.0, "operator": "+", "operand2": }'
    # OR, valid JSON but invalid schema
    tool_args_json = json.dumps({"operand1": 5.0, "operator": "+", "operand_two": 3.0}) # wrong field name
    final_response_text = "I couldn't understand the arguments for the calculator."

    mock_tool_call_resp = create_mock_tool_call_response([{
        "id": tool_id,
        "type": "function",
        "function": {"name": tool_name, "arguments": tool_args_json}
    }])
    mock_final_response = BaseOutputSchema(response_message=final_response_text)
    mock_provider.generate_response.side_effect = [mock_tool_call_resp, mock_final_response]

    # Mock the tool's run method - it shouldn't be called if args are invalid
    calculator_tool = base_agent.tool_map[tool_name]
    mock_tool_run = MagicMock()
    calculator_tool.run = mock_tool_run

    result = base_agent.run(input_data)

    assert isinstance(result, BaseOutputSchema)
    assert result.response_message == final_response_text
    assert mock_provider.generate_response.call_count == 2
    mock_tool_run.assert_not_called() # Tool run should not be called
    # Check the tool message sent back
    second_call_args = mock_provider.generate_response.call_args_list[1]
    prompt_history = second_call_args.kwargs['prompt']
    assert prompt_history[-1]['role'] == 'tool'
    assert prompt_history[-1]['tool_call_id'] == tool_id
    tool_result_content = json.loads(prompt_history[-1]['content'])
    assert tool_result_content['success'] is False
    assert "Invalid arguments provided" in tool_result_content['error_message']


def test_base_agent_run_with_tool_call_tool_exec_error(base_agent, mock_provider, mock_prompt_builder): # Add builder
    """Tests handling when a tool execution raises an exception."""
    input_message = "Calculate 10 / 0" # Will cause tool error
    input_data = BaseInputSchema(chat_message=input_message)
    tool_name = "calculator"
    tool_id = "call_abc"
    tool_args_json = json.dumps({"operand1": 10.0, "operand2": 0.0, "operator": "/"})
    final_response_text = "There was an error using the calculator."

    mock_tool_call_resp = create_mock_tool_call_response([{
        "id": tool_id,
        "type": "function",
        "function": {"name": tool_name, "arguments": tool_args_json}
    }])
    mock_final_response = BaseOutputSchema(response_message=final_response_text)
    mock_provider.generate_response.side_effect = [mock_tool_call_resp, mock_final_response]

    # Let the actual tool run method execute (which should return an error output)
    # No need to mock calculator_tool.run here

    result = base_agent.run(input_data)

    assert isinstance(result, BaseOutputSchema)
    assert result.response_message == final_response_text
    assert mock_provider.generate_response.call_count == 2
    # Check the tool message sent back
    second_call_args = mock_provider.generate_response.call_args_list[1]
    prompt_history = second_call_args.kwargs['prompt']
    assert prompt_history[-1]['role'] == 'tool'
    assert prompt_history[-1]['tool_call_id'] == tool_id
    tool_result_content = json.loads(prompt_history[-1]['content'])
    assert tool_result_content['success'] is False
    assert "Division by zero" in tool_result_content['error_message']