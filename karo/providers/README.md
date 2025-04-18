# Karo Framework - Providers

This directory contains the implementations for interacting with different Large Language Model (LLM) providers. The goal is to abstract the specifics of each provider's API behind a common interface defined by `BaseProvider`.

## Core Concepts

*   **`BaseProvider` (`base_provider.py`):** An Abstract Base Class (ABC) that defines the required methods and properties for any provider integration. Key methods include `__init__`, `get_client`, `get_model_name`, and `generate_response`.
*   **Concrete Providers (e.g., `openai_provider.py`):** Classes that inherit from `BaseProvider` and implement the abstract methods for a specific LLM service (like OpenAI, Anthropic, Groq, Ollama, etc.). Each provider typically has its own Pydantic configuration model (e.g., `OpenAIProviderConfig`) to handle provider-specific settings like API keys, model names, and base URLs.
*   **Instructor Integration:** Providers are expected to return an `instructor`-patched client via `get_client()`. The `generate_response` method leverages this patched client to make the LLM API call and automatically validate the response against the Pydantic schema provided by the `BaseAgent`.

## How it Works

1.  A concrete provider (e.g., `OpenAIProvider`) is instantiated with its specific configuration (`OpenAIProviderConfig`).
2.  This provider instance is passed to the `BaseAgent` during its initialization via the `BaseAgentConfig`.
3.  When the `BaseAgent`'s `run` method is called, it invokes the `generate_response` method on its configured `provider` instance.
4.  The provider's `generate_response` method handles the actual API call to the specific LLM service, using the `instructor`-patched client to ensure the output matches the required schema.

This abstraction allows the `BaseAgent` to remain agnostic to the underlying LLM provider, making it easy to swap providers by simply changing the provider instance passed in the `BaseAgentConfig`.

## Adding New Providers

To add support for a new LLM provider:

1.  Create a new configuration model (inheriting from Pydantic's `BaseModel`) for the provider's specific settings.
2.  Create a new provider class (e.g., `AnthropicProvider`) that inherits from `BaseProvider`.
3.  Implement the required abstract methods (`__init__`, `get_client`, `get_model_name`, `generate_response`) using the provider's official Python library and patching its client with `instructor`.
4.  Ensure `generate_response` correctly calls the provider's API and returns the validated Pydantic schema instance.