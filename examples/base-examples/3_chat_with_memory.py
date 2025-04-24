import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Load environment variables from .env file
load_dotenv()

# Import Karo components
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema
from karo.memory.services.chromadb_service import ChromaDBService, ChromaDBConfig
from karo.memory.memory_manager import MemoryManager

# Initialize console for rich output
console = Console()

def main():
    console.print(Panel("[bold cyan]Karo Framework - Chat with Memory Example[/bold cyan]", title="Welcome", expand=False))

    # 1. Check for API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY environment variable not set.")
        return

    # 2. Configure and Initialize ChromaDB Service & Memory Manager
    try:
        # Using default local ChromaDB path './.karo_chroma_db'
        chroma_config = ChromaDBConfig()
        chroma_service = ChromaDBService(config=chroma_config)
        memory_manager = MemoryManager(chroma_service=chroma_service)
        console.print("[green]✓ ChromaDB Service & Memory Manager Initialized[/green]")
        # Optional: Clear previous memories for a clean run
        # console.print("[yellow]Clearing previous memories...[/yellow]")
        # chroma_service.clear_collection()
    except Exception as e:
        console.print(f"[bold red]Error initializing Memory System:[/bold red] {e}")
        return

    # 3. Configure the OpenAI Provider
    provider_config = OpenAIProviderConfig(model="gpt-4o-mini") # Or another model
    try:
        provider = OpenAIProvider(config=provider_config)
        console.print(f"[green]✓ OpenAI Provider Initialized (Model: {provider.get_model_name()})[/green]")
    except Exception as e:
        console.print(f"[bold red]Error initializing OpenAI Provider:[/bold red] {e}")
        return

    # 4. Configure the Base Agent WITH Memory Manager
    # We can customize the system prompt to mention memory usage
    system_prompt = (
        "You are a helpful assistant with memory. "
        "You can recall relevant information from past interactions provided below under 'Relevant previous information'. "
        "Use this information to provide more contextually relevant responses."
    )
    agent_config = BaseAgentConfig(
        provider=provider,
        memory_manager=memory_manager,
        system_prompt=system_prompt,
        memory_query_results=3 # Retrieve top 3 relevant memories
    )
    agent = BaseAgent(config=agent_config)
    console.print("[green]✓ Base Agent Initialized with Memory[/green]")

    # 5. Interaction Loop
    console.print("\nEnter your message below (type 'quit' to exit):")
    conversation_history = [] # Simple list to hold conversation turns for memory formation
    while True:
        try:
            user_input_text = console.input("[bold blue]You:[/bold blue] ")
            if user_input_text.lower() == 'quit':
                break
            if not user_input_text:
                continue

            # Prepare input data
            input_data = agent.config.input_schema(chat_message=user_input_text)

            # Run the agent (will retrieve memories before calling LLM)
            console.print("[yellow]Agent retrieving memories & thinking...[/yellow]")
            result = agent.run(input_data) # Can add kwargs like temperature=0.7 here

            # Process the result
            agent_response_text = None
            if isinstance(result, agent.config.output_schema):
                agent_response_text = result.response_message
                console.print(f"[bold green]Agent:[/bold green] {agent_response_text}")
            elif isinstance(result, AgentErrorSchema):
                console.print(f"[bold red]Agent Error:[/bold red] {result.error_type} - {result.error_message}")
                if result.details:
                    console.print(f"   Details: {result.details}")
            else:
                console.print(f"[bold red]Unexpected result type:[/bold red] {type(result)}")

            # --- Memory Formation Step ---
            # Store a summary of the turn in memory *after* the interaction
            if agent_response_text and agent.memory_manager:
                turn_summary = f"User asked: '{user_input_text}' | Agent responded: '{agent_response_text}'"
                # Add conversation turn to history (optional, could be used for more complex memory formation)
                conversation_history.append({"role": "user", "content": user_input_text})
                conversation_history.append({"role": "assistant", "content": agent_response_text})

                console.print("[yellow]Storing interaction summary in memory...[/yellow]")
                memory_id = agent.memory_manager.add_memory(
                    text=turn_summary,
                    metadata={"source": "conversation_turn"}
                )
                if memory_id:
                    console.print(f"[dim]Stored memory with ID: {memory_id}[/dim]")
                else:
                    console.print("[bold yellow]Warning:[/bold yellow] Failed to store memory for this turn.")
            # --- End Memory Formation ---


        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred in the loop:[/bold red] {e}")

    console.print("\n[bold cyan]Exiting chatbot. Goodbye![/bold cyan]")

if __name__ == "__main__":
    # Ensure python-dotenv and rich are installed
    main()