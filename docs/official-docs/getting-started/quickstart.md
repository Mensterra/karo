# Quickstart Guide

This guide shows the basic steps to create and run a simple Karo agent after installing the framework.

## Prerequisites

*   Karo framework installed (`pip install karo`). See [Installation](./installation.md).
*   An LLM provider API key (e.g., for OpenAI) set as an environment variable (`OPENAI_API_KEY`). See [Installation](./installation.md) for setting up `.env`.
*   `python-dotenv` installed in your project (`pip install python-dotenv`).

## 1. Basic Agent Setup

Create a Python script (e.g., `my_agent_app.py`) in your project:

```python
import os
from dotenv import load_dotenv

# Load environment variables from your project's .env file
load_dotenv()

# Import necessary Karo components
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema

# --- Configuration ---

# 1. Configure the LLM Provider (e.g., OpenAI)
# Ensure OPENAI_API_KEY is set in your .env file
provider_config = OpenAIProviderConfig(model="gpt-4o-mini") # Choose your desired model
try:
    openai_provider = OpenAIProvider(config=provider_config)
    print(f"Provider Initialized: {openai_provider.get_model_name()}")
except Exception as e:
    print(f"Error initializing provider: {e}")
    exit()

# 2. Configure the Agent
# Uses the default input/output schemas and system prompt
agent_config = BaseAgentConfig(provider=openai_provider)
my_agent = BaseAgent(config=agent_config)
print("Agent Initialized.")

# --- Interaction ---

# 3. Prepare Input
user_message = "Tell me a short fact about the Karo framework."
input_data = BaseInputSchema(chat_message=user_message) # Use the agent's default input schema

# 4. Run the Agent
print(f"\nSending message: '{user_message}'")
result = my_agent.run(input_data)

# 5. Process Output
if isinstance(result, BaseOutputSchema):
    print(f"\nAgent Response: {result.response_message}")
elif isinstance(result, AgentErrorSchema):
    print(f"\nAgent Error: {result.error_type} - {result.error_message}")
else:
    print(f"\nUnexpected result type: {type(result)}")

```

## 2. Running the Script

Save the code above as `my_agent_app.py` in your project directory (where your `.env` file is located). Run it from your terminal:

```bash
python my_agent_app.py
```

You should see output indicating the provider and agent initialization, followed by the agent's response.

## 3. Adding Memory

To give your agent memory:

```python
# (Add these imports)
from karo.memory.services.chromadb_service import ChromaDBService, ChromaDBConfig
from karo.memory.memory_manager import MemoryManager

# --- Configuration ---
# ... (Provider setup as before) ...

# 2a. Initialize Memory System
# This will create a local DB in ./.karo_memory_db by default
try:
    chroma_config = ChromaDBConfig(path="./.my_project_karo_db") # Optional: specify path
    chroma_service = ChromaDBService(config=chroma_config)
    memory_manager = MemoryManager(chroma_service=chroma_service)
    print("Memory Manager Initialized.")
except Exception as e:
    print(f"Error initializing memory: {e}")
    memory_manager = None # Continue without memory if init fails

# 2b. Configure the Agent WITH Memory
agent_config = BaseAgentConfig(
    provider=openai_provider,
    memory_manager=memory_manager # Pass the manager instance
    # Optionally adjust memory_query_results or system_prompt
)
my_agent = BaseAgent(config=agent_config)
print("Agent Initialized with Memory.")

# --- Interaction ---
# ... (Prepare input and run agent as before) ...

# 5a. Store Memory (Optional - after getting a response)
if isinstance(result, BaseOutputSchema) and memory_manager:
    turn_summary = f"User: '{user_message}' | Agent: '{result.response_message}'"
    memory_id = memory_manager.add_memory(text=turn_summary, metadata={"source": "my_app"})
    if memory_id:
        print(f"(Stored memory: {memory_id})")
    else:
        print("(Failed to store memory)")

# ... (Process output as before) ...
```

Now, when you run the agent multiple times, it will retrieve relevant past interactions (stored as summaries) and use them as context.

## 4. Using Tools

To enable tools:

```python
# (Add these imports)
from karo.tools.calculator_tool import CalculatorTool
# from your_custom_tool_module import YourCustomTool # If you create one

# --- Configuration ---
# ... (Provider and Memory setup as before) ...

# 2c. Initialize Tools
calculator = CalculatorTool()
# my_custom_tool = YourCustomTool()
available_tools = [calculator] # Add any other tools here
print("Tools Initialized.")

# 2d. Configure the Agent WITH Tools (and Memory)
agent_config = BaseAgentConfig(
    provider=openai_provider,
    memory_manager=memory_manager,
    tools=available_tools # Pass the list of tool instances
    # Adjust system prompt to mention tools
)
my_agent = BaseAgent(config=agent_config)
print("Agent Initialized with Memory and Tools.")

# --- Interaction ---
# ... (Prepare input) ...
user_message = "What is 75 divided by 3?"
input_data = BaseInputSchema(chat_message=user_message)

# ... (Run agent and process output as before) ...
# The agent should now use the calculator tool automatically if needed.
```

## Next Steps

*   Explore how to create [Custom Schemas](./schemas.md - *TODO*) to structure agent inputs and outputs more precisely.
*   Learn about creating [Custom Tools](./tools.md - *TODO*).
*   Dive deeper into the [Memory System](./memory.md - *TODO*).
*   Check the [API Reference](./api/index.md - *TODO*) for detailed class and method documentation.