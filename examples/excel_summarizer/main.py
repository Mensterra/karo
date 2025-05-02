# import argparse
# import os
# from dotenv import load_dotenv
# from karo.prompts.system_prompt_builder import SystemPromptBuilder
# from rich.console import Console
# from pydantic import Field
# from typing import List, Dict, Any
# from rich.panel import Panel
# import logging

# # Configure basic logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# # Load environment variables from .env file (assuming it's in the root karo/ dir)
# dotenv_path = os.path.join(os.path.dirname(__file__), '../../.env')
# load_dotenv(dotenv_path=dotenv_path)

# # Import Karo components
# from karo.core.base_agent import BaseAgent, BaseAgentConfig
# from karo.providers.anthropic_provider import AnthropicProvider, AnthropicProviderConfig
# from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema
# # Import the custom tool using relative import
# from examples.excel_summarizer.excel_reader_tool import ExcelReaderInput, ExcelReaderTool


# # Initialize console for rich output
# console = Console()

# # --- Define a specific output schema for the summarization ---
# class SummarizationOutput(BaseOutputSchema):
#     summary: str = Field(..., description="A concise summary of the provided data.")
#     key_takeaways: List[str] = Field(default_factory=list, description="A list of key points or takeaways from the data.")

# def run_summarization(file_path: str):
#     """Orchestrates reading the Excel file and generating a summary."""
#     console.print(Panel(f"[bold cyan]Excel Summarizer Example: Processing '{file_path}'[/bold cyan]", title="Karo", expand=False))

#     # 1. Check for API Key
#     api_key = os.getenv("ANTHROPIC_API_KEY")
#     if not api_key:
#         console.print("[bold red]Error:[/bold red] ANTHROPIC_API_KEY environment variable not set.")
#         return

#     # 2. Initialize Tool
#     try:
#         excel_reader = ExcelReaderTool()
#         console.print("[green]✓ ExcelReaderTool Initialized[/green]")
#     except Exception as e:
#         console.print(f"[bold red]Error initializing ExcelReaderTool:[/bold red] {e}")
#         return

#     # 3. Run Tool to Read Excel Data
#     console.print(f"[yellow]Reading data from '{file_path}'...[/yellow]")
#     tool_input = ExcelReaderInput(file_path=file_path)
#     tool_output = excel_reader.run(tool_input)

#     if not tool_output.success or not tool_output.data_preview:
#         console.print(f"[bold red]Error reading Excel file:[/bold red] {tool_output.error_message}")
#         return

#     console.print(f"[green]✓ Successfully read sheet '{tool_output.sheet_name_read}' ({tool_output.row_count} rows, {len(tool_output.column_names)} cols)[/green]")
#     console.print(Panel(tool_output.data_preview, title="Data Preview", border_style="dim"))

#     # 4. Initialize Anthropic Provider
#     try:
#         # Use Claude 3 Opus for high-quality summarization
#         provider_config = AnthropicProviderConfig(model="claude-3-opus-20240229", temperature=0.7)
#         provider = AnthropicProvider(config=provider_config)
#         console.print(f"[green]✓ Anthropic Provider Initialized (Model: {provider.get_model_name()})[/green]")
#     except Exception as e:
#         console.print(f"[bold red]Error initializing Anthropic Provider:[/bold red] {e}")
#         return

#     # 5. Configure and Run Summarization Agent
#     # Define a system prompt
#     system_prompt_content = "You are an expert data analyst. Your task is to analyze Excel data and provide accurate summaries and insights."
    
#     # Create a proper system prompt builder object
#     system_prompt_builder = SystemPromptBuilder(role_description=system_prompt_content)
    
#     # Create agent configuration with the proper system prompt
#     agent_config = BaseAgentConfig(
#         provider_config=provider_config,
#         system_prompt=system_prompt_builder,
#         output_schema=SummarizationOutput
#     )
    
#     # Initialize the agent
#     summarization_agent = BaseAgent(config=agent_config)
#     console.print("[green]✓ Summarization Agent Configured[/green]")
    
#     # Create the message content about the Excel data
#     data_message = (
#         "Please analyze this sales data:\n\n"
#         "Data Preview:\n"
#         "```markdown\n"
#         f"{tool_output.data_preview}\n"
#         "```\n\n"
#         f"Column Names: {', '.join(tool_output.column_names)}\n"
#         f"Sheet Name: {tool_output.sheet_name_read}\n"
#         f"(Note: Only the first {tool_output.row_count} rows are shown in the preview)\n\n"
#         "Generate a summary that specifically analyzes the sales data by region and salesperson. "
#         "Include insights about top performers and regional performance."
#     )
    
#     # Debug log to see the prompts being constructed
#     console.print(Panel(f"[bold yellow]Debug - System Prompt:[/bold yellow]\n{system_prompt_content}", 
#                         title="System Prompt", border_style="yellow"))
#     console.print(Panel(f"[bold yellow]Debug - User Message:[/bold yellow]\n{data_message}", 
#                         title="User Message", border_style="yellow"))
    
#     # Important: Create an external history to pass to BaseAgent
#     # This ensures our message reaches the LLM properly
#     external_history = [
#         {"role": "user", "content": data_message}
#     ]
    
#     # Log the agent configuration and history
#     logger.info(f"Agent configuration: {agent_config}")
#     logger.info(f"External history being passed: {external_history}")
    
#     console.print("[yellow]Generating summary...[/yellow]")
    
#     # Use a simple input for the run method - all data is in the history
#     simple_input = BaseInputSchema(chat_message="")
    
#     # Pass the external_history to ensure our data message gets to the LLM
#     summary_result = summarization_agent.run(
#         input_data=simple_input,
#         history=external_history
#     )

#     # 6. Display Results
#     if isinstance(summary_result, SummarizationOutput):
#         console.print(Panel(summary_result.summary, title="Summary", border_style="green"))
#         if summary_result.key_takeaways:
#             console.print(Panel("\n".join(f"- {item}" for item in summary_result.key_takeaways), title="Key Takeaways", border_style="blue"))
#     elif isinstance(summary_result, AgentErrorSchema):
#         console.print(f"[bold red]Summarization Error:[/bold red] {summary_result.error_type} - {summary_result.error_message}")
#     else:
#         console.print(f"[bold red]Unexpected summarization result type:[/bold red] {type(summary_result)}")


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Summarize data from an Excel file using Karo.")
#     parser.add_argument("-f", "--file", required=True, help="Path to the Excel file (.xlsx or .xls).")
#     args = parser.parse_args()

#     # Run the summarization
#     run_summarization(args.file)


import argparse
import os
from dotenv import load_dotenv
from karo.prompts.system_prompt_builder import SystemPromptBuilder
from rich.console import Console
from pydantic import Field
from typing import List, Dict, Any
from rich.panel import Panel
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file (assuming it's in the root karo/ dir)
dotenv_path = os.path.join(os.path.dirname(__file__), '../../.env')
load_dotenv(dotenv_path=dotenv_path)

# Import Karo components
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema
# Import the custom tool using relative import
from examples.excel_summarizer.excel_reader_tool import ExcelReaderInput, ExcelReaderTool


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

    # 4. Initialize OpenAI Provider
    try:
        # Use GPT-4-turbo for high-quality summarization
        provider_config = OpenAIProviderConfig(model="gpt-4-turbo", temperature=0.7)
        provider = OpenAIProvider(config=provider_config)
        console.print(f"[green]✓ OpenAI Provider Initialized (Model: {provider.get_model_name()})[/green]")
    except Exception as e:
        console.print(f"[bold red]Error initializing OpenAI Provider:[/bold red] {e}")
        return

    # 5. Configure and Run Summarization Agent
    # Define a system prompt
    system_prompt_content = "You are an expert data analyst. Your task is to analyze Excel data and provide accurate summaries and insights."
    
    # Create a proper system prompt builder object
    system_prompt_builder = SystemPromptBuilder(role_description=system_prompt_content)
    
    # Create agent configuration with the proper system prompt
    agent_config = BaseAgentConfig(
        provider_config=provider_config,
        system_prompt=system_prompt_builder,
        output_schema=SummarizationOutput
    )
    
    # Initialize the agent
    summarization_agent = BaseAgent(config=agent_config)
    console.print("[green]✓ Summarization Agent Configured[/green]")
    
    # Create the message content about the Excel data
    data_message = (
        "Please analyze this sales data:\n\n"
        "Data Preview:\n"
        "```markdown\n"
        f"{tool_output.data_preview}\n"
        "```\n\n"
        f"Column Names: {', '.join(tool_output.column_names)}\n"
        f"Sheet Name: {tool_output.sheet_name_read}\n"
        f"(Note: Only the first {tool_output.row_count} rows are shown in the preview)\n\n"
        "Generate a summary that specifically analyzes the sales data by region and salesperson. "
        "Include insights about top performers and regional performance."
    )
    
    # Debug log to see the prompts being constructed
    console.print(Panel(f"[bold yellow]Debug - System Prompt:[/bold yellow]\n{system_prompt_content}", 
                        title="System Prompt", border_style="yellow"))
    console.print(Panel(f"[bold yellow]Debug - User Message:[/bold yellow]\n{data_message}", 
                        title="User Message", border_style="yellow"))
    
    # Important: Create an external history to pass to BaseAgent
    # This ensures our message reaches the LLM properly
    external_history = [
        {"role": "user", "content": data_message}
    ]
    
    # Log the agent configuration and history
    logger.info(f"Agent configuration: {agent_config}")
    logger.info(f"External history being passed: {external_history}")
    
    console.print("[yellow]Generating summary...[/yellow]")
    
    # Use a simple input for the run method - all data is in the history
    simple_input = BaseInputSchema(chat_message="")
    
    # Pass the external_history to ensure our data message gets to the LLM
    summary_result = summarization_agent.run(
        input_data=simple_input,
        history=external_history
    )

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

    # Run the summarization
    run_summarization(args.file)