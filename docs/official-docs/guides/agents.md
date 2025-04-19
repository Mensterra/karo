# Guide: Agents in Karo

The core concept in Karo is the **Agent**. An agent is responsible for orchestrating interactions with Large Language Models (LLMs), using tools, accessing memory, and managing the overall task execution flow.

## `BaseAgent`

The primary class you'll typically use or subclass is `karo.core.base_agent.BaseAgent`. It provides the fundamental ReAct-style loop for reasoning and acting.

**Key Responsibilities:**

*   Receiving input data (validated against a schema).
*   Interacting with a configured LLM **Provider**.
*   Managing **Tools** available to the agent.
*   Optionally interacting with a **Memory** system.
*   Using a **Prompt Builder** to construct dynamic system prompts.
*   Executing the **ReAct loop**:
    1.  Call LLM (with tools, memory context).
    2.  Check if the LLM requested a tool call.
    3.  If yes: Execute the tool, get the result.
    4.  Send the tool result back to the LLM.
    5.  Get the final response.
    6.  If no tool call initially, return the direct LLM response.
*   Returning the final output (validated against a schema) or an error schema.

## `BaseAgentConfig`

The behavior of a `BaseAgent` instance is determined by its configuration, defined by the `karo.core.base_agent.BaseAgentConfig` Pydantic model.

**Key Configuration Fields:**

*   `provider: BaseProvider`: **Required.** An instance of an LLM provider (e.g., `OpenAIProvider`). This tells the agent which LLM service to use.
*   `input_schema: Type[BaseInputSchema]`: The Pydantic model defining the expected input structure. Defaults to `BaseInputSchema` (which expects a `chat_message: str`). You can subclass `BaseInputSchema` for more complex inputs.
*   `output_schema: Type[BaseOutputSchema]`: The Pydantic model defining the desired final output structure. Defaults to `BaseOutputSchema` (which expects a `response_message: str`). The agent uses `instructor` (via the provider) to try and force the LLM's final response into this schema.
*   `prompt_builder: Optional[SystemPromptBuilder]`: An instance of `SystemPromptBuilder` used to construct the system prompt dynamically. If `None`, a default builder with a basic role description is used. See the [Prompts Guide](./prompts.md) for details.
*   `memory_manager: Optional[MemoryManager]`: An instance of `MemoryManager` if the agent needs to access persistent memory (e.g., for RAG from a knowledge base). See the [Memory Guide](./memory.md) *(Coming Soon)*.
*   `memory_query_results: int`: If `memory_manager` is used, this specifies how many relevant memory chunks to retrieve per query (default: 3).
*   `tools: Optional[List[BaseTool]]`: A list of tool instances (e.g., `[CalculatorTool(), OrderCSVTool()]`) that the agent can use. See the [Tools Guide](./tools.md) *(Coming Soon)*.
*   `max_tool_iterations: int`: The maximum number of times the agent will loop through the LLM -> Tool -> LLM cycle before giving up and forcing a final response (default: 5). Prevents infinite loops.

## Creating an Agent Instance

You typically create a function or class that handles the initialization of all necessary components (provider, tools, memory, prompt builder) and then instantiates the `BaseAgentConfig` and `BaseAgent`.

```python
# Example structure (see order_agent/agent.py for a full example)
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
from karo.prompts.system_prompt_builder import SystemPromptBuilder
# ... import tools, memory manager etc.

def create_my_agent():
    # 1. Init Provider
    provider_config = OpenAIProviderConfig(model="gpt-4o-mini")
    provider = OpenAIProvider(config=provider_config)

    # 2. Init Tools (if any)
    # calculator = CalculatorTool()
    # available_tools = [calculator]

    # 3. Init Memory (if any)
    # memory_manager = MemoryManager(...)

    # 4. Init Prompt Builder
    prompt_builder = SystemPromptBuilder(
        role_description="You are MyAgent...",
        # ... other sections
    )

    # 5. Create Agent Config
    agent_config = BaseAgentConfig(
        provider=provider,
        prompt_builder=prompt_builder,
        # tools=available_tools,
        # memory_manager=memory_manager
    )

    # 6. Create Agent
    agent = BaseAgent(config=agent_config)
    return agent

# --- Usage ---
# my_agent_instance = create_my_agent()
# input_data = BaseInputSchema(chat_message="Hello agent!")
# result = my_agent_instance.run(input_data)
# print(result)
```

This modular approach allows you to easily configure agents with different capabilities by assembling the necessary components.