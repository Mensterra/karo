import argparse
import os
import instructor
from dotenv import load_dotenv
from rich.console import Console
from pydantic import Field
from typing import List
from rich.panel import Panel
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file (assuming it's in the root karo/ dir)
dotenv_path = os.path.join(os.path.dirname(__file__), '../../.env')
load_dotenv(dotenv_path=dotenv_path)

# Import Karo components
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema
# Import the custom tool using relative import
from .excel_reader_tool import ExcelReaderTool, ExcelReaderInput, ExcelReaderOutput

# Initialize console for rich output
console = Console()

# --- Define a specific output schema for the summarization ---
class SummarizationOutput(BaseOutputSchema):
    summary: str = Field(..., description="A concise summary of the provided data.")
    key_takeaways: List[str] = Field(default_factory=list, description="A list of key points or takeaways from the data.")

def run_summarization(file_path: str):
    """Orchestrates reading the Excel file and generating a summary."""
    console.print(Panel(f"[bold cyan]Excel Summarizer Example: Processing '{file_path}'[/bold cyan]", title="Karo", expand=False))

    # 1. Check for API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY environment variable not set.")
        return

    # 2. Initialize Tool
    try:
        excel_reader = ExcelReaderTool()
        console.print("[green]✓ ExcelReaderTool Initialized[/green]")
    except Exception as e:
        console.print(f"[bold red]Error initializing ExcelReaderTool:[/bold red] {e}")
        return

    # 3. Run Tool to Read Excel Data
    console.print(f"[yellow]Reading data from '{file_path}'...[/yellow]")
    tool_input = ExcelReaderInput(file_path=file_path)
    tool_output = excel_reader.run(tool_input)

    if not tool_output.success or not tool_output.data_preview:
        console.print(f"[bold red]Error reading Excel file:[/bold red] {tool_output.error_message}")
        return

    console.print(f"[green]✓ Successfully read sheet '{tool_output.sheet_name_read}' ({tool_output.row_count} rows, {len(tool_output.column_names)} cols)[/green]")
    console.print(Panel(tool_output.data_preview, title="Data Preview", border_style="dim"))

    # 4. Initialize LLM Provider
    try:
        # Use a model suitable for summarization
        provider_config = OpenAIProviderConfig(model="gpt-4o-mini")
        provider = OpenAIProvider(config=provider_config)
        console.print(f"[green]✓ OpenAI Provider Initialized (Model: {provider.get_model_name()})[/green]")
    except Exception as e:
        console.print(f"[bold red]Error initializing OpenAI Provider:[/bold red] {e}")
        return

    # 5. Configure and Run Summarization Agent
    # We'll use a BaseAgent with a specific prompt and output schema
    summarization_prompt = (
        "You are an expert data analyst. Based on the following data preview from an Excel sheet, "
        "provide a concise summary and list the key takeaways.\n\n"
        "Data Preview:\n"
        "```markdown\n"
        f"{tool_output.data_preview}\n"
        "```\n\n"
        f"Column Names: {', '.join(tool_output.column_names)}\n"
        f"Sheet Name: {tool_output.sheet_name_read}\n"
        f"(Note: Only the first {tool_output.row_count} rows are shown in the preview)\n\n"
        "Generate the summary and key takeaways."
    )

    # Use BaseAgent directly, configuring the output schema and prompt
    agent_config = BaseAgentConfig(
        provider=provider,
        system_prompt=summarization_prompt, # Use the detailed prompt as the system prompt
        output_schema=SummarizationOutput # Expect summary and takeaways
        # No tools needed for this specific LLM call
    )
    summarization_agent = BaseAgent(config=agent_config)
    console.print("[green]✓ Summarization Agent Configured[/green]")

    console.print("[yellow]Generating summary...[/yellow]")
    # We need a dummy input message for the BaseAgent run method
    dummy_input = BaseInputSchema(chat_message="Summarize the provided data.")
    summary_result = summarization_agent.run(dummy_input)

    # 6. Display Results
    if isinstance(summary_result, SummarizationOutput):
        console.print(Panel(summary_result.summary, title="Summary", border_style="green"))
        if summary_result.key_takeaways:
            console.print(Panel("\n".join(f"- {item}" for item in summary_result.key_takeaways), title="Key Takeaways", border_style="blue"))
    elif isinstance(summary_result, AgentErrorSchema):
        console.print(f"[bold red]Summarization Error:[/bold red] {summary_result.error_type} - {summary_result.error_message}")
    else:
        console.print(f"[bold red]Unexpected summarization result type:[/bold red] {type(summary_result)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize data from an Excel file using Karo.")
    parser.add_argument("-f", "--file", required=True, help="Path to the Excel file (.xlsx or .xls).")
    args = parser.parse_args()

    # Ensure necessary dependencies are installed: pandas, openpyxl, python-dotenv, rich
    run_summarization(args.file)