import os
import instructor
from dotenv import load_dotenv
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from typing import Any, Type, List, Dict

# Load environment variables from .env file
load_dotenv()

# Import Karo components
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.providers.base_provider import BaseProvider
from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema

# Initialize console for rich output
console = Console()

# --- Define a Mock Provider for Demonstration ---
class MockProviderConfig(BaseModel):
    model: str = "mock-model"
    mock_response: str = "This is a mock response."

class MockProvider(BaseProvider):
    """A simple mock provider for demonstrating provider swapping."""
    def __init__(self, config: MockProviderConfig):
        self.config = config
        # No real client needed for mock
        self.client = None

    def get_client(self) -> Any:
        return self.client # Returns None

    def get_model_name(self) -> str:
        return self.config.model

    def generate_response(
        self,
        prompt: List[Dict[str, str]],
        output_schema: Type[BaseOutputSchema],
        **kwargs
    ) -> BaseOutputSchema:
        # Simulate generating a response based on the output schema
        # For simplicity, we assume BaseOutputSchema with 'response_message'
        user_message = next((msg['content'] for msg in prompt if msg['role'] == 'user'), "Unknown input")
        response_text = f"{self.config.mock_response} (Input was: '{user_message[:30]}...')"

        # Create an instance of the expected output schema
        # This assumes the output_schema has a 'response_message' field.
        # A more robust mock might inspect the schema fields.
        if hasattr(output_schema, 'model_fields') and 'response_message' in output_schema.model_fields:
             return output_schema(response_message=response_text)
        else:
             # Fallback or raise error if schema doesn't match expectation
             raise TypeError(f"MockProvider cannot fulfill unexpected output schema: {output_schema.__name__}")


def main():
    console.print(Panel("[bold cyan]Karo Framework - Multi-Provider Setup Example[/bold cyan]", title="Welcome", expand=False))

    # --- Provider 1: OpenAI ---
    console.print("\n--- Configuring OpenAI Provider ---")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]Skipping OpenAI:[/bold red] OPENAI_API_KEY not set.")
        openai_provider = None
    else:
        openai_provider_config = OpenAIProviderConfig(model="gpt-4o-mini")
        try:
            openai_provider = OpenAIProvider(config=openai_provider_config)
            console.print(f"[green]✓ OpenAI Provider Initialized (Model: {openai_provider.get_model_name()})[/green]")
        except Exception as e:
            console.print(f"[bold red]Error initializing OpenAI Provider:[/bold red] {e}")
            openai_provider = None

    # --- Provider 2: Mock Provider ---
    console.print("\n--- Configuring Mock Provider ---")
    mock_provider_config = MockProviderConfig()
    mock_provider = MockProvider(config=mock_provider_config)
    console.print(f"[green]✓ Mock Provider Initialized (Model: {mock_provider.get_model_name()})[/green]")


    # --- Agent Configuration ---
    console.print("\n--- Configuring Agents ---")
    openai_agent = None
    if openai_provider:
        openai_agent_config = BaseAgentConfig(provider=openai_provider)
        openai_agent = BaseAgent(config=openai_agent_config)
        console.print("[green]✓ OpenAI Agent Configured[/green]")

    mock_agent_config = BaseAgentConfig(provider=mock_provider)
    mock_agent = BaseAgent(config=mock_agent_config)
    console.print("[green]✓ Mock Agent Configured[/green]")


    # --- Interaction Demonstration ---
    console.print("\n--- Running Interaction ---")
    input_text = "Tell me about the Karo framework."
    input_data = BaseInputSchema(chat_message=input_text)
    console.print(f"[bold blue]Input:[/bold blue] {input_text}")

    # Run with OpenAI Agent (if available)
    if openai_agent:
        console.print("\n[yellow]Running with OpenAI Agent...[/yellow]")
        result_openai = openai_agent.run(input_data)
        if isinstance(result_openai, BaseOutputSchema):
            console.print(f"[bold green]OpenAI Agent:[/bold green] {result_openai.response_message}")
        elif isinstance(result_openai, AgentErrorSchema):
            console.print(f"[bold red]OpenAI Agent Error:[/bold red] {result_openai.error_type}")
    else:
        console.print("\n[yellow]Skipping OpenAI Agent run (provider not initialized).[/yellow]")


    # Run with Mock Agent
    console.print("\n[yellow]Running with Mock Agent...[/yellow]")
    result_mock = mock_agent.run(input_data)
    if isinstance(result_mock, BaseOutputSchema):
        console.print(f"[bold green]Mock Agent:[/bold green] {result_mock.response_message}")
    elif isinstance(result_mock, AgentErrorSchema):
         console.print(f"[bold red]Mock Agent Error:[/bold red] {result_mock.error_type}")


    console.print("\n[bold cyan]Example finished. Notice how the BaseAgent uses whichever provider it was configured with.[/bold cyan]")


if __name__ == "__main__":
    # Ensure python-dotenv and rich are installed
    main()