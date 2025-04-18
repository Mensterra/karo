from abc import ABC, abstractmethod
from typing import Any, Type, List, Dict, Optional, Union

# Assuming BaseOutputSchema might be needed for type hinting, adjust if necessary
from karo.schemas.base_schemas import BaseOutputSchema

class BaseProvider(ABC):
    """
    Abstract Base Class for LLM providers in the Karo framework.
    Defines the interface for interacting with different language models.
    """

    @abstractmethod
    def __init__(self, config: Any):
        """
        Initialize the provider with its specific configuration.
        The config type can vary depending on the provider.
        """
        pass

    @abstractmethod
    def get_client(self) -> Any:
        """
        Returns the underlying, instructor-patched client instance used by the provider.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Returns the specific model name being used by this provider instance.
        """
        pass

    @abstractmethod
    def generate_response(
        self,
        prompt: List[Dict[str, str]],
        output_schema: Type[BaseOutputSchema],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None, # e.g., "auto", "none", {"type": "function", "function": {"name": "my_tool"}}
        **kwargs
    ) -> Union[BaseOutputSchema, Any]: # Can return validated schema OR raw response (e.g., with tool_calls)
        """
        Generates a response from the LLM, potentially using tools.

        If tools are provided and the LLM decides to use one, this method might return
        the raw response object containing tool call information instead of the validated
        output_schema instance. The calling agent is responsible for handling this.

        Args:
            prompt: The message list for the LLM.
            output_schema: The Pydantic model for the final desired response structure
                           (used by instructor if no tool call occurs or after tool execution).
            tools: Optional list of tools in the format expected by the LLM API.
            tool_choice: Optional tool choice parameter for the LLM API.
            **kwargs: Additional provider-specific arguments (e.g., temperature).

        Returns:
            - An instance of the specified output_schema if the LLM provides a direct answer
              that validates against the schema.
            - The raw response object from the LLM client (type Any) if the response
              contains tool calls or cannot be validated against the output_schema directly.

        Raises:
            NotImplementedError: If the provider does not implement this method.
            Exception: Provider-specific exceptions related to API calls or validation.
        """
        raise NotImplementedError("Provider must implement the 'generate_response' method.")

    # Optional: Add other common methods if needed, e.g., for streaming, embeddings, etc.