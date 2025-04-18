import os
import instructor
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
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
from karo.tools.calculator_tool import CalculatorTool
from karo.memory.tools.memory_store_tool import MemoryStoreTool
from karo.memory.tools.memory_query_tool import MemoryQueryTool

# Initialize console for rich output
console = Console()

def main():
    console.print(Panel("[bold cyan]Karo Framework - Agent with Tools Example[/bold cyan]", title="Welcome", expand=False))
    console.print("[yellow]Note:[/yellow] This example demonstrates configuring an agent with tools. Actual tool execution requires further implementation in BaseAgent and providers.")

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
        available_tools = [calculator, memory_store, memory_query]
        console.print(f"[green]✓ Tools Initialized: {', '.join([t.get_name() for t in available_tools])}[/green]")
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
    system_prompt = (
        "You are a helpful assistant equipped with several tools: a calculator, a memory storage tool, and a memory query tool. "
        "Use the calculator for math problems. Use the memory tools to store or retrieve information when asked or when relevant. "
        "You also have access to relevant memories from past interactions provided below."
    )
    agent_config = BaseAgentConfig(
        provider=provider,
        memory_manager=memory_manager,
        tools=available_tools, # Pass the list of tool instances
        system_prompt=system_prompt,
        memory_query_results=3
    )
    agent = BaseAgent(config=agent_config)
    console.print("[green]✓ Base Agent Initialized with Memory and Tools[/green]")
    console.print(f"  Prepared LLM tools: {agent.llm_tools}") # Show the formatted tools

    # 6. Interaction Loop
    console.print("\nEnter your message below (e.g., 'What is 12 * 5?', 'Remember my favorite color is blue', 'What is my favorite color?'):")
    while True:
        try:
            user_input_text = console.input("[bold blue]You:[/bold blue] ")
            if user_input_text.lower() == 'quit':
                break
            if not user_input_text:
                continue

            input_data = agent.config.input_schema(chat_message=user_input_text)

            console.print("[yellow]Agent thinking (may attempt tool use)...[/yellow]")
            # IMPORTANT: Current BaseAgent.run does NOT execute tools yet.
            # It passes the tool definitions, but expects a direct BaseOutputSchema response.
            # The LLM might respond asking *if* it should use a tool, or might try to output
            # a tool call structure which our current agent/provider won't process.
            result = agent.run(input_data)

            if isinstance(result, agent.config.output_schema):
                console.print(f"[bold green]Agent:[/bold green] {result.response_message}")
                # --- Memory Store (Example - store user input/output pair) ---
                if agent.memory_manager:
                     turn_summary = f"User: '{user_input_text}' | Agent: '{result.response_message}'"
                     agent.memory_manager.add_memory(text=turn_summary, metadata={"source": "tool_agent_turn"})
                     console.print("[dim]Stored turn summary in memory.[/dim]")
                # --- End Memory Store ---
            elif isinstance(result, AgentErrorSchema):
                console.print(f"[bold red]Agent Error:[/bold red] {result.error_type} - {result.error_message}")
            else:
                console.print(f"[bold red]Unexpected result type:[/bold red] {type(result)}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred in the loop:[/bold red] {e}")

    console.print("\n[bold cyan]Exiting agent example. Goodbye![/bold cyan]")

if __name__ == "__main__":
    main()