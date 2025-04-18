# Karo Framework - Memory System

This directory contains components related to providing persistent memory capabilities to Karo agents. The goal is to allow agents to store, retrieve, and utilize information from past interactions or external knowledge sources.

## Architecture

The memory system is composed of several parts:

1.  **`services/`**: Contains low-level service integrations for the actual memory storage backend.
    *   **`chromadb_service.py`**: Implements the connection, embedding generation, and CRUD operations for a ChromaDB vector store. It handles the direct interaction with the database.

2.  **`memory_models.py`**: Defines Pydantic models for structuring memory data.
    *   **`MemoryRecord`**: Represents a single piece of information stored in memory, including text, metadata (like timestamps, source), and potentially an importance score.
    *   **`MemoryQueryResult`**: Wraps a `MemoryRecord` along with its relevance score (distance) when retrieved from a query.

3.  **`tools/`**: Provides higher-level, tool-like interfaces for memory operations, suitable for being called by an agent's reasoning process (if using a tool-using agent architecture).
    *   **`memory_store_tool.py`**: A tool to add a new memory record.
    *   **`memory_query_tool.py`**: A tool to query for relevant memories based on text similarity.

4.  **`memory_manager.py`**:
    *   **`MemoryManager`**: Acts as the primary interface for agents to interact with the memory system. It orchestrates calls to the underlying service (like `ChromaDBService`) or memory tools. It simplifies adding and retrieving memories for the agent. Future enhancements could include logic for automatic memory summarization, importance weighting, or deciding *what* to store.

## How it Integrates with `BaseAgent`

*   The `BaseAgentConfig` can optionally accept an instance of `MemoryManager`.
*   If a `MemoryManager` is provided, the `BaseAgent`'s `run` method will:
    1.  Use the `MemoryManager` to retrieve memories relevant to the current user input *before* calling the LLM.
    2.  Format these retrieved memories (e.g., as part of the system prompt or a dedicated context section) to provide context to the LLM.
*   Storing memories is typically handled *after* an interaction, potentially by a dedicated step in an agent's workflow or by a separate "memory formation" agent/process that analyzes the conversation turn. The `MemoryManager` (or `MemoryStoreTool`) provides the mechanism for this storage.

This setup allows agents to leverage past information stored in ChromaDB to generate more contextually relevant and informed responses.