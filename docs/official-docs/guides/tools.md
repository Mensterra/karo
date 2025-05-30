# Guide: Using and Creating Tools

Tools are essential components in the Karo framework that allow agents to interact with the outside world, perform specific calculations, access databases, or call external APIs. They extend the capabilities of the LLM beyond its internal knowledge.

## Core Concepts

*   **`BaseTool`:** An abstract base class (`karo.tools.base_tool.BaseTool`) that all tools must inherit from. It defines the standard interface.
*   **Input/Output Schemas:** Each tool defines its expected input and output using Pydantic models that inherit from `BaseToolInputSchema` and `BaseToolOutputSchema`. This ensures structured data exchange and validation.
*   **`run` Method:** The core logic of the tool resides in its `run` method, which takes the validated input schema instance and returns an instance of the output schema.
*   **Name & Description:** Each tool has a `name` (unique identifier) and a `description` (natural language explanation for the LLM). These are crucial for the LLM to understand when and how to use the tool.

## Using Built-in Tools

Karo provides some common tools ready to use:

*   **`CalculatorTool` (`karo.tools.calculator_tool.CalculatorTool`):**
    *   **Purpose:** Performs basic arithmetic (+, -, \*, /, ^).
    *   **Input:** `CalculatorInput(operand1: float, operand2: float, operator: str)`
    *   **Output:** `CalculatorOutput(result: Optional[float], success: bool, error_message: Optional[str])`
*   **`DocumentReaderTool` (`karo.tools.document_reader_tool.DocumentReaderTool`):**
    *   **Purpose:** Reads text content from files (.txt, .md, .pdf, .docx).
    *   **Input:** `DocumentReaderInput(file_path: FilePath)`
    *   **Output:** `DocumentReaderOutput(content: Optional[str], file_path: Optional[str], success: bool, error_message: Optional[str])`
    *   **Dependencies:** Requires `pypdf` and `python-docx` to be installed for PDF/DOCX support (`pip install pypdf python-docx`).

**How to Use (Refactored Approach):**

1.  **Import & Instantiate Tool:** Import the tool class and create an instance, providing any necessary configuration.
    ```python
    from karo.tools.calculator_tool import CalculatorTool, CalculatorInput
    # ... other imports

    calculator = CalculatorTool()
    # Store instantiated tools for lookup, e.g., in a dictionary
    available_tools = {calculator.get_name(): calculator}
    ```
2.  **Define Agent Output Schema:** Create or use an output schema for your agent that allows it to specify *which* tool to use and the *parameters* for that tool. This schema should inherit from `BaseOutputSchema`.
    ```python
    from pydantic import Field
    from typing import Union, Optional
    from karo.schemas.base_schemas import BaseOutputSchema
    # Import input schemas for the tools the agent might call
    from karo.tools.calculator_tool import CalculatorInput
    # from karo.tools.memory_query_tool import MemoryQueryInput # etc.

    class OrchestrationOutputSchema(BaseOutputSchema):
        tool_name: Optional[str] = Field(None, description="The name of the tool to execute.")
        tool_parameters: Optional[Union[CalculatorInput, ...]] = Field(None, description="The input parameters for the selected tool.")
        direct_response: Optional[str] = Field(None, description="Direct response if no tool needed.")
        # Add validation logic if needed (e.g., ensure tool_name+params OR direct_response)
    ```
3.  **Configure Agent:** Configure your `BaseAgent` instance, setting its `output_schema` to the orchestration schema you defined. **Do not** pass tools directly to the agent config anymore.
    ```python
    from karo.core.base_agent import BaseAgent, BaseAgentConfig
    # ... other imports

    agent_config = BaseAgentConfig(
        provider=my_provider,
        output_schema=OrchestrationOutputSchema, # Use the orchestration schema
        # ... other config (memory, prompt_builder)
    )
    agent = BaseAgent(config=agent_config)
    ```
4.  **Instruct the Agent:** Modify the agent's system prompt to instruct it:
    *   About the available tools (by name and description).
    *   To decide if a tool is needed based on the user query.
    *   If a tool is needed, to respond using the `OrchestrationOutputSchema` format, populating `tool_name` and `tool_parameters` (matching the specific tool's input schema).
    *   If no tool is needed, to populate the `direct_response` field instead.
5.  **Implement External Orchestration Logic:** In your application code where you call `agent.run()`:
    *   Receive the agent's output (which should be an instance of `OrchestrationOutputSchema`).
    *   Check if `agent_output.tool_name` is set.
    *   If yes:
        *   Look up the corresponding tool instance (e.g., from the `available_tools` dictionary).
        *   Call `tool_instance.run(agent_output.tool_parameters)`.
        *   Process the tool's result.
    *   If no `tool_name` is set, use `agent_output.direct_response`.

    ```python
    # --- In your application loop ---
    agent_output = agent.run(user_input_data)

    if isinstance(agent_output, OrchestrationOutputSchema):
        if agent_output.tool_name and agent_output.tool_parameters:
            tool_to_run = available_tools.get(agent_output.tool_name)
            if tool_to_run:
                print(f"Executing tool: {agent_output.tool_name}")
                tool_result = tool_to_run.run(agent_output.tool_parameters)
                print(f"Tool result: {tool_result}")
                # Process tool_result...
            else:
                print(f"Error: Agent requested unknown tool '{agent_output.tool_name}'")
        elif agent_output.direct_response:
            print(f"Agent response: {agent_output.direct_response}")
        else:
            print("Agent returned no action.")
    # Handle AgentErrorSchema etc.
    # --- End application loop snippet ---
    ```

## Creating Custom Tools

Building your own tools is straightforward:

1.  **Define Schemas:**
    *   Create an input schema class inheriting from `karo.tools.base_tool.BaseToolInputSchema`. Define fields using Pydantic for all necessary inputs.
    *   Create an output schema class inheriting from `karo.tools.base_tool.BaseToolOutputSchema`. Define fields for the results your tool will produce. Remember it automatically includes `success: bool` and `error_message: Optional[str]`.

    ```python
    from karo.tools.base_tool import BaseTool, BaseToolInputSchema, BaseToolOutputSchema
    from pydantic import Field
    from typing import Optional

    class MyToolInput(BaseToolInputSchema):
        target_url: str = Field(..., description="The URL to process.")
        max_length: Optional[int] = Field(None, description="Optional max length.")

    class MyToolOutput(BaseToolOutputSchema):
        processed_data: Optional[str] = Field(None, description="The result of processing.")
        items_found: Optional[int] = Field(None)
    ```

2.  **Create Tool Class:**
    *   Create a class inheriting from `karo.tools.base_tool.BaseTool`.
    *   Define the required class attributes:
        *   `input_schema`: Set to your input schema class (e.g., `MyToolInput`).
        *   `output_schema`: Set to your output schema class (e.g., `MyToolOutput`).
        *   `name`: A unique, descriptive snake_case name (e.g., `"web_scraper"`).
        *   `description`: A clear, concise description for the LLM explaining what the tool does and when to use it.

    ```python
    from typing import Type # Import Type for schema hints

    class MyWebTool(BaseTool):
        input_schema: Type[MyToolInput] = MyToolInput
        output_schema: Type[MyToolOutput] = MyToolOutput
        name: str = "my_web_tool"
        description: str = "Scrapes a target URL and returns processed data."
        # ... __init__ and run methods follow ...
    ```

3.  **Implement `__init__`:**
    *   Add an `__init__` method if your tool needs any setup or configuration (like API keys, database connections, service instances). Accept these via a `config: Optional[Dict[str, Any]] = None` argument or direct keyword arguments.

    ```python
    class MyWebTool(BaseTool):
        # ... schemas, name, description ...
        api_key: str

        def __init__(self, config: Optional[Dict[str, Any]] = None, api_key: Optional[str] = None):
            key_to_use = api_key or (config.get("api_key") if config else None) or os.getenv("MY_API_KEY")
            if not key_to_use:
                raise ValueError("MyWebTool requires an API key.")
            self.api_key = key_to_use
            # Initialize any clients or resources here
            print("MyWebTool initialized.")
    ```

4.  **Implement `run` Method:**
    *   This is where the tool's core logic goes.
    *   It receives one argument: `input_data`, which is a validated instance of your `input_schema`.
    *   Perform the tool's action (call an API, query DB, calculate, etc.).
    *   Handle potential errors gracefully using `try...except`.
    *   Return an instance of your `output_schema`, setting `success=True` and populating result fields on success, or `success=False` and setting `error_message` on failure.

    ```python
    import httpx # Example dependency

    class MyWebTool(BaseTool):
        # ... schemas, name, description, __init__ ...

        def run(self, input_data: MyToolInput) -> MyToolOutput:
            logger.info(f"Running MyWebTool for URL: {input_data.target_url}")
            try:
                # Example: Make an external API call
                response = httpx.get(input_data.target_url, headers={"Authorization": f"Bearer {self.api_key}"})
                response.raise_for_status() # Raise exception for bad status codes
                data = response.json()

                # Process data (example)
                processed = str(data)[:input_data.max_length] if input_data.max_length else str(data)
                items = len(data.get("items", [])) if isinstance(data, dict) else None

                return self.output_schema(
                    success=True,
                    processed_data=processed,
                    items_found=items
                )
            except httpx.RequestError as e:
                logger.error(f"HTTP error calling {input_data.target_url}: {e}")
                return self.output_schema(success=False, error_message=f"HTTP Request failed: {e}")
            except Exception as e:
                logger.error(f"Error running MyWebTool: {e}", exc_info=True)
                return self.output_schema(success=False, error_message=f"Tool execution failed: {e}")

    ```

5.  **Use the Tool:** Instantiate your custom tool and make it available to your external orchestration logic (e.g., add it to the `available_tools` dictionary). Update your agent's system prompt and `OrchestrationOutputSchema` (specifically the `Union` in `tool_parameters`) to include the new tool and its input schema. Ensure your orchestration logic can handle the new `tool_name` when the agent requests it.