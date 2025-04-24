import instructor
from openai import OpenAI, APIError, RateLimitError # Import specific errors if needed for handling
from pydantic import BaseModel, Field, SecretStr, HttpUrl, ValidationError
from typing import Any, Type, List, Dict, Optional

from karo.providers.base_provider import BaseProvider
from karo.schemas.base_schemas import BaseOutputSchema

from typing import Literal # Import Literal

class OpenAIProviderConfig(BaseModel):
    """
    Configuration specific to the OpenAI provider.
    """
    type: Literal["openai"] = Field("openai", description="Discriminator field for provider type.")
    api_key: Optional[SecretStr] = Field(None, description="OpenAI API key. If None, attempts to use environment variable OPENAI_API_KEY.")
    base_url: Optional[HttpUrl] = Field(None, description="Optional custom base URL for the OpenAI API (e.g., for proxies).")
    organization: Optional[str] = Field(None, description="Optional OpenAI organization ID.")
    model: str = Field(..., description="The specific OpenAI model to use (e.g., 'gpt-4o-mini', 'gpt-4-turbo').")
    # Add other OpenAI client parameters as needed (e.g., timeout, max_retries)

    class Config:
        arbitrary_types_allowed = True

class OpenAIProvider(BaseProvider):
    """
    Karo provider implementation for OpenAI models.
    Uses the official 'openai' library and 'instructor' for schema enforcement.
    """

    def __init__(self, config: OpenAIProviderConfig):
        """
        Initializes the OpenAI provider.

        Args:
            config: An instance of OpenAIProviderConfig.
        """
        if not isinstance(config, OpenAIProviderConfig):
            raise TypeError("config must be an instance of OpenAIProviderConfig")

        self.config = config
        api_key_value = self.config.api_key.get_secret_value() if self.config.api_key else None

        try:
            # Initialize the OpenAI client
            raw_client = OpenAI(
                api_key=api_key_value,
                base_url=str(self.config.base_url) if self.config.base_url else None,
                organization=self.config.organization,
                # Add other parameters like timeout, max_retries here if included in config
            )
            # Patch the client with instructor
            self.client = instructor.from_openai(raw_client)
        except Exception as e:
            # Handle potential initialization errors (e.g., invalid API key format - though OpenAI lib might handle this)
            # Consider logging the error
            raise ConnectionError(f"Failed to initialize OpenAI client: {e}") from e

    def get_client(self) -> Any:
        """Returns the underlying, instructor-patched OpenAI client instance."""
        return self.client

    def get_model_name(self) -> str:
        """Returns the specific OpenAI model name being used."""
        return self.config.model

    def generate_response(
        self,
        prompt: List[Dict[str, str]],
        output_schema: Type[BaseOutputSchema],
        # Removed tools and tool_choice parameters
        **kwargs
    ) -> BaseOutputSchema: # Return type is now always the validated schema
        """
        Generates a response from the OpenAI LLM, enforcing the output schema.

        Args:
            prompt: The message list for the chat completion.
            output_schema: The Pydantic model for the desired response structure.
            **kwargs: Additional arguments for the OpenAI chat completions API
                      (e.g., temperature, max_tokens).

        Returns:
            An instance of output_schema.

        Raises:
            APIError: If the OpenAI API returns an error.
            RateLimitError: If the rate limit is exceeded.
            Exception: For other unexpected errors during the API call.
            ValidationError: If the response fails Pydantic validation (handled by instructor).
        """
        try:
            # Prepare arguments for the OpenAI API call
            api_kwargs = {
                "model": self.config.model,
                "messages": prompt,
                "response_model": output_schema, # Always enforce the output schema
                **kwargs
            }

            # Removed logic for adding tools and tool_choice

            # Make the API call using the instructor-patched client
            # Instructor will handle validation against the output_schema
            response = self.client.chat.completions.create(**api_kwargs)

            # Response should now always be the validated output_schema instance
            # due to instructor's handling when response_model is provided.
            return response

        except ValidationError as e:
             # Instructor raises ValidationError if response_model is set and validation fails
             print(f"OpenAI response validation error: {e}")
             raise # Re-raise validation error for the agent to handle

        except (APIError, RateLimitError) as e:
            # Log the specific API error
            print(f"OpenAI API Error: {e}")
            # Re-raise or wrap in a custom provider error if desired
            raise
        except Exception as e:
            # Log unexpected errors
            print(f"Unexpected error during OpenAI call: {e}")
            # Re-raise or wrap
            raise