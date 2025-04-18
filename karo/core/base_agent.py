from pydantic import BaseModel, Field, ValidationError
from typing import Type, Optional, List, Dict, Any
import json # For potential tool argument parsing later

# Helper function to safely parse JSON arguments
def _parse_tool_arguments(tool_name: str, arguments_json: str) -> Dict[str, Any]:
    try:
        return json.loads(arguments_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON arguments received for tool '{tool_name}': {arguments_json}") from e


# Import base schemas
from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema
# Import provider base, memory components, and tool base
from karo.providers.base_provider import BaseProvider
from karo.memory.memory_manager import MemoryManager
from karo.memory.memory_models import MemoryQueryResult
from karo.tools.base_tool import BaseTool

class BaseAgentConfig(BaseModel):
    """
    Configuration for the BaseAgent.
    """
    provider: BaseProvider = Field(..., description="An instance of a class derived from BaseProvider (e.g., OpenAIProvider).")
    input_schema: Type[BaseInputSchema] = Field(default=BaseInputSchema, description="The Pydantic model for agent input.")
    output_schema: Type[BaseOutputSchema] = Field(default=BaseOutputSchema, description="The Pydantic model for agent output.")
    system_prompt: Optional[str] = Field(default="You are a helpful assistant.", description="The base system prompt for the agent.")
    memory_manager: Optional[MemoryManager] = Field(None, description="Optional instance of MemoryManager for persistent memory.")
    memory_query_results: int = Field(default=3, description="Number of relevant memories to retrieve if memory_manager is enabled.")
    tools: Optional[List[BaseTool]] = Field(None, description="Optional list of tools available to the agent.")
    # Add other config fields as needed, e.g., context providers, tool_choice strategy

    class Config:
        # Allow custom classes like BaseProvider instances without deep validation
        arbitrary_types_allowed = True

class BaseAgent:
    """
    The fundamental agent class in the Karo framework.
    Handles interaction with the LLM provider using specified schemas.
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
        self.provider = config.provider # Store the provider instance
        self.memory_manager = config.memory_manager # Store the memory manager instance

        # Process tools
        self.tools = config.tools or []
        self.tool_map: Dict[str, BaseTool] = {tool.get_name(): tool for tool in self.tools}
        self.llm_tools = self._prepare_llm_tools() # Prepare tools in LLM format once

    def run(self, input_data: BaseInputSchema, **kwargs) -> BaseOutputSchema | AgentErrorSchema:
        """
        Runs the agent with the given input data.

        Args:
            input_data: An instance of the agent's input schema containing the input data.
            **kwargs: Additional keyword arguments to pass to the provider's generate_response method
                      (e.g., temperature, max_tokens).

        Returns:
            An instance of the agent's output schema containing the result,
            or an AgentErrorSchema if an error occurs.
        """
        if not isinstance(input_data, self.config.input_schema):
            return AgentErrorSchema(
                error_type="InputValidationError",
                error_message=f"Input data does not conform to the expected schema: {self.config.input_schema.__name__}",
                details=str(input_data)
            )

        try:
            # 0. Retrieve relevant memories (if manager exists)
            retrieved_memories: List[MemoryQueryResult] = []
            if self.memory_manager:
                try:
                    retrieved_memories = self.memory_manager.retrieve_relevant_memories(
                        query_text=input_data.chat_message,
                        n_results=self.config.memory_query_results
                    )
                except Exception as mem_e:
                    # Log memory retrieval error but continue without memories
                    print(f"Warning: Failed to retrieve memories: {mem_e}")


            # 1. Format the prompt, potentially including memories
            prompt = self._create_prompt(input_data.chat_message, retrieved_memories)

            # 2. Call the LLM via the configured provider, passing tools if available
            # Note: The provider's generate_response needs to be updated to handle 'tools' and 'tool_choice'
            # Note: The output_schema might need to be more flexible if tool calls are expected directly
            #       (e.g., using Union or allowing the raw response). This needs refinement.
            response = self.provider.generate_response(
                prompt=prompt,
                output_schema=self.config.output_schema, # For now, assume direct response or provider handles tool calls internally
                tools=self.llm_tools,
                tool_choice="auto" if self.llm_tools else None, # Basic auto tool choice
                **kwargs # Pass through other LLM parameters
            )

            # --- Tool Execution Logic ---
            # Check if the response object has tool_calls (specific to OpenAI client response structure)
            # We assume the provider returns the raw response object when tools might be called.
            # Note: This structure might need adjustment for different provider libraries.
            if hasattr(response, 'choices') and response.choices and response.choices[0].message.tool_calls:
                tool_calls = response.choices[0].message.tool_calls
                assistant_message = response.choices[0].message # Keep the assistant message that included the tool calls

                # Append the assistant's message to the prompt history
                prompt.append(assistant_message.model_dump(exclude_unset=True)) # Use model_dump for OpenAI v1+

                # Execute tools and collect results
                tool_outputs = []
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_id = tool_call.id
                    tool_to_call = self.tool_map.get(tool_name)

                    if not tool_to_call:
                        print(f"Error: LLM requested unknown tool '{tool_name}'")
                        tool_outputs.append({
                            "tool_call_id": tool_id,
                            "role": "tool",
                            "name": tool_name,
                            "content": json.dumps({"success": False, "error_message": f"Tool '{tool_name}' not found."})
                        })
                        continue # Skip to next tool call

                    try:
                        # Parse arguments string into a dictionary
                        arguments_dict = _parse_tool_arguments(tool_name, tool_call.function.arguments)

                        # Validate arguments using the tool's input schema
                        tool_input_data = tool_to_call.get_input_schema()(**arguments_dict)

                        # Run the tool
                        tool_output = tool_to_call.run(tool_input_data)

                        # Append successful tool output
                        tool_outputs.append({
                            "tool_call_id": tool_id,
                            "role": "tool",
                            "name": tool_name,
                            # Serialize the output schema (which includes success/error)
                            "content": tool_output.model_dump_json()
                        })

                    except (ValidationError, ValueError, json.JSONDecodeError) as arg_err:
                         print(f"Error parsing arguments for tool '{tool_name}': {arg_err}")
                         tool_outputs.append({
                            "tool_call_id": tool_id,
                            "role": "tool",
                            "name": tool_name,
                            "content": json.dumps({"success": False, "error_message": f"Invalid arguments provided: {arg_err}"})
                         })
                    except Exception as exec_err:
                         print(f"Error executing tool '{tool_name}': {exec_err}")
                         tool_outputs.append({
                            "tool_call_id": tool_id,
                            "role": "tool",
                            "name": tool_name,
                            "content": json.dumps({"success": False, "error_message": f"Tool execution failed: {exec_err}"})
                         })

                # Append all tool outputs to the prompt history
                prompt.extend(tool_outputs)

                # Make the second call to the LLM with tool results, asking for final response
                final_response = self.provider.generate_response(
                    prompt=prompt,
                    output_schema=self.config.output_schema,
                    tool_choice="none", # Ensure LLM doesn't try to call tools again
                    **kwargs # Pass original kwargs like temperature
                )
                output_data = final_response

            elif isinstance(response, self.config.output_schema):
                 # If the first response was already the validated output schema (no tool call)
                 output_data = response
            else:
                 # Handle unexpected response type from provider
                 raise TypeError(f"Unexpected response type from provider: {type(response)}. Expected {self.config.output_schema} or object with tool_calls.")
            # --- End Tool Execution Logic ---

            return output_data

        except ValidationError as e:
            # Handle Pydantic validation errors during output parsing
            return AgentErrorSchema(
                error_type="OutputValidationError",
                error_message="LLM output failed validation against the output schema.",
                details=str(e)
            )
        except Exception as e:
            # Handle other potential errors during the LLM call or processing
            return AgentErrorSchema(
                error_type="RuntimeError",
                error_message="An unexpected error occurred during agent execution.",
                details=str(e)
            )

    def _create_prompt(
        self,
        input_message: str,
        retrieved_memories: Optional[List[MemoryQueryResult]] = None
    ) -> List[Dict[str, str]]:
        """
        Creates the list of messages for the LLM API call, incorporating system prompt,
        retrieved memories (if any), and the current user input.

        Args:
            input_message: The user's input message string.
            retrieved_memories: Optional list of relevant memories retrieved.

        Returns:
            A list of dictionaries formatted for the chat completions API.
        """
        messages = []
        system_content = self.config.system_prompt or "You are a helpful assistant."

        # Format memories into the system prompt or a separate context message
        # Simple approach: prepend to system prompt
        if retrieved_memories:
            memory_context = "\n\nRelevant previous information:\n"
            for i, mem in enumerate(retrieved_memories):
                # Include timestamp or other metadata if useful
                timestamp_str = mem.record.timestamp.strftime('%Y-%m-%d %H:%M')
                memory_context += f"- ({timestamp_str}): {mem.record.text}\n"
            system_content += memory_context

        if system_content:
            messages.append({"role": "system", "content": system_content})

        # TODO: Add conversation history management here later if needed

        messages.append({"role": "user", "content": input_message})
        return messages

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
                print(f"Warning: Failed to prepare tool '{tool.get_name()}' for LLM: {e}")
                # Optionally skip the tool or raise a more specific error

        return llm_tools if llm_tools else None