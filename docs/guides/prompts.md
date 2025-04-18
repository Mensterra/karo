# Guide: Building System Prompts

The system prompt is crucial for defining an agent's behavior, capabilities, and constraints. Karo provides the `SystemPromptBuilder` class to help construct detailed and dynamic system prompts in a structured way.

## Why Use `SystemPromptBuilder`?

Instead of passing a single, potentially very long and hard-to-manage string as the system prompt, the builder allows you to define distinct sections and dynamically insert context like available tools or retrieved memories. This improves:

*   **Readability & Maintainability:** Prompts are broken down into logical parts.
*   **Flexibility:** Easily add, remove, or reorder sections.
*   **Dynamic Context:** Seamlessly integrate runtime information (tools, memory) into the prompt.
*   **Security:** Includes a dedicated section for prompt injection mitigation instructions.

## Core Concepts

The `SystemPromptBuilder` works with predefined sections. The default sections and their order are:

1.  `role_description`: The primary identity and goal of the agent (Required).
2.  `core_instructions`: General operational rules or steps.
3.  `memory_section`: Dynamically populated with relevant retrieved memories.
4.  `tool_section`: Dynamically populated with descriptions of available tools.
5.  `output_instructions`: Guidelines on the desired output format (often complements the Pydantic output schema).
6.  `security_instructions`: Warnings to the LLM against harmful instructions or prompt manipulation.

## Basic Usage

You typically initialize the builder when configuring your agent and pass it to the `BaseAgentConfig`.

```python
from karo.prompts.system_prompt_builder import SystemPromptBuilder
from karo.core.base_agent import BaseAgentConfig
# ... other imports (provider, etc.)

# 1. Define static prompt sections
role = "You are a helpful customer support assistant for an online store."
guidelines = """
- Be polite and empathetic.
- Use the available tools to answer questions about orders and store policies.
- If you cannot answer, politely state that you don't have the information.
"""
output_fmt = "Provide clear, concise answers. Use markdown for lists if needed."

# 2. Initialize the builder
prompt_builder = SystemPromptBuilder(
    role_description=role,
    core_instructions=guidelines,
    output_instructions=output_fmt
    # Uses default security instructions
)

# 3. Configure the agent
# provider = ... (initialize your provider)
# tools = [...] (initialize your tools)
# memory_manager = ... (initialize your memory manager)

agent_config = BaseAgentConfig(
    provider=provider,
    prompt_builder=prompt_builder, # Pass the builder instance
    tools=tools,
    memory_manager=memory_manager
)

# 4. Create the agent
agent = BaseAgent(config=agent_config)

# Now, when agent.run() is called, it will internally use the builder
# to construct the system prompt, automatically adding formatted
# tool descriptions and retrieved memories based on the current input.
```

## Customization

### Custom Headers

You can change the markdown headers used for different sections:

```python
custom_headers = {
    "tool_section": "### Tools You Can Use:",
    "memory_section": "### Context from Past Interactions:",
    "security_instructions": "#### IMPORTANT SAFETY NOTE"
}

builder = SystemPromptBuilder(
    role_description="My Agent",
    section_headers=custom_headers
)
```

### Custom Section Order

You can change the order in which sections appear in the final prompt:

```python
custom_order = [
    "role_description",
    "security_instructions", # Put security first
    "core_instructions",
    "memory_section",
    "tool_section",
    "output_instructions",
]

builder = SystemPromptBuilder(
    role_description="My Agent",
    section_order=custom_order
)
```

## How Dynamic Content is Added

The `BaseAgent` automatically handles formatting and passing the available tools (`agent.llm_tools`) and retrieved memories to the `prompt_builder.build()` method before each LLM call that requires a system prompt. The builder then inserts these formatted strings into the appropriate sections (`tool_section`, `memory_section`) based on the configured headers and order.

This ensures that the LLM receives the most relevant context for the current interaction turn.