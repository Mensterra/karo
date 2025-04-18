# Karo Framework

[![PyPI version](https://badge.fury.io/py/karo.svg)](https://badge.fury.io/py/karo) <!-- Placeholder badge -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) <!-- Placeholder badge -->

Karo is a modular Python framework designed for building robust and maintainable AI agent applications. It emphasizes:

*   **Modularity:** Construct agents from reusable components (core logic, memory, tools).
*   **Predictability:** Define clear agent interactions using Pydantic schemas.
*   **Memory:** Equip agents with persistent memory using vector stores like ChromaDB.
*   **Extensibility:** Easily integrate various LLM providers and custom tools.
*   **Control:** Maintain fine-grained control over agent behavior and data flow.

Inspired by frameworks like Atomic Agents, Karo aims to provide developers with the building blocks needed for creating sophisticated, reliable AI agents.

## Key Features

*   **Schema-Driven Development:** Use Pydantic for defining agent inputs, outputs, and tool parameters.
*   **Provider Abstraction:** Pluggable interface for different LLM providers (OpenAI included).
*   **Persistent Memory:** Built-in `MemoryManager` using `ChromaDBService` for storing and retrieving relevant context.
*   **Tool Integration:** Define and integrate custom tools for agents to use.
*   **Pythonic Control Flow:** All agent logic and orchestration is written in Python.

## Installation

```bash
pip install karo
```
*(Note: Replace `karo` with the actual package name if different)*

See the full [Installation Guide](./docs/installation.md) for details on setting up dependencies and environment variables (like `OPENAI_API_KEY`).

## Quickstart

Here's a minimal example of creating a basic agent:

```python
import os
from dotenv import load_dotenv
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema

# Load API keys from .env file in your project root
load_dotenv()

# Configure provider (requires OPENAI_API_KEY in .env)
provider_config = OpenAIProviderConfig(model="gpt-4o-mini")
provider = OpenAIProvider(config=provider_config)

# Configure agent
agent_config = BaseAgentConfig(provider=provider)
agent = BaseAgent(config=agent_config)

# Run agent
input_data = BaseInputSchema(chat_message="Explain the concept of AI agents briefly.")
result = agent.run(input_data)

if isinstance(result, BaseOutputSchema):
    print(f"Agent: {result.response_message}")
else:
    print(f"Error: {result.error_message}")
```

For more detailed examples, including memory and tool usage, check out the [Quickstart Guide](./docs/quickstart.md).

## Documentation

Full documentation, including guides and API references, can be found in the `docs/` directory (or at the hosted documentation site - *link TBD*).

*   [Installation](./docs/installation.md)
*   [Quickstart Guide](./docs/quickstart.md)
*   *(More guides coming soon)*

## Contributing

Contributions are welcome! Please see the [Contributing Guidelines](./CONTRIBUTING.md) for more information.

## License

Karo is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.