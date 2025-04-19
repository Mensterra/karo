# Karo LLM Providers

This directory contains implementations for interacting with various Large Language Model (LLM) providers.

## Base Class

*   **`base_provider.py`**: Defines the abstract `BaseProvider` class that all specific provider implementations inherit from. It establishes the common interface, including methods like `generate_response`, `get_client`, and `get_model_name`.

## Supported Providers

*   **`openai_provider.py`**:
    *   Provides integration with OpenAI models (like GPT-4, GPT-3.5) using the `openai` Python library.
    *   Uses `instructor` for response model validation and tool use handling.
    *   **Also supports OpenAI-compatible endpoints**, such as Google Gemini's compatibility layer. Configure using `OpenAIProviderConfig` with the appropriate `api_key`, `model`, and `base_url`.
    *   Requires `openai` and `instructor` libraries.
    *   Expects `OPENAI_API_KEY` environment variable (or passed via config) for OpenAI, or the provider-specific key (e.g., `GOOGLE_API_KEY`) for compatible endpoints.
*   **`anthropic_provider.py`**:
    *   Provides integration with Anthropic Claude models (like Claude 3 Opus, Sonnet, Haiku) using the `anthropic` Python library.
    *   Uses `instructor` for response model validation and tool use handling.
    *   Requires `anthropic` and `instructor` libraries.
    *   Expects `ANTHROPIC_API_KEY` environment variable (or passed via config).

## Adding New Providers

To add support for a new LLM provider:

1.  Create a new file (e.g., `my_provider.py`).
2.  Define a configuration class inheriting from `pydantic.BaseModel` (e.g., `MyProviderConfig`) to hold necessary settings like API keys and model names.
3.  Create a provider class inheriting from `BaseProvider`.
4.  Implement the required methods:
    *   `__init__(self, config: MyProviderConfig)`: Initialize the provider's client library, handle API keys, and potentially patch the client with `instructor` if supported (`instructor.from_...`).
    *   `get_client(self) -> Any`: Return the initialized client instance.
    *   `get_model_name(self) -> str`: Return the configured model name.
    *   `generate_response(...)`: Implement the logic to:
        *   Format the Karo standard prompt (`List[Dict[str, str]]`) into the format expected by the provider's API.
        *   Format the Karo standard tool list (`List[Dict[str, Any]]`) into the format expected by the provider's API.
        *   Call the provider's API (preferably via the `instructor`-patched client) with the formatted prompt, tools, `response_model=output_schema`, and any other relevant parameters (`temperature`, `max_tokens`, etc.).
        *   Handle potential API errors and validation errors.
        *   Return either the validated `output_schema` instance or the raw API response if tool calls are detected (the `BaseAgent` will handle the raw response).
5.  Add necessary client libraries to `pyproject.toml`.
6.  Add unit tests in `tests/providers/`.
7.  Update this README and relevant documentation/examples.