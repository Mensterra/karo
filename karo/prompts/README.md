# Karo Framework - Prompts

This directory contains components related to prompt engineering and management within the Karo framework.

## `system_prompt_builder.py`

*   **`SystemPromptBuilder`**: A class designed to construct complex system prompts dynamically. It allows defining static sections (like agent role, core instructions, security guidelines) and dynamically inserting context such as available tools and retrieved memories.

### Key Features:
*   **Structured Sections:** Organizes the prompt into logical parts (role, instructions, tools, memory, output format, security).
*   **Configurability:** Allows customization of section content, order, and headers during initialization.
*   **Dynamic Content:** The `build()` method accepts lists of tools (formatted for the LLM) and memory results, incorporating them into the final prompt string.
*   **Basic Security:** Includes a default (or customizable) section to instruct the LLM against prompt injection attempts.

### Usage with `BaseAgent`:
1.  Instantiate `SystemPromptBuilder` with desired static sections (role description is required).
2.  Pass the builder instance to `BaseAgentConfig` via the `prompt_builder` argument.
3.  The `BaseAgent` will automatically use the builder in its `_create_prompt` method, passing the agent's formatted tools (`llm_tools`) and any retrieved memories to the builder's `build()` method before making the LLM call.

This provides a flexible and maintainable way to manage potentially complex system prompts for different agents.