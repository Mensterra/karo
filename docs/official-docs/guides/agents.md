# Guide: Agents in Karo

The core concept in Karo is the **Agent**. An agent is responsible for orchestrating interactions with Large Language Models (LLMs), using tools, accessing memory, and managing the overall task execution flow.

## `BaseAgent`

The primary class you'll typically use or subclass is `karo.core.base_agent.BaseAgent`. It provides the fundamental ReAct-style loop for reasoning and acting.

**Key Responsibilities:**

*   Receiving input data (validated against its `input_schema`).
*   Interacting with a configured LLM **Provider**.
*   Optionally interacting with a **Memory** system to retrieve context.
*   Using a **Prompt Builder** to construct dynamic system prompts (including retrieved memory).
*   Calling the LLM provider to generate a response that conforms to the agent's configured `output_schema`.
*   Returning the final output (validated `output_schema` instance) or an `AgentErrorSchema`.
*   **Note:** Tool execution is **not** handled internally by `BaseAgent`. The agent's role is typically to generate structured output (via its `output_schema`) that *indicates* which tool should be called and with what parameters. External application logic is responsible for interpreting this output and executing the corresponding tool.

## `BaseAgentConfig`

The behavior of a `BaseAgent` instance is determined by its configuration, defined by the `karo.core.base_agent.BaseAgentConfig` Pydantic model.

**Key Configuration Fields:**

*   `provider: BaseProvider`: **Required.** An instance of an LLM provider (e.g., `OpenAIProvider`). This tells the agent which LLM service to use.
*   `input_schema: Type[BaseInputSchema]`: The Pydantic model defining the expected input structure. Defaults to `BaseInputSchema` (which expects a `chat_message: str`). You can subclass `BaseInputSchema` for more complex inputs.
*   `output_schema: Type[BaseOutputSchema]`: The Pydantic model defining the desired final output structure. Defaults to `BaseOutputSchema` (which expects a `response_message: str`). The agent uses `instructor` (via the provider) to try and force the LLM's final response into this schema.
*   `prompt_builder: Optional[SystemPromptBuilder]`: An instance of `SystemPromptBuilder` used to construct the system prompt dynamically. If `None`, a default builder with a basic role description is used. See the [Prompts Guide](./prompts.md) for details.
*   `memory_manager: Optional[MemoryManager]`: An instance of `MemoryManager` if the agent needs to access **long-term persistent memory** (e.g., for RAG from a knowledge base). See the [Memory Guide](./memory.md) *(Coming Soon)*.
*   `memory_query_results: int`: If `memory_manager` is used, this specifies how many relevant memory chunks to retrieve per query (default: 3).
*   `conversation_history: Optional[ConversationHistory]`: An instance of `ConversationHistory` (`karo.memory.conversation_history.ConversationHistory`) used to manage the **short-term turn-by-turn chat history buffer**. If provided, `BaseAgent` will automatically add user/assistant messages and include the history in prompts sent to the LLM.
*   **Removed:** `tools` and `max_tool_iterations` fields are no longer part of `BaseAgentConfig`. Tool handling is managed externally.

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
        # memory_manager=memory_manager,
        # conversation_history=ConversationHistory(max_messages=10), # Add history buffer
        output_schema=MyOrchestrationOutputSchema # Example: Set output schema for tool indication
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