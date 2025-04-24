import os
from dotenv import load_dotenv
from pydantic import Field
from rich.console import Console
from rich.panel import Panel
import logging
from typing import Union, Optional, Dict, Any # Added for Union type

# Configure basic logging
# logging.basicConfig(level=logging.INFO) # Let's use DEBUG for more insight
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Import Karo components
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema
from karo.memory.services.chromadb_service import ChromaDBService, ChromaDBConfig
from karo.memory.memory_manager import MemoryManager
# Import Tools
from karo.tools.calculator_tool import CalculatorTool, CalculatorInput, CalculatorOutput
from karo.memory.tools.memory_store_tool import MemoryStoreTool, MemoryStoreInput, MemoryStoreOutput
from karo.memory.tools.memory_query_tool import MemoryQueryTool, MemoryQueryInput, MemoryQueryOutput
# Import BaseTool for type hinting if needed later
from karo.tools.base_tool import BaseTool

# Define the Orchestration Output Schema
class OrchestrationOutputSchema(BaseOutputSchema):
    """
    Output schema for the orchestrator agent. Specifies which tool to use and its parameters,
    or provides a direct response if no tool is needed.
    """
    tool_name: Optional[str] = Field(None, description="The name of the tool to execute (e.g., 'calculator', 'memory_store', 'memory_query'). None if no tool is needed.")
    tool_parameters: Optional[Union[CalculatorInput, MemoryStoreInput, MemoryQueryInput]] = Field(None, description="The validated input parameters for the selected tool.")
    direct_response: Optional[str] = Field(None, description="A direct response from the agent if no tool execution is required.")

    # Add a validator to ensure either tool info or direct_response is provided
    @classmethod
    def model_validator(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        tool_name, params, response = values.get('tool_name'), values.get('tool_parameters'), values.get('direct_response')
        if tool_name and params is not None and response is None:
            # Valid tool call
            return values
        elif tool_name is None and params is None and response is not None:
            # Valid direct response
            return values
        elif tool_name is None and params is None and response is None:
             # Allow empty response if needed, maybe agent decides nothing to do.
             # Or raise error if one must be present. Let's allow empty for now.
             # raise ValueError("Either tool information (name and parameters) or a direct response must be provided.")
             return values # Allow empty/no-op response
        else:
            # Invalid combination
            raise ValueError("Invalid combination: Provide tool_name and tool_parameters OR direct_response, not both or partial tool info.")


# Initialize console for rich output
console = Console()

def main():
    console.print(Panel("[bold cyan]Karo Framework - Refactored Agent with External Tools Example[/bold cyan]", title="Welcome", expand=False))
    console.print("[yellow]Note:[/yellow] This example demonstrates external tool orchestration based on agent output.")

    # 1. Check for API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY environment variable not set.")
        return

    # 2. Initialize Memory System (needed for memory tools)
    try:
        chroma_config = ChromaDBConfig()
        chroma_service = ChromaDBService(config=chroma_config)
        memory_manager = MemoryManager(chroma_service=chroma_service)
        console.print("[green]✓ Memory System Initialized[/green]")
    except Exception as e:
        console.print(f"[bold red]Error initializing Memory System:[/bold red] {e}")
        return

    # 3. Initialize Tools
    try:
        calculator = CalculatorTool()
        # Note: Memory tools require the chroma_service instance
        memory_store = MemoryStoreTool(chroma_service=chroma_service)
        memory_query = MemoryQueryTool(chroma_service=chroma_service)
        # Store tools in a dictionary for easy lookup by name
        available_tools: Dict[str, BaseTool] = {
            calculator.get_name(): calculator,
            memory_store.get_name(): memory_store,
            memory_query.get_name(): memory_query
        }
        console.print(f"[green]✓ Tools Initialized: {', '.join(available_tools.keys())}[/green]")
    except Exception as e:
        console.print(f"[bold red]Error initializing Tools:[/bold red] {e}")
        return

    # 4. Configure the OpenAI Provider
    # Use a model known to support tool calling well, like gpt-4o-mini or gpt-4-turbo
    provider_config = OpenAIProviderConfig(model="gpt-4o-mini")
    try:
        provider = OpenAIProvider(config=provider_config)
        console.print(f"[green]✓ OpenAI Provider Initialized (Model: {provider.get_model_name()})[/green]")
    except Exception as e:
        console.print(f"[bold red]Error initializing OpenAI Provider:[/bold red] {e}")
        return

    # 5. Configure the Base Agent WITH Tools and Memory
    # 5. Configure the Base Agent (Orchestrator)
    # Update system prompt to reflect the new output schema requirement
    system_prompt = (
        "You are an orchestrator assistant. Your task is to analyze the user query and determine if a tool is needed. "
        "Available tools: 'calculator', 'memory_store', 'memory_query'.\n"
        "Calculator: Use for math problems. Requires 'operand1', 'operand2', 'operator'.\n"
        "Memory Store: Use to remember specific facts provided by the user. Requires 'memory' (a dict with 'content').\n"
        "Memory Query: Use to retrieve previously stored information. Requires 'query'.\n"
        "If a tool is needed, respond ONLY with the 'tool_name' and 'tool_parameters' fields populated in the required JSON format. "
        "The parameters must match the specific input schema for the chosen tool.\n"
        "If no tool is needed, or you can answer directly using the provided context (like retrieved memories), respond ONLY with the 'direct_response' field populated.\n"
        "You have access to relevant memories from past interactions provided below."
        # TODO: Include schema definitions in prompt? Instructor might handle this via response_model.
    )
    agent_config = BaseAgentConfig(
        provider=provider,
        memory_manager=memory_manager,
        # Removed 'tools' parameter
        output_schema=OrchestrationOutputSchema, # Set the new output schema
        prompt_builder=None, # Let BaseAgent create default, pass system_prompt below? No, prompt_builder handles it.
        # Let's create a builder and pass the prompt
        # prompt_builder=SystemPromptBuilder(role_description=system_prompt), # This might not be right way
        memory_query_results=3 # Keep memory retrieval
    )
    # Let's manually set the system prompt in the builder after agent init for clarity
    agent = BaseAgent(config=agent_config)
    agent.prompt_builder.role_description = system_prompt # Override default role description
    console.print("[green]✓ Base Agent (Orchestrator) Initialized[/green]")
    # Removed print of agent.llm_tools as it no longer exists

    # 6. Interaction Loop with External Tool Orchestration
    console.print("\nEnter your message below (e.g., 'What is 12 * 5?', 'Remember my favorite color is blue', 'What is my favorite color?'):")
    while True:
        try:
            user_input_text = console.input("[bold blue]You:[/bold blue] ")
            if user_input_text.lower() == 'quit':
                break
            if not user_input_text:
                continue

            # Prepare agent input
            input_data = agent.config.input_schema(chat_message=user_input_text)

            console.print("[yellow]Agent thinking (will output tool instructions or direct response)...[/yellow]")
            agent_output = agent.run(input_data) # Agent now returns OrchestrationOutputSchema or AgentErrorSchema

            # --- External Tool Execution Logic ---
            if isinstance(agent_output, OrchestrationOutputSchema):
                tool_name = agent_output.tool_name
                tool_params = agent_output.tool_parameters
                direct_response = agent_output.direct_response

                if tool_name and tool_params is not None:
                    console.print(f"[magenta]Agent requested tool:[/magenta] {tool_name}")
                    console.print(f"[magenta]Parameters:[/magenta] {tool_params}")

                    # Find and execute the tool
                    # Handle potential prefix like 'functions.' added by instructor/LLM
                    base_tool_name = tool_name.split('.')[-1] # Get the part after the last dot
                    if base_tool_name in available_tools:
                        tool_instance = available_tools[base_tool_name]
                        # Validate parameters match the tool's input schema
                        # (Instructor should have done this based on the Union type hint, but double check)
                        if isinstance(tool_params, tool_instance.get_input_schema()):
                            try:
                                console.print(f"[yellow]Executing {base_tool_name}...[/yellow]")
                                tool_result = tool_instance.run(tool_params)
                                console.print(f"[bold green]Tool Result ({base_tool_name}):[/bold green]")
                                console.print(tool_result)

                                # --- Optional: Store interaction summary ---
                                if agent.memory_manager:
                                    turn_summary = f"User: '{user_input_text}' | Agent requested {base_tool_name} | Tool Result: {tool_result}"
                                    agent.memory_manager.add_memory(text=turn_summary, metadata={"source": "orchestration_turn"})
                                    console.print("[dim]Stored orchestration summary in memory.[/dim]")
                                # --- End Memory Store ---

                            except Exception as tool_err:
                                console.print(f"[bold red]Error executing tool {base_tool_name}:[/bold red] {tool_err}")
                        else:
                            console.print(f"[bold red]Parameter type mismatch:[/bold red] Agent provided parameters of type {type(tool_params).__name__}, but tool {base_tool_name} expected {tool_instance.get_input_schema().__name__}.")
                    else:
                        console.print(f"[bold red]Unknown tool requested:[/bold red] Agent specified '{tool_name}', base name '{base_tool_name}' not found in available tools.")

                elif direct_response:
                    console.print(f"[bold green]Agent:[/bold green] {direct_response}")
                    # --- Optional: Store interaction summary ---
                    if agent.memory_manager:
                         turn_summary = f"User: '{user_input_text}' | Agent: '{direct_response}'"
                         agent.memory_manager.add_memory(text=turn_summary, metadata={"source": "direct_response_turn"})
                         console.print("[dim]Stored direct response summary in memory.[/dim]")
                    # --- End Memory Store ---
                else:
                    # Agent returned the schema but with no tool and no direct response
                    console.print("[yellow]Agent decided no action or response was needed.[/yellow]")

            elif isinstance(agent_output, AgentErrorSchema):
                console.print(f"[bold red]Agent Error:[/bold red] {agent_output.error_type} - {agent_output.error_message}")
            else:
                # This case should ideally not happen if the provider + instructor work correctly
                console.print(f"[bold red]Unexpected result type from agent:[/bold red] {type(agent_output)}")
            # --- End External Tool Execution Logic ---

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred in the loop:[/bold red] {e}")

    console.print("\n[bold cyan]Exiting agent example. Goodbye![/bold cyan]")

if __name__ == "__main__":
    main()