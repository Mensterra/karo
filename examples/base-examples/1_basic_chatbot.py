import os
import instructor
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Load environment variables from .env file
load_dotenv()

# Import Karo components
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema

# Initialize console for rich output
console = Console()

def main():
    console.print(Panel("[bold cyan]Karo Framework - Basic Chatbot Example[/bold cyan]", title="Welcome", expand=False))

    # 1. Check for API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY environment variable not set.")
        console.print("Please create a `.env` file in the root directory (`karo/`) and add your key:")
        console.print("OPENAI_API_KEY='your-key-here'")
        return

    # 2. Configure the OpenAI Provider
    # Using gpt-4o-mini as a default, change if needed
    provider_config = OpenAIProviderConfig(model="gpt-4o-mini")
    try:
        provider = OpenAIProvider(config=provider_config)
        console.print(f"[green]✓ OpenAI Provider Initialized (Model: {provider.get_model_name()})[/green]")
    except Exception as e:
        console.print(f"[bold red]Error initializing OpenAI Provider:[/bold red] {e}")
        return

    # 3. Configure the Base Agent
    # We use the default input/output schemas and system prompt here
    agent_config = BaseAgentConfig(provider=provider)
    agent = BaseAgent(config=agent_config)
    console.print("[green]✓ Base Agent Initialized[/green]")

    # 4. Interaction Loop
    console.print("\nEnter your message below (type 'quit' to exit):")
    while True:
        try:
            user_input_text = console.input("[bold blue]You:[/bold blue] ")
            if user_input_text.lower() == 'quit':
                break
            if not user_input_text:
                continue

            # Prepare input data using the agent's input schema
            input_data = agent.config.input_schema(chat_message=user_input_text)

            # Run the agent
            console.print("[yellow]Agent thinking...[/yellow]")
            result = agent.run(input_data) # Can add kwargs like temperature=0.7 here

            # Process the result
            if isinstance(result, agent.config.output_schema):
                console.print(f"[bold green]Agent:[/bold green] {result.response_message}")
            elif isinstance(result, AgentErrorSchema):
                console.print(f"[bold red]Agent Error:[/bold red] {result.error_type} - {result.error_message}")
                if result.details:
                    console.print(f"   Details: {result.details}")
            else:
                # Should not happen if agent.run() behaves correctly
                console.print(f"[bold red]Unexpected result type:[/bold red] {type(result)}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred in the loop:[/bold red] {e}")
            # Optionally break or continue based on error severity

    console.print("\n[bold cyan]Exiting chatbot. Goodbye![/bold cyan]")

if __name__ == "__main__":
    # Add python-dotenv to dependencies if not already present
    # `poetry add python-dotenv` or `pip install python-dotenv`
    # Also add rich: `poetry add rich` or `pip install rich`
    main()