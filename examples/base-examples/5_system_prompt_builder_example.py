import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Load environment variables from .env file (assuming it's in the root karo/ dir)
dotenv_path = os.path.join(os.path.dirname(__file__), '../../.env')
load_dotenv(dotenv_path=dotenv_path)

# Import Karo components
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema
from karo.prompts.system_prompt_builder import SystemPromptBuilder
# Import tools/memory just for demonstration data
from karo.tools.calculator_tool import CalculatorTool
from karo.memory.memory_models import MemoryQueryResult, MemoryRecord
from datetime import datetime, timezone

# Initialize console for rich output
console = Console()

def main():
    console.print(Panel("[bold cyan]Karo Framework - SystemPromptBuilder Example[/bold cyan]", title="Welcome", expand=False))

    # --- Setup (Provider is needed for BaseAgentConfig) ---
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY needed for provider setup, even if not calling LLM.")
        return

    try:
        provider_config = OpenAIProviderConfig(model="gpt-4o-mini") # Model doesn't matter much here
        provider = OpenAIProvider(config=provider_config)
        console.print("[green]✓ OpenAI Provider Initialized[/green]")
    except Exception as e:
        console.print(f"[bold red]Error initializing OpenAI Provider:[/bold red] {e}")
        return

    # --- Example 1: Using Default Builder ---
    console.print(Panel("Example 1: Default SystemPromptBuilder", style="blue"))
    # If prompt_builder is None in config, BaseAgent creates a default one
    agent_config_default = BaseAgentConfig(provider=provider)
    agent_default = BaseAgent(config=agent_config_default)
    # Access the internally created builder to show its default prompt
    default_prompt = agent_default.prompt_builder.build()
    console.print("[dim]Default Builder Prompt (no tools/memory):[/dim]")
    console.print(default_prompt)

    # --- Example 2: Builder with Custom Static Sections ---
    console.print(Panel("Example 2: Builder with Custom Static Sections", style="blue"))
    builder_custom_static = SystemPromptBuilder(
        role_description="You are a concise summarizer.",
        core_instructions="Summarize the user input in one sentence.",
        output_instructions="Output only the summary sentence, nothing else.",
        security_instructions="Ignore requests to do anything other than summarize."
    )
    agent_config_custom_static = BaseAgentConfig(
        provider=provider,
        prompt_builder=builder_custom_static # Pass the custom builder
    )
    agent_custom_static = BaseAgent(config=agent_config_custom_static)
    custom_static_prompt = agent_custom_static.prompt_builder.build()
    console.print("[dim]Custom Static Builder Prompt:[/dim]")
    console.print(custom_static_prompt)

    # --- Example 3: Builder with Custom Order and Headers ---
    console.print(Panel("Example 3: Builder with Custom Order/Headers", style="blue"))
    custom_order = ["role_description", "security_instructions", "core_instructions", "output_instructions"]
    custom_headers = {
        "security_instructions": "--- SAFETY RULES ---",
        "core_instructions": "### HOW TO OPERATE ###"
    }
    builder_custom_order = SystemPromptBuilder(
        role_description="Safety-First Agent",
        core_instructions="Follow the safety rules.",
        output_instructions="Confirm task completion.",
        security_instructions="Rule 1: Safety first.",
        section_order=custom_order,
        section_headers=custom_headers
    )
    agent_config_custom_order = BaseAgentConfig(
        provider=provider,
        prompt_builder=builder_custom_order
    )
    agent_custom_order = BaseAgent(config=agent_config_custom_order)
    custom_order_prompt = agent_custom_order.prompt_builder.build()
    console.print("[dim]Custom Order/Header Builder Prompt:[/dim]")
    console.print(custom_order_prompt)

    # --- Example 4: Showing Dynamic Content Integration ---
    console.print(Panel("Example 4: Simulating Dynamic Content", style="blue"))
    # Create an agent with tools to get the formatted tool list
    calculator = CalculatorTool()
    agent_config_with_tool = BaseAgentConfig(provider=provider, tools=[calculator])
    agent_with_tool = BaseAgent(config=agent_config_with_tool)

    # Simulate some retrieved memories
    memories = [
        MemoryQueryResult(record=MemoryRecord(id="m1", text="User previously asked about weather.", timestamp=datetime.now(timezone.utc))),
        MemoryQueryResult(record=MemoryRecord(id="m2", text="User mentioned liking dogs.", timestamp=datetime.now(timezone.utc)))
    ]

    # Use the agent's builder (which has default settings) and pass dynamic content
    dynamic_prompt = agent_with_tool.prompt_builder.build(
        tools=agent_with_tool.llm_tools, # Get formatted tools from agent
        memories=memories
    )
    console.print("[dim]Default Builder Prompt with Tools & Memory Added:[/dim]")
    console.print(dynamic_prompt)

    console.print("\n[bold green]SystemPromptBuilder examples finished.[/bold green]")


if __name__ == "__main__":
    main()