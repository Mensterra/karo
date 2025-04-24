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

## 4. Using Tools (Refactored Approach)

Tool usage now involves external orchestration based on the agent's output.

```python
# (Add these imports)
from karo.tools.calculator_tool import CalculatorTool, CalculatorInput
from typing import Union, Optional # For the orchestration schema
from karo.schemas.base_schemas import BaseOutputSchema # For the orchestration schema
from pydantic import Field # For the orchestration schema

# Define an output schema for the agent to indicate tool use
class OrchestrationOutputSchema(BaseOutputSchema):
    tool_name: Optional[str] = Field(None, description="The name of the tool to execute (e.g., 'calculator').")
    tool_parameters: Optional[Union[CalculatorInput]] = Field(None, description="The input parameters for the selected tool.")
    direct_response: Optional[str] = Field(None, description="Direct response if no tool needed.")
    # Add validation logic if needed

# --- Configuration ---
# ... (Provider and Memory setup as before) ...

# 2c. Initialize Tools
calculator = CalculatorTool()
available_tools = {calculator.get_name(): calculator} # Store in a dict
print("Tools Initialized.")

# 2d. Configure the Agent for Orchestration
agent_config = BaseAgentConfig(
    provider=openai_provider,
    memory_manager=memory_manager,
    output_schema=OrchestrationOutputSchema, # Set the orchestration schema
    # Adjust system prompt to instruct agent on using the OrchestrationOutputSchema format
    # e.g., "If you need to calculate, respond with tool_name='calculator' and the required tool_parameters..."
)
my_agent = BaseAgent(config=agent_config)
# Update system prompt if not done via builder in config
# my_agent.prompt_builder.role_description = "..."
print("Agent Initialized for Orchestration.")

# --- Interaction ---
user_message = "What is 75 divided by 3?"
input_data = BaseInputSchema(chat_message=user_message) # Agent's input schema

print(f"\nSending message: '{user_message}'")
agent_output = my_agent.run(input_data)

# 5. Process Output and Execute Tool Externally
if isinstance(agent_output, OrchestrationOutputSchema):
    if agent_output.tool_name and agent_output.tool_parameters:
        tool_to_run = available_tools.get(agent_output.tool_name)
        if tool_to_run and agent_output.tool_name == "calculator":
            print(f"Agent requested tool: {agent_output.tool_name}")
            try:
                # Ensure parameters are correct type (should be handled by Pydantic/Instructor)
                if isinstance(agent_output.tool_parameters, CalculatorInput):
                    tool_result = tool_to_run.run(agent_output.tool_parameters)
                    print(f"Tool Result ({agent_output.tool_name}): {tool_result}")
                    # You might want to display tool_result.result specifically
                    if tool_result.success:
                         print(f"Calculation Result: {tool_result.result}")
                    else:
                         print(f"Calculation Error: {tool_result.error_message}")
                else:
                    print("Error: Agent provided incorrect parameter type for calculator.")
            except Exception as e:
                print(f"Error running tool {agent_output.tool_name}: {e}")
        elif tool_to_run:
             print(f"Error: Handling for tool '{agent_output.tool_name}' not implemented in this example.")
        else:
            print(f"Error: Agent requested unknown tool '{agent_output.tool_name}'")
    elif agent_output.direct_response:
        print(f"\nAgent Response: {agent_output.direct_response}")
    else:
        print("\nAgent returned no specific action.")

elif isinstance(agent_output, AgentErrorSchema):
    print(f"\nAgent Error: {agent_output.error_type} - {agent_output.error_message}")
else:
    print(f"\nUnexpected result type: {type(agent_output)}")

```

## Next Steps

*   Explore how to create [Custom Schemas](./schemas.md - *TODO*) to structure agent inputs and outputs more precisely.
*   Learn about creating [Custom Tools](./tools.md - *TODO*).
*   Dive deeper into the [Memory System](./memory.md - *TODO*).
*   Check the [API Reference](./api/index.md - *TODO*) for detailed class and method documentation.