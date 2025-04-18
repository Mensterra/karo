# Karo Framework - Core Components

This directory contains the core engine components of the Karo framework.

## `base_agent.py`

*   **`BaseAgentConfig`**: A Pydantic model used to configure instances of `BaseAgent`. It defines essential parameters like the LLM client (expected to be patched by `instructor`), the model name, input/output schemas, and the system prompt.
*   **`BaseAgent`**: The fundamental agent class. It orchestrates the interaction with the language model based on its configuration.
    *   It takes an input conforming to its `input_schema`.
    *   It interacts with the configured LLM provider (via the `client` in its config).
    *   It uses `instructor` (implicitly, through the patched client) to ensure the LLM's response conforms to the specified `output_schema`.
    *   It handles basic input validation and error reporting using `AgentErrorSchema`.

### Basic Usage (Conceptual - Full example in `/examples`)

```python
# Assuming necessary imports and setup
import instructor
import openai
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.schemas.base_schemas import BaseInputSchema # Or a custom input schema

# 1. Configure the agent
client = instructor.from_openai(openai.OpenAI()) # Replace with actual setup
agent_config = BaseAgentConfig(
    client=client,
    model="gpt-4o-mini" # Or your desired model
    # Optionally override input/output schemas, system_prompt, etc.
)

# 2. Initialize the agent
agent = BaseAgent(config=agent_config)

# 3. Prepare input data
input_data = BaseInputSchema(chat_message="Hello, Karo!")

# 4. Run the agent
result = agent.run(input_data)

# 5. Process the result
if isinstance(result, agent.config.output_schema):
    print(f"Agent Response: {result.response_message}")
elif isinstance(result, AgentErrorSchema):
    print(f"Agent Error: {result.error_type} - {result.error_message}")

```

*(Note: The actual LLM interaction logic within `BaseAgent.run` is currently a placeholder and will be fully implemented during the Provider Abstraction phase.)*