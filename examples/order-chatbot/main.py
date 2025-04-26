import os
import json
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from pydantic import Field

# Import Karo components using relative paths
try:
    from karo.core.base_agent import BaseAgent, BaseAgentConfig
    from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
    from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema # Base for custom schema
    from karo.memory.services.chromadb_service import ChromaDBService, ChromaDBConfig
    from karo.memory.memory_manager import MemoryManager # Long-term memory
    from karo.prompts.system_prompt_builder import SystemPromptBuilder
    from karo.tools.csv_reader_tool import CsvReaderInput, CsvReaderTool

except ImportError as e:
    raise ImportError(f"Ensure Karo framework components are accessible relative to main.py: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constants ---
SCRIPT_DIR = os.path.dirname(__file__)
ORDERS_CSV_PATH = os.path.join(SCRIPT_DIR, 'orders.csv')
FAQ_JSON_PATH = os.path.join(SCRIPT_DIR, 'faq_data.json')
DB_PATH = os.path.join(SCRIPT_DIR, ".karo_orderbot_db") # Local DB path
FAQ_COLLECTION_NAME = "orderbot_faq"

# --- Agent Output Schema ---
class OrderBotOutputSchema(BaseOutputSchema):
    """
    Output schema for the Order Bot. Determines the next action.
    """
    action: str = Field(..., description="The required action: 'ANSWER', 'REQUEST_INFO', 'LOOKUP_ORDER'.")
    response_text: Optional[str] = Field(None, description="The direct text response to the user (used for ANSWER or REQUEST_INFO).")
    tool_parameters: Optional[CsvReaderInput] = Field(None, description="Parameters if action is 'LOOKUP_ORDER'.")

    @classmethod
    def model_validator(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        action = values.get('action')
        response = values.get('response_text')
        params = values.get('tool_parameters')

        if action == 'ANSWER' and response is not None and params is None:
            return values
        elif action == 'REQUEST_INFO' and response is not None and params is None:
            return values
        elif action == 'LOOKUP_ORDER' and response is None and params is not None:
            return values
        else:
            raise ValueError(f"Invalid combination for action '{action}'. Check response_text and tool_parameters.")

# --- Main Application Logic ---
def load_faq_data(memory_manager: MemoryManager, faq_file: str):
    """Loads FAQ data from JSON into the MemoryManager."""
    try:
        with open(faq_file, 'r') as f:
            faqs = json.load(f)
        logger.info(f"Loading {len(faqs)} FAQs from {faq_file}...")
        for i, item in enumerate(faqs):
            # Store question as the main text for retrieval, answer in metadata
            memory_id = f"faq_{i+1}"
            text_to_embed = item['question']
            metadata = {"answer": item['answer'], "source": "faq"}
            memory_manager.add_memory(text=text_to_embed, metadata=metadata, memory_id=memory_id)
        logger.info("FAQ loading complete.")
        # Removed call to non-existent count_memories method

    except FileNotFoundError:
        logger.error(f"FAQ file not found: {faq_file}")
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from FAQ file: {faq_file}")
    except Exception as e:
        logger.error(f"Error loading FAQ data: {e}", exc_info=True)

def main():
    console = Console()
    console.print(Panel("[bold cyan]Karo Framework - Order Chatbot Example[/bold cyan]", title="Welcome", expand=False))

    # --- Initialization ---
    load_dotenv(dotenv_path=os.path.join(SCRIPT_DIR, '../../.env')) # Load .env from root
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY needed.")
        return

    try:
        # Memory
        chroma_config = ChromaDBConfig(path=DB_PATH, collection_name=FAQ_COLLECTION_NAME)
        chroma_service = ChromaDBService(config=chroma_config)
        memory_manager = MemoryManager(chroma_service=chroma_service)
        console.print(f"[green]✓ Memory System Initialized (DB: {DB_PATH}, Collection: {FAQ_COLLECTION_NAME})[/green]")
        load_faq_data(memory_manager, FAQ_JSON_PATH) # Load FAQs

        # Tool
        order_reader_tool = CsvReaderTool()
        available_tools = {order_reader_tool.get_name(): order_reader_tool}
        console.print(f"[green]✓ Tools Initialized: {', '.join(available_tools.keys())}[/green]")

        # Provider
        provider_config = OpenAIProviderConfig(model="gpt-4o-mini")
        provider = OpenAIProvider(config=provider_config)
        console.print(f"[green]✓ OpenAI Provider Initialized (Model: {provider.get_model_name()})[/green]")

        # Agent
        # Conversation history is now initialized inside BaseAgent

        system_prompt = (
            "You are an Order Support Chatbot. Your primary functions are:\n"
            "1. Answer general questions based ONLY on the provided FAQ context.\n"
            "2. Look up order status using the 'csv_order_reader' tool.\n\n"
            "ORDER LOOKUP RULES:\n"
            "- To look up an order, you MUST have BOTH the Order Number and the Customer Email.\n"
            "- If the user asks for order status but hasn't provided both, set action='REQUEST_INFO' and ask for the missing information in 'response_text'.\n"
            "- If you have both Order Number and Customer Email, set action='LOOKUP_ORDER' and populate 'tool_parameters' with 'order_number', 'customer_email', and 'file_path' ('" + ORDERS_CSV_PATH + "'). Do NOT populate 'response_text'.\n\n"
            "FAQ RULES:\n"
            "- If the user asks a general question, check the provided 'Relevant Previous Information' (FAQ context).\n"
            "- If a relevant FAQ answer is found, set action='ANSWER' and provide the answer directly in 'response_text'.\n"
            "- If the question is general but NOT covered by the FAQs, politely state that you cannot answer that specific question and can only help with order status or the provided FAQs. Set action='ANSWER'.\n\n"
            "GENERAL RULES:\n"
            "- Be polite, helpful, and conversational.\n"
            "- After successfully providing an order status or answering an FAQ, always ask if there is anything else you can help with.\n"
            "- Do not answer questions outside the scope of order status or the provided FAQs.\n"
            "- Always respond using the required output schema format."
        )

        # Configure agent, passing max_history_messages
        agent_config = BaseAgentConfig(
            provider=provider,
            memory_manager=memory_manager, # For FAQ retrieval
            max_history_messages=10, # Control history buffer size here
            output_schema=OrderBotOutputSchema,
            prompt_builder=SystemPromptBuilder(role_description=system_prompt),
            memory_query_results=3 # Retrieve top 3 relevant FAQs
        )
        # Removed post-init assignment and debug log for conversation_history
        agent = BaseAgent(config=agent_config)
        console.print("[green]✓ Order Bot Agent Initialized[/green]") # Simplified log message

    except Exception as e:
        console.print(f"[bold red]Initialization Error:[/bold red] {e}")
        logger.error("Initialization failed", exc_info=True)
        return

    # --- Interaction Loop ---
    console.print("\n[bold]Welcome to Order Support! How can I help you today?[/bold]")
    console.print("(Type 'quit' to exit)")
    # Removed manual conversation_history list
    while True:
        try:
            user_input_text = console.input("[bold blue]You:[/bold blue] ")
            if user_input_text.lower() == 'quit':
                break
            if not user_input_text:
                continue

            # Prepare agent input (BaseAgent will now handle adding this to history)
            input_data = BaseInputSchema(chat_message=user_input_text)

            console.print("[yellow]Bot thinking...[/yellow]")

            # Agent run now handles history and memory retrieval internally
            agent_output = agent.run(input_data)

            # --- External Orchestration ---
            # Removed manual history management and direct provider call
            # BaseAgent now adds user/assistant messages to its ConversationHistory instance
            if isinstance(agent_output, OrderBotOutputSchema):
                action = agent_output.action
                response_text = agent_output.response_text
                tool_params = agent_output.tool_parameters

                if action == "ANSWER" or action == "REQUEST_INFO":
                    console.print(f"[bold green]Bot:[/bold green] {response_text}")
                    # bot_response_for_history = response_text # Removed (handled by BaseAgent)
                elif action == "LOOKUP_ORDER":
                    if tool_params and tool_params.order_number and tool_params.customer_email:
                        console.print(f"[magenta]Bot needs to lookup order {tool_params.order_number}...[/magenta]")
                        # Ensure file path is set correctly
                        tool_params.file_path = ORDERS_CSV_PATH
                        try:
                            tool_result = order_reader_tool.run(tool_params)
                            if tool_result.success:
                                # --- Feed result back to agent for final response ---
                                tool_result_text = f"Successfully found order {tool_result.order_number}. Status: {tool_result.status}."
                                logger.info(f"Tool success: {tool_result_text}")
                                # Add tool result to history (as assistant context)
                                agent.conversation_history.add_message(role="assistant", content=tool_result_text)

                                console.print("[yellow]Bot formulating final response...[/yellow]")
                                # Build prompt with history including tool result
                                final_prompt_messages = agent._create_prompt_with_history(retrieved_memories=None) # Use history, maybe not FAQs again?
                                # Call provider directly for final response
                                final_agent_output = agent.provider.generate_response(
                                    prompt=final_prompt_messages,
                                    output_schema=agent.config.output_schema
                                )

                                if isinstance(final_agent_output, OrderBotOutputSchema) and final_agent_output.action == "ANSWER":
                                     console.print(f"[bold green]Bot:[/bold green] {final_agent_output.response_text}")
                                     # BaseAgent will add this final response to history automatically now
                                else:
                                     # Fallback if agent didn't generate expected final answer
                                     logger.warning(f"Agent did not provide expected ANSWER action after tool success. Output: {final_agent_output}")
                                     console.print(f"[bold green]Bot:[/bold green] {tool_result_text} Is there anything else I can help with?") # Manual fallback
                                     agent.conversation_history.add_message(role="assistant", content=f"{tool_result_text} Is there anything else I can help with?") # Add fallback to history

                                # --- End feedback loop ---
                            else:
                                # Tool failed, report error directly
                                tool_error_text = f"I couldn't retrieve the status. {tool_result.error_message}"
                                console.print(f"[bold green]Bot:[/bold green] {tool_error_text}")
                                # Add this error response to history via BaseAgent
                                agent.conversation_history.add_message(role="assistant", content=tool_error_text)
                        except Exception as tool_err:
                            logger.error(f"Error executing tool {order_reader_tool.name}: {tool_err}", exc_info=True)
                            error_text = "Sorry, there was an error trying to look up the order."
                            console.print(f"[bold red]Bot:[/bold red] {error_text}")
                            # Add this error response to history via BaseAgent
                            agent.conversation_history.add_message(role="assistant", content=error_text)
                    else:
                         console.print("[bold red]Error:[/bold red] Agent requested LOOKUP_ORDER but didn't provide valid parameters.")
                else:
                     console.print(f"[bold red]Error:[/bold red] Agent returned unknown action '{action}'.")
                     # bot_response_for_history = "I seem to have encountered an internal issue." # Removed (handled by BaseAgent)

            elif isinstance(agent_output, AgentErrorSchema):
                error_msg = f"Agent Error: {agent_output.error_type} - {agent_output.error_message}"
                console.print(f"[bold red]{error_msg}[/bold red]")
                # bot_response_for_history = f"Sorry, I encountered an error: {agent_output.error_type}" # Removed (handled by BaseAgent)
            else:
                error_msg = f"Unexpected result type from agent: {type(agent_output)}"
                console.print(f"[bold red]{error_msg}[/bold red]")
                # bot_response_for_history = "Sorry, I encountered an unexpected issue." # Removed (handled by BaseAgent)
        # --- End Orchestration ---

        # History is now managed internally by BaseAgent via ConversationHistory

        except KeyboardInterrupt:
            # Correct indentation for the except block
            break
        except Exception as e:
            # Correct indentation for the except block
            console.print(f"[bold red]An unexpected error occurred in the loop:[/bold red] {e}")
            logger.error("Error in interaction loop", exc_info=True)

    console.print("\n[bold cyan]Exiting Order Chatbot. Goodbye![/bold cyan]")

if __name__ == "__main__":
    # Add check for dependencies like pandas
    try:
        import pandas
    except ImportError:
        print("Error: 'pandas' library is required. Please install it using 'pip install pandas'")
    else:
        main()