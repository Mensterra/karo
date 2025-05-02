# karo/providers/gemini_provider.py
import os
import instructor
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError # Import specific Google errors
from pydantic import BaseModel, Field, SecretStr, ValidationError
from typing import Any, Type, List, Dict, Optional, Union, Literal

from karo.providers.base_provider import BaseProvider
from karo.schemas.base_schemas import BaseOutputSchema # Assuming this path

# --- Gemini Provider Configuration (Native SDK) ---

class GeminiProviderConfig(BaseModel):
    """
    Configuration specific to the Google Gemini provider using the native SDK.
    """
    type: Literal["gemini"] = Field("gemini", description="Discriminator field for provider type.")
    api_key: Optional[SecretStr] = Field(
        None,
        description="Google API Key for Gemini. If None, attempts to use environment variable GOOGLE_API_KEY."
    )
    model: str = Field(..., description="The specific Gemini model to use (e.g., 'gemini-1.5-flash-latest').")
    # Optional: Add generation_config if needed frequently
    # generation_config: Optional[Dict[str, Any]] = Field(None, description="Gemini generation config (temperature, max_tokens, etc.)")
    instructor_mode: instructor.Mode = Field(
        instructor.Mode.GEMINI_JSON, # Default to JSON mode as per example
        description="Instructor mode (e.g., GEMINI_JSON, GEMINI_TOOLS)."
    )

    class Config:
        arbitrary_types_allowed = True # Allow instructor.Mode

# --- Gemini Provider Implementation (Native SDK) ---

class GeminiProvider(BaseProvider):
    """
    Karo provider implementation for Google Gemini models using the native
    'google-generativeai' library and 'instructor'.
    """

    def __init__(self, config: GeminiProviderConfig):
        """
        Initializes the Gemini provider using the native SDK.

        Args:
            config: An instance of GeminiProviderConfig.

        Raises:
            TypeError: If config is not an instance of GeminiProviderConfig.
            ValueError: If API key is missing.
            ConnectionError: If the client fails to initialize or configure.
        """
        if not isinstance(config, GeminiProviderConfig):
            raise TypeError("config must be an instance of GeminiProviderConfig")

        self.config = config

        # Resolve API Key: Config > Environment Variable
        api_key_value: Optional[str] = None
        if self.config.api_key:
            api_key_value = self.config.api_key.get_secret_value()
        else:
            api_key_from_env = os.getenv("GOOGLE_API_KEY")
            if api_key_from_env:
                api_key_value = api_key_from_env
            else:
                raise ValueError("Gemini API Key not found. Provide it in config or set GOOGLE_API_KEY environment variable.")

        try:
            # Configure the genai library globally (standard practice)
            genai.configure(api_key=api_key_value)

            # Initialize the raw Gemini client
            raw_client = genai.GenerativeModel(
                model_name=self.config.model,
                # generation_config can be passed here globally or per-request
            )

            # Patch the client with instructor using the appropriate function
            self.client = instructor.from_gemini(
                client=raw_client,
                mode=self.config.instructor_mode # Use mode from config
            )
        except Exception as e:
            # Catch potential configuration or initialization errors
            print(f"Failed to initialize or configure Gemini client: {e}")
            raise ConnectionError(f"Failed to initialize Gemini client: {e}") from e

    def get_client(self) -> Any:
        """
        Returns the underlying, instructor-patched Gemini client instance.
        """
        return self.client

    def get_model_name(self) -> str:
        """Returns the specific Gemini model name being used."""
        return self.config.model

    def generate_response(
        self,
        prompt: List[Dict[str, str]],
        output_schema: Type[BaseOutputSchema],
        **kwargs # Accepts generation_config, etc.
    ) -> BaseOutputSchema:
        """
        Generates a response from the Gemini model, enforcing the output schema.

        Args:
            prompt: The message list for the chat completion (should align with Gemini format).
                    Instructor typically handles the conversion from OpenAI format if needed.
            output_schema: The Pydantic model for the desired response structure.
            **kwargs: Additional arguments for the Gemini API call, like 'generation_config'.
                      Example: generate_response(..., generation_config={"temperature": 0.7})

        Returns:
            An instance of the specified output_schema.

        Raises:
            GoogleAPIError: If the Google API returns an error.
            ValidationError: If the response fails Pydantic validation against the schema.
            Exception: For other unexpected errors during the API call.
        """
        try:
            # Instructor's patched client often uses chat.completions.create for consistency
            # It maps the arguments to the underlying Gemini SDK call.
            # Pass kwargs directly, allowing 'generation_config' etc. to be included.
            response = self.client.chat.completions.create(
                messages=prompt, # Instructor handles mapping if needed
                response_model=output_schema,
                **kwargs # Pass through generation_config, etc.
            )
            return response

        except ValidationError as e:
             print(f"Gemini response validation error: {e}")
             raise
        except GoogleAPIError as e:
            print(f"Google API Error: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error during Gemini call: {e}")
            raise

# --- End Gemini Provider ---