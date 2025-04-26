from pydantic import BaseModel, Field, ValidationError
from typing import Type, Optional, List, Dict, Any, Union
import logging  # Add logging

from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema
from karo.providers.openai_provider import OpenAIProviderConfig
from karo.providers.anthropic_provider import AnthropicProviderConfig
from karo.providers.ollama_provider import OllamaProviderConfig
from karo.memory.memory_manager import MemoryManagerConfig
from karo.memory.memory_models import MemoryQueryResult
from karo.prompts.system_prompt_builder import SystemPromptBuilder

logger = logging.getLogger(__name__)  # Setup logger


class BaseAgentConfig(BaseModel):
    """
    Configuration for the BaseAgent.
    Accepts configuration objects/dictionaries for components, which are instantiated by BaseAgent.
    """

    # Provider Config: Use a Union of specific provider config models, discriminated by 'type'
    # Note: Pydantic needs a way to know which Union member to use. Add 'type: Literal["openai", "anthropic", ...]' to each ProviderConfig.
    provider_config: Union[
        OpenAIProviderConfig, AnthropicProviderConfig, OllamaProviderConfig
    ] = Field(
        ...,
        description="Configuration object for the LLM provider (e.g., OpenAIProviderConfig). Must include a 'type' field.",
        discriminator="type",
    )
    input_schema: Type[BaseInputSchema] = Field(
        default=BaseInputSchema, description="The Pydantic model class for agent input."
    )
    output_schema: Type[BaseOutputSchema] = Field(
        default=BaseOutputSchema, description="The Pydantic model class for agent output."
    )
    prompt_builder_config: Optional[Dict[str, Any]] = Field(
        None, description="Optional dictionary of arguments for SystemPromptBuilder initialization."
    )
    memory_manager_config: Optional[MemoryManagerConfig] = Field(
        None, description="Optional configuration object for MemoryManager."
    )
    memory_query_results: int = Field(
        default=3, description="Number of relevant memories to retrieve if memory_manager is enabled."
    )

    class Config:
        arbitrary_types_allowed = True  # Still needed for Type[BaseModel] fields
        # validate_assignment = True # Probably not needed now


class BaseAgent:
    """
    The fundamental agent class in the Karo framework.
    Handles interaction with the LLM provider using specified schemas,
    including multi-turn tool execution following a ReAct-like pattern.
    """

    def __init__(self, config: BaseAgentConfig):
        """
        Initializes the BaseAgent.

        Args:
            config: An instance of BaseAgentConfig containing the agent's configuration.
        """
        if not isinstance(config, BaseAgentConfig):
            raise TypeError("config must be an instance of BaseAgentConfig")

        self.config = config  # Store the raw config object

        # --- Instantiate Provider ---
        provider_config = config.provider_config
        # Import provider classes locally to avoid potential circular dependencies
        if provider_config.type == "openai":
            from karo.providers.openai_provider import OpenAIProvider

            self.provider = OpenAIProvider(config=provider_config)
        elif provider_config.type == "anthropic":
            from karo.providers.anthropic_provider import AnthropicProvider

            self.provider = AnthropicProvider(config=provider_config)
        elif provider_config.type == "ollama":
            from karo.providers.ollama_provider import OllamaProvider

            self.provider = OllamaProvider(config=provider_config)
        elif provider_config.type == "ollama":
            from karo.providers.ollama_provider import OllamaProvider

            self.provider = OllamaProvider(config=provider_config)
        # Add elif for other provider config types...
        else:
            # This should ideally be caught by Pydantic validation based on Union/discriminator
            raise TypeError(f"Unsupported provider_config type: {type(provider_config)}")
        logger.info(f"BaseAgent: Provider '{self.provider.__class__.__name__}' instantiated.")

        # --- Instantiate Memory Manager (Optional) ---
        self.memory_manager: Optional[MemoryManager] = None  # Type hint instance variable
        if config.memory_manager_config:
            # MemoryManager now handles internal service instantiation based on its config
            from karo.memory.memory_manager import MemoryManager  # Import locally

            try:
                self.memory_manager = MemoryManager(config=config.memory_manager_config)
                logger.info("BaseAgent: MemoryManager instantiated.")
            except Exception as e:
                logger.error(f"Failed to instantiate MemoryManager from config: {e}", exc_info=True)
                # Decide if this should be fatal or just log a warning
                # For now, log warning and continue without memory manager
                logger.warning("Continuing without MemoryManager due to instantiation error.")
                self.memory_manager = None
        else:
            logger.info("BaseAgent: No MemoryManager configured.")

        # --- Conversation History Removed ---
        # History is now passed externally via the run() method

        # --- Instantiate Prompt Builder ---
        if config.prompt_builder_config:
            # Pass the config dict as kwargs to the builder's init
            try:
                self.prompt_builder = SystemPromptBuilder(**config.prompt_builder_config)
                logger.info("BaseAgent: SystemPromptBuilder instantiated from config.")
            except Exception as e:
                logger.error(f"Failed to instantiate SystemPromptBuilder from config: {e}", exc_info=True)
                logger.warning("Falling back to default SystemPromptBuilder.")
                self.prompt_builder = SystemPromptBuilder(role_description="You are a helpful assistant.")
        else:
            # Create a default builder if no config provided
            self.prompt_builder = SystemPromptBuilder(role_description="You are a helpful assistant.")
            logger.info("BaseAgent: Default SystemPromptBuilder instantiated.")

    # Removed reset_history method

    def run(
        self,
        input_data: BaseInputSchema,
        history: Optional[List[Dict[str, str]]] = None,
        state: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> BaseOutputSchema | AgentErrorSchema:
        """
        Runs the agent with the given input data, conversation history, and state.

        Args:
            input_data: An instance of the agent's input schema.
            history: Optional list of previous conversation turns (dicts with 'role' and 'content').
            state: Optional dictionary representing the current session state.
            **kwargs: Additional keyword arguments for the LLM provider (e.g., temperature).

        Returns:
            An instance of the agent's output schema or an AgentErrorSchema.
            (Note: The agent currently does not modify or return the state dict, but could be extended to do so).
        """
        if not isinstance(input_data, self.config.input_schema):
            return AgentErrorSchema(
                error_type="InputValidationError",
                error_message=f"Input data does not conform to the expected schema: {self.config.input_schema.__name__}",
                details=str(input_data),
            )

        try:
            # --- State Interaction (Placeholder) ---
            # Agent can access the passed state dictionary here if needed
            if state:
                logger.debug(f"Agent received state: {state}")
                # Example: Modify state based on input or agent logic
                # state["last_input_type"] = input_data.__class__.__name__

            # --- History is now passed externally ---
            # No need to add user input to internal history here

            # 0. Retrieve relevant long-term memories
            # Use chat_message if available, otherwise maybe a generic query or skip?
            query_text = (
                input_data.chat_message if hasattr(input_data, "chat_message") else "current context"
            )
            retrieved_memories = self._retrieve_memories(query_text)

            # 1. Format the prompt (using externally provided history)
            current_prompt = self._create_prompt_with_history(
                external_history=history,  # Pass the history argument
                retrieved_memories=retrieved_memories,
            )
            logger.debug(f"Sending prompt to LLM (length {len(current_prompt)}): {current_prompt}")

            # 2. Call LLM provider
            response = self.provider.generate_response(
                prompt=current_prompt,
                output_schema=self.config.output_schema,
                # Removed tools and tool_choice parameters
                **kwargs,
            )

            # 3. Validate and return response
            if isinstance(response, self.config.output_schema):
                logger.debug("Received validated response from provider.")
                # --- History is now passed externally ---
                # No need to add assistant response to internal history here
                return response
            else:
                # Attempt to handle potential raw response if validation didn't happen in provider
                # (This might depend on provider implementation)
                logger.warning(f"Provider returned unexpected type: {type(response)}. Attempting manual validation.")
                try:
                    # Basic assumption: if not validated, it might be raw content string
                    # More robust handling might be needed depending on provider behavior
                    if hasattr(response, "choices") and response.choices and response.choices[0].message:
                        content = response.choices[0].message.content
                        if content:
                            validated_response = self.config.output_schema(
                                response_message=content
                            )  # Assumes BaseOutputSchema structure
                            logger.info("Manually validated raw response content.")
                            # --- History is now passed externally ---
                            # No need to add assistant response to internal history here
                            return validated_response
                    raise ValueError("Response structure not recognized for manual validation.")
                except Exception as val_err:
                    logger.error(f"Failed to validate or interpret provider response: {val_err}")
                    # Don't add failed response to history
                    return AgentErrorSchema(
                        error_type="OutputValidationError",
                        error_message="LLM response could not be validated against the output schema.",
                        details=str(response),  # Log the raw response
                    )

        except ValidationError as e:
            # This catches validation errors if the provider itself raises them during generation
            logger.error(f"Pydantic validation error during agent run: {e}", exc_info=True)
            return AgentErrorSchema(
                error_type="OutputValidationError",
                error_message="LLM output failed validation against the output schema.",
                details=str(e),
            )
        except Exception as e:
            logger.error(f"Unexpected error during agent execution: {e}", exc_info=True)
            return AgentErrorSchema(
                error_type="RuntimeError",
                error_message="An unexpected error occurred during agent execution.",
                details=str(e),
            )

    def _retrieve_memories(self, query_text: str) -> List[MemoryQueryResult]:
        """Helper to retrieve memories, handling potential errors."""
        if not self.memory_manager:
            return []
        try:
            return self.memory_manager.retrieve_relevant_memories(
                query_text=query_text, n_results=self.config.memory_query_results
            )
        except Exception as mem_e:
            logger.warning(f"Failed to retrieve memories: {mem_e}", exc_info=True)
            return []

    def _create_prompt_with_history(
        self,
        external_history: Optional[List[Dict[str, str]]] = None,
        retrieved_memories: Optional[List[MemoryQueryResult]] = None,
    ) -> List[Dict[str, str]]:
        """
        Creates the list of messages for the LLM API call, combining system prompt,
        retrieved memories, and externally provided conversation history.
        """
        # 1. Get system prompt content (potentially including long-term memories)
        system_content = self.prompt_builder.build(memories=retrieved_memories)

        # 2. Initialize message list
        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})

        # 3. Add externally provided conversation history
        if external_history:
            messages.extend(external_history)
        else:
            logger.debug("No external history provided to _create_prompt_with_history.")

        return messages

    # Removed _execute_tool_calls method
    # Removed _prepare_llm_tools method