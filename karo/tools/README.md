# Karo Framework - Tools

This directory contains tools that can be used by Karo agents to perform specific actions or interact with external systems.

## Core Concepts

*   **`BaseTool` (`base_tool.py`):** An Abstract Base Class (ABC) defining the standard interface for all tools. It requires subclasses to define `input_schema`, `output_schema`, `__init__`, and `run` methods. It also provides optional `name` and `description` attributes used for identification and informing the LLM.
*   **Tool Schemas (`BaseToolInputSchema`, `BaseToolOutputSchema`):** Base Pydantic models that tool-specific input/output schemas should inherit from. This promotes consistency.
*   **Concrete Tools (e.g., `calculator_tool.py`, `document_reader_tool.py`):** Classes inheriting from `BaseTool` that implement a specific functionality. Each tool defines its unique input/output schemas and the logic within its `run` method.

## How Tools Integrate with `BaseAgent`

1.  **Configuration:** A list of tool instances (e.g., `[CalculatorTool(), WebSearchTool()]`) is passed to the `BaseAgentConfig` during agent setup.
2.  **Preparation:** The `BaseAgent` converts these tool instances into a format suitable for the LLM API (e.g., OpenAI's function/tool format) using the `_prepare_llm_tools` helper method. This format includes the tool's name, description, and input parameter schema.
3.  **LLM Call:** When the agent runs, it passes the prepared tool definitions to the LLM provider via the `tools` parameter. It typically also sets `tool_choice="auto"` to let the LLM decide if and which tool to use.
4.  **Tool Call Detection (Provider Responsibility - TODO):** The LLM provider (e.g., `OpenAIProvider`) needs to be enhanced to:
    *   Recognize when the LLM response includes a request to call a tool (`tool_calls`).
    *   Parse the tool name and arguments from the response.
5.  **Execution (Agent Responsibility - TODO):** If the provider signals a tool call:
    *   The `BaseAgent` (or a dedicated tool execution loop within it) looks up the corresponding tool instance in its `tool_map`.
    *   It validates the arguments provided by the LLM against the tool's `input_schema`.
    *   It executes the tool's `run` method with the validated arguments.
    *   It formats the tool's output (from its `output_schema`) into a message suitable for the LLM (e.g., role=`tool`).
6.  **Final Response Generation (Agent Responsibility - TODO):** The agent sends the conversation history (including the initial user message, the assistant's tool call request, and the tool's output message) back to the LLM (with `tool_choice="none"`) to generate the final, user-facing response.

*(Note: Steps 4, 5, and 6 require further implementation in `BaseAgent` and the provider classes.)*

## Creating Custom Tools

1.  **Define Schemas:** Create Pydantic models inheriting from `BaseToolInputSchema` and `BaseToolOutputSchema` for your tool's specific inputs and outputs. Ensure the output schema includes `success: bool` and `error_message: Optional[str]`.
2.  **Create Tool Class:** Create a new class inheriting from `BaseTool`.
3.  **Set Class Attributes:** Define the `input_schema`, `output_schema`, `name` (must be unique), and `description` class attributes.
4.  **Implement `__init__`:** Add an initializer if your tool requires configuration or setup (e.g., API keys, service connections).
5.  **Implement `run`:** Write the core logic of your tool within the `run` method. It should:
    *   Accept an instance of your tool's input schema.
    *   Perform its action.
    *   Handle potential errors gracefully.
    *   Return an instance of your tool's output schema, correctly setting the `success` flag and `error_message` if applicable.
6.  **Instantiate and Use:** Instantiate your new tool and add it to the `tools` list in the `BaseAgentConfig` when creating an agent.

## Built-in Tools

Karo aims to provide some common tools out-of-the-box:

*   **`CalculatorTool` (`calculator_tool.py`):** Performs basic arithmetic operations.
*   **`DocumentReaderTool` (`document_reader_tool.py`):** Reads text content from `.txt`, `.md`, `.pdf`, and `.docx` files. Requires optional dependencies `pypdf` and `python-docx` for PDF/DOCX support.