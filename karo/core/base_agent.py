from pydantic import BaseModel, Field, ValidationError
from typing import Type, Optional, List, Dict, Any
import json # For potential tool argument parsing later
import logging # Add logging

# Helper function to safely parse JSON arguments
def _parse_tool_arguments(tool_name: str, arguments_json: str) -> Dict[str, Any]:
    try:
        return json.loads(arguments_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON arguments received for tool '{tool_name}': {arguments_json}") from e

# Import base schemas
from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema
# Import provider base, memory components, tool base, and prompt builder
from karo.providers.base_provider import BaseProvider
from karo.memory.memory_manager import MemoryManager
from karo.memory.memory_models import MemoryQueryResult
from karo.tools.base_tool import BaseTool
from karo.prompts.system_prompt_builder import SystemPromptBuilder

logger = logging.getLogger(__name__) # Setup logger

class BaseAgentConfig(BaseModel):
    """
    Configuration for the BaseAgent.
    """
    provider: BaseProvider = Field(..., description="An instance of a class derived from BaseProvider (e.g., OpenAIProvider).")
    input_schema: Type[BaseInputSchema] = Field(default=BaseInputSchema, description="The Pydantic model for agent input.")
    output_schema: Type[BaseOutputSchema] = Field(default=BaseOutputSchema, description="The Pydantic model for agent output.")
    prompt_builder: Optional[SystemPromptBuilder] = Field(None, description="Optional SystemPromptBuilder instance. If None, a default one is created.")
    memory_manager: Optional[MemoryManager] = Field(None, description="Optional instance of MemoryManager for persistent memory.")
    memory_query_results: int = Field(default=3, description="Number of relevant memories to retrieve if memory_manager is enabled.")
    tools: Optional[List[BaseTool]] = Field(None, description="Optional list of tools available to the agent.")
    max_tool_iterations: int = Field(default=5, description="Maximum number of tool call iterations before forcing a final response.")

    class Config:
        arbitrary_types_allowed = True

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

        self.config = config
        self.provider = config.provider
        self.memory_manager = config.memory_manager

        # Initialize or store the prompt builder
        if config.prompt_builder:
            self.prompt_builder = config.prompt_builder
        else:
            # Create a default builder if none provided
            self.prompt_builder = SystemPromptBuilder(role_description="You are a helpful assistant.")

        # Process tools
        self.tools = config.tools or []
        self.tool_map: Dict[str, BaseTool] = {tool.get_name(): tool for tool in self.tools}
        self.llm_tools = self._prepare_llm_tools() # Prepare tools in LLM format once

    def run(self, input_data: BaseInputSchema, **kwargs) -> BaseOutputSchema | AgentErrorSchema:
        """
        Runs the agent with the given input data, handling potential tool calls.

        Args:
            input_data: An instance of the agent's input schema.
            **kwargs: Additional keyword arguments for the LLM provider (e.g., temperature).
                      Note: 'tool_choice' might be overridden internally during the ReAct loop.

        Returns:
            An instance of the agent's output schema or an AgentErrorSchema.
        """
        if not isinstance(input_data, self.config.input_schema):
            return AgentErrorSchema(
                error_type="InputValidationError",
                error_message=f"Input data does not conform to the expected schema: {self.config.input_schema.__name__}",
                details=str(input_data)
            )

        try:
            # 0. Retrieve relevant memories
            retrieved_memories = self._retrieve_memories(input_data.chat_message)

            # 1. Format the initial prompt (conversation history)
            current_prompt = self._create_initial_prompt(input_data.chat_message, retrieved_memories)

            # --- ReAct Loop (Tool Execution) ---
            for iteration in range(self.config.max_tool_iterations):
                logger.debug(f"Agent Run - Iteration {iteration + 1}")
                logger.debug(f"Sending prompt to LLM (length {len(current_prompt)}): {current_prompt}")

                # 2. Call LLM (First call in the loop, potentially requesting tools)
                response = self.provider.generate_response(
                    prompt=current_prompt,
                    output_schema=self.config.output_schema,
                    tools=self.llm_tools,
                    tool_choice="auto" if self.llm_tools else None, # Only 'auto' on first real pass
                    **kwargs
                )

                # 3. Check for Tool Calls
                tool_calls = None
                assistant_message_content = None
                raw_message_for_history = None

                if hasattr(response, 'choices') and response.choices:
                     message = response.choices[0].message
                     assistant_message_content = message.content
                     raw_message_for_history = message.model_dump(exclude_unset=True, exclude_none=True) # Get message dict
                     if message.tool_calls:
                         tool_calls = message.tool_calls
                     else:
                          # No tool calls, LLM provided a direct answer
                          logger.debug("LLM provided direct answer. Exiting loop.")
                          if isinstance(response, self.config.output_schema):
                              return response # Already validated
                          elif assistant_message_content:
                               # Attempt validation if provider returned raw but no tool calls
                               try:
                                   validated_response = self.config.output_schema(response_message=assistant_message_content)
                                   logger.warning("Provider returned raw response without tool calls, manual validation attempted.")
                                   return validated_response
                               except Exception as val_err:
                                    logger.error(f"Failed to validate direct response content: {val_err}")
                                    return AgentErrorSchema(error_type="OutputValidationError", error_message="LLM response could not be validated.", details=str(assistant_message_content))
                          else:
                               logger.error(f"Unexpected raw response type without tool calls or content: {type(response)}")
                               return AgentErrorSchema(error_type="ProviderResponseError", error_message="Unexpected response from provider.")

                # If no tool calls were detected, exit the loop (should have been handled above)
                if not tool_calls:
                    logger.warning("Exiting tool loop: No tool calls detected.")
                    if isinstance(response, self.config.output_schema):
                         return response
                    else:
                         return AgentErrorSchema(error_type="LogicError", error_message="Agent loop ended unexpectedly without valid response or tool calls.")

                # --- Tool execution proceeds ---
                logger.debug(f"Detected {len(tool_calls)} tool calls.")
                # Append assistant's turn (requesting the tool) to history
                if raw_message_for_history:
                    current_prompt.append(raw_message_for_history)

                # 4. Execute Tools
                tool_outputs = self._execute_tool_calls(tool_calls)

                # 5. Append tool results to prompt history
                current_prompt.extend(tool_outputs)

                # 6. Make the second call to the LLM with tool results
                logger.debug("Making second LLM call with tool results...")
                # Filter tool_choice from kwargs to ensure "none" takes precedence
                final_call_kwargs = {k: v for k, v in kwargs.items() if k != 'tool_choice'}
                final_response = self.provider.generate_response(
                    prompt=current_prompt, # Use the updated prompt
                    output_schema=self.config.output_schema,
                    tool_choice="none", # Explicitly prevent further tool use
                    **final_call_kwargs
                )

                # The response from this second call IS the final answer for this turn.
                if isinstance(final_response, self.config.output_schema):
                    logger.debug("Received final validated response after tool execution.")
                    return final_response
                else:
                    # This indicates an issue, maybe the LLM tried to call tools again despite tool_choice="none"
                    # or the provider/instructor failed to validate the final response.
                    logger.error(f"Final response after tool execution was not the expected schema: {type(final_response)}")
                    return AgentErrorSchema(error_type="OutputValidationError", error_message="Failed to get valid final response after tool execution.")

            # End of loop (max iterations reached)
            logger.warning(f"Max tool iterations ({self.config.max_tool_iterations}) reached without a final answer.")
            return AgentErrorSchema(error_type="MaxIterationsReached", error_message=f"Agent exceeded maximum tool iterations ({self.config.max_tool_iterations}).")


        except ValidationError as e:
            logger.error(f"Pydantic validation error during agent run: {e}", exc_info=True)
            return AgentErrorSchema(
                error_type="OutputValidationError",
                error_message="LLM output failed validation against the output schema.",
                details=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error during agent execution: {e}", exc_info=True)
            return AgentErrorSchema(
                error_type="RuntimeError",
                error_message="An unexpected error occurred during agent execution.",
                details=str(e)
            )

    def _retrieve_memories(self, query_text: str) -> List[MemoryQueryResult]:
        """Helper to retrieve memories, handling potential errors."""
        if not self.memory_manager:
            return []
        try:
            return self.memory_manager.retrieve_relevant_memories(
                query_text=query_text,
                n_results=self.config.memory_query_results
            )
        except Exception as mem_e:
            logger.warning(f"Failed to retrieve memories: {mem_e}", exc_info=True)
            return []

    def _create_initial_prompt(
        self,
        input_message: str,
        retrieved_memories: Optional[List[MemoryQueryResult]] = None
    ) -> List[Dict[str, str]]:
        """Creates the initial list of messages for the LLM API call."""
        system_content = self.prompt_builder.build(
            tools=self.llm_tools,
            memories=retrieved_memories
        )
        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        # TODO: Add conversation history management here later if needed
        messages.append({"role": "user", "content": input_message})
        return messages

    def _execute_tool_calls(self, tool_calls: List[Any]) -> List[Dict[str, str]]:
         """Executes requested tool calls and returns formatted results."""
         tool_outputs = []
         for tool_call in tool_calls:
             # Structure assumes OpenAI format: tool_call.id, tool_call.function.name, tool_call.function.arguments
             tool_name = tool_call.function.name
             tool_id = tool_call.id
             tool_to_call = self.tool_map.get(tool_name)
             logger.info(f"Attempting to execute tool: {tool_name} (Call ID: {tool_id})")

             if not tool_to_call:
                 logger.error(f"LLM requested unknown tool '{tool_name}'")
                 tool_outputs.append({
                     "tool_call_id": tool_id,
                     "role": "tool",
                     "name": tool_name,
                     "content": json.dumps({"success": False, "error_message": f"Tool '{tool_name}' not found."})
                 })
                 continue

             try:
                 arguments_dict = _parse_tool_arguments(tool_name, tool_call.function.arguments)
                 logger.debug(f"Parsed arguments for {tool_name}: {arguments_dict}")

                 tool_input_data = tool_to_call.get_input_schema()(**arguments_dict)
                 logger.debug(f"Validated input data for {tool_name}: {tool_input_data}")

                 tool_output = tool_to_call.run(tool_input_data)
                 logger.info(f"Tool '{tool_name}' executed successfully.")
                 logger.debug(f"Tool '{tool_name}' output: {tool_output}")

                 tool_outputs.append({
                     "tool_call_id": tool_id,
                     "role": "tool",
                     "name": tool_name,
                     "content": tool_output.model_dump_json() # Serialize the Pydantic output model
                 })

             except (ValidationError, ValueError, json.JSONDecodeError) as arg_err:
                  logger.error(f"Argument error for tool '{tool_name}': {arg_err}", exc_info=True)
                  tool_outputs.append({
                     "tool_call_id": tool_id,
                     "role": "tool",
                     "name": tool_name,
                     "content": json.dumps({"success": False, "error_message": f"Invalid arguments provided: {arg_err}"})
                  })
             except Exception as exec_err:
                  logger.error(f"Execution error for tool '{tool_name}': {exec_err}", exc_info=True)
                  tool_outputs.append({
                     "tool_call_id": tool_id,
                     "role": "tool",
                     "name": tool_name,
                     "content": json.dumps({"success": False, "error_message": f"Tool execution failed: {exec_err}"})
                  })
         return tool_outputs


    def _prepare_llm_tools(self) -> Optional[List[Dict[str, Any]]]:
        """
        Converts the BaseTool instances into the format required by the LLM API (e.g., OpenAI functions).
        """
        if not self.tools:
            return None

        llm_tools = []
        for tool in self.tools:
            try:
                schema = tool.get_input_schema().model_json_schema()
                # Remove 'title' if present, as OpenAI doesn't use it at the top level
                schema.pop('title', None)
                # Ensure 'properties' exists, even if empty, for tools with no args
                if 'properties' not in schema:
                    schema['properties'] = {}

                tool_config = {
                    "type": "function",
                    "function": {
                        "name": tool.get_name(),
                        "description": tool.get_description() or f"Executes the {tool.get_name()} tool.", # Add default description
                        "parameters": schema,
                    },
                }
                llm_tools.append(tool_config)
            except Exception as e:
                logger.warning(f"Failed to prepare tool '{tool.get_name()}' for LLM: {e}", exc_info=True)
                # Optionally skip the tool or raise a more specific error

        return llm_tools if llm_tools else None