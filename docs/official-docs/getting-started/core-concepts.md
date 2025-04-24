# Core Concepts

Understanding these core concepts is key to effectively using the Karo framework.

## 1. Agent (`BaseAgent`)

*   **What it is:** The central orchestrator. It takes user input, interacts with LLMs, uses tools, accesses memory, and generates responses.
*   **Configuration (`BaseAgentConfig`):** Defines the agent's behavior, including which LLM provider, memory system, and prompt builder to use.
*   **Interaction:** The `run` method now accepts external conversation `history` and `state` dictionaries, allowing for session management outside the agent itself.
*   **Key Idea:** Encapsulates the main reasoning loop, now decoupled from internal history management.

## 2. Provider (`BaseProvider`)

*   **What it is:** An abstraction layer for interacting with different Large Language Models (LLMs).
*   **Implementation (`OpenAIProvider`):** Karo includes an implementation for OpenAI models. Others can be added.
*   **Key Idea:** Makes the agent LLM-agnostic. You configure the agent with a specific provider instance.

## 3. Schema (`BaseInputSchema`, `BaseOutputSchema`, Pydantic)

*   **What it is:** Defines the expected structure and data types for inputs and outputs (for agents, tools, etc.) using Pydantic models.
*   **Benefits:** Ensures data validation, provides clear interfaces, and helps guide the LLM's output format (when used with `instructor`).
*   **Key Idea:** Structured data flow and validation.

## 4. Tool (`BaseTool`)

*   **What it is:** A reusable component that performs a specific action (e.g., calculation, database lookup, web search, file reading).
*   **Structure:** Tools inherit from `BaseTool` and define their own input/output schemas and execution logic (`run` method).
*   **Usage:** Tools are instantiated in the application logic. The agent is configured with an output schema that allows it to *indicate* which tool to use and the necessary parameters. External logic receives the agent's output, interprets the tool request, and executes the appropriate tool's `run` method.
*   **Key Idea:** Extends agent capabilities beyond the LLM's inherent knowledge.

## 5. Memory (`MemoryManager`, `ChromaDBService`)

*   **What it is:** Allows agents to store and retrieve information persistently, typically using a vector database like ChromaDB for semantic search.
*   **Components:**
    *   `ChromaDBService`: Handles direct interaction with the ChromaDB database.
    *   `MemoryManager`: Provides a higher-level interface for the agent to add and retrieve memories.
*   **Usage (RAG):** Often used for Retrieval-Augmented Generation (RAG), where relevant information from the memory store (e.g., a knowledge base) is retrieved and added to the LLM prompt as context.
*   **Key Idea:** Gives agents long-term context and access to external knowledge.

## 6. Prompt Builder (`SystemPromptBuilder`)

*   **What it is:** A helper class for constructing complex system prompts dynamically.
*   **Structure:** Manages distinct sections (role, guidelines, tools, memory, security, etc.) and allows customization of content, order, and headers.
*   **Usage:** The `BaseAgent` uses the builder to assemble the final system prompt sent to the LLM, incorporating dynamic information like available tools and retrieved memories.
*   **Key Idea:** Flexible, maintainable, and more secure prompt engineering.


## 7. Session Management (`BaseSession`, `BaseEvent`, `BaseSessionService`)

*   **What it is:** A system for maintaining conversation context (history) and state across multiple interactions with an agent, typically used within the server environment.
*   **Components:**
    *   `BaseEvent`: Represents a single turn (user message or assistant response).
    *   `BaseSession`: Holds a list of `BaseEvent`s and an arbitrary `state` dictionary for a specific conversation.
    *   `BaseSessionService`: Defines the interface for storing and retrieving sessions (e.g., `InMemorySessionService`).
*   **Usage:** The FastAPI server uses a session service to load/save sessions, passing the relevant `history` and `state` to the `BaseAgent.run` method on each `/invoke` call.
*   **Key Idea:** Enables multi-turn conversations and stateful interactions.

Understanding how these components interact is fundamental to building applications with Karo. Refer to the specific guides for more in-depth information on each concept.