# karo/providers/ollama_provider.py
import os
import instructor
from openai import OpenAI, APIError, RateLimitError, APIConnectionError # Add connection error
from pydantic import BaseModel, Field, SecretStr, HttpUrl, ValidationError
from typing import Any, Type, List, Dict, Optional, Union, Literal

from karo.providers.base_provider import BaseProvider
from karo.schemas.base_schemas import BaseOutputSchema # Assuming this path

# --- Ollama Provider Configuration ---

class OllamaProviderConfig(BaseModel):
    """
    Configuration specific to the Ollama provider.
    Uses the OpenAI client library compatibility.
    """
    type: Literal["ollama"] = Field("ollama", description="Discriminator field.")
    # API Key is usually unused but required by OpenAI client init
    api_key: SecretStr = Field(
        SecretStr("ollama"),
        description="API Key for Ollama (required by OpenAI client, but typically unused)."
    )
    model: str = Field(..., description="The specific Ollama model to use (e.g., 'llama3', 'mistral'). Ensure it's pulled locally.")
    base_url: HttpUrl = Field(
        "http://localhost:11434/v1", # Default Ollama endpoint
        description="Base URL for the local Ollama API server."
    )
    # Mode MUST be JSON for Ollama compatibility as shown in docs
    instructor_mode: Literal[instructor.Mode.JSON] = Field(
        instructor.Mode.JSON,
        description="Instructor mode. MUST be JSON for Ollama.",
        exclude=True # Exclude from serialization if not needed, mode is fixed.
    )

    class Config:
        arbitrary_types_allowed = True

# --- Ollama Provider Implementation ---

class OllamaProvider(BaseProvider):
    """
    Karo provider implementation for local Ollama models using the 'openai'
    library compatibility and 'instructor' in JSON mode.

    Ensure the Ollama server is running and the specified model is pulled.
    """

    def __init__(self, config: OllamaProviderConfig):
        """
        Initializes the Ollama provider.

        Args:
            config: An instance of OllamaProviderConfig.

        Raises:
            TypeError: If config is not OllamaProviderConfig.
            ConnectionError: If the client fails to initialize or connect to Ollama server.
        """
        if not isinstance(config, OllamaProviderConfig):
            raise TypeError("config must be an instance of OllamaProviderConfig")

        self.config = config

        try:
            # Initialize the OpenAI client configured for Ollama
            raw_client = OpenAI(
                api_key=self.config.api_key.get_secret_value(),
                base_url=str(self.config.base_url),
            )
            # Patch with instructor using from_openai and JSON mode
            self.client = instructor.from_openai(
                raw_client,
                mode=instructor.Mode.JSON # Force JSON mode for Ollama
            )
            # Optional: Add a check here to see if Ollama server is reachable
            # try: self.client.models.list() except APIConnectionError: raise...

        except APIConnectionError as e:
             print(f"Failed to connect to Ollama server at {self.config.base_url}. Is it running? {e}")
             raise ConnectionError(f"Failed to connect to Ollama server at {self.config.base_url}") from e
        except Exception as e:
            print(f"Failed to initialize OpenAI client for Ollama: {e}")
            raise ConnectionError(f"Failed to initialize client for Ollama endpoint {self.config.base_url}: {e}") from e

    def get_client(self) -> Any:
        """Returns the instructor-patched OpenAI client configured for Ollama."""
        return self.client

    def get_model_name(self) -> str:
        """Returns the specific Ollama model name being used."""
        return self.config.model

    def generate_response(
        self,
        prompt: List[Dict[str, str]],
        output_schema: Type[BaseOutputSchema],
        **kwargs
    ) -> BaseOutputSchema:
        """
        Generates a response from the local Ollama model, enforcing the output schema.

        Args:
            prompt: The message list for the chat completion.
            output_schema: The Pydantic model for the desired response structure.
            **kwargs: Additional arguments for the OpenAI chat completions API
                      compatible with the Ollama endpoint (e.g., temperature, options).

        Returns:
            An instance of the specified output_schema.

        Raises:
            APIConnectionError: If connection to the Ollama server fails during the call.
            APIError: If the Ollama endpoint returns an API error.
            ValidationError: If the response fails Pydantic validation.
            Exception: For other unexpected errors.
        """
        try:
            api_kwargs = {
                "model": self.config.model,
                "messages": prompt,
                "response_model": output_schema,
                **kwargs
            }
            response = self.client.chat.completions.create(**api_kwargs)
            return response

        except ValidationError as e:
             print(f"Ollama response validation error: {e}")
             raise
        except APIConnectionError as e:
            # Catch connection errors during the actual call too
            print(f"Failed to connect to Ollama server at {self.config.base_url} during API call: {e}")
            raise ConnectionError(f"Connection lost to Ollama server at {self.config.base_url}") from e
        except APIError as e:
            # Catch other API errors from Ollama (might indicate model issues)
            print(f"Ollama API Error (via OpenAI client): {e}")
            raise
        except Exception as e:
            print(f"Unexpected error during Ollama call: {e}")
            raise

# --- End Ollama Provider ---