# Memory Guide

This guide explains how to use Karo's memory management features to build agents that can remember and reason about past interactions.

## MemoryManager

The `MemoryManager` is the central component for managing an agent's memory. It provides a high-level interface for storing, retrieving, and deleting memories.

### Configuration

The `MemoryManager` is configured using a `MemoryManagerConfig` object. This object allows you to specify the type of database to use for storing memories, as well as any configuration options specific to that database.

```python
from karo.memory.memory_manager import MemoryManager, MemoryManagerConfig
from karo.memory.services.chromadb_service import ChromaDBConfig

# Configure ChromaDB
chroma_config = ChromaDBConfig(path="./my_agent_db", collection_name="my_agent_memory")

# Configure MemoryManager to use ChromaDB
memory_manager_config = MemoryManagerConfig(db_type="chromadb", chromadb_config=chroma_config)

# Initialize the MemoryManager
memory_manager = MemoryManager(config=memory_manager_config)
```

### Usage

The `MemoryManager` provides the following methods:

*   `add_memory(text: str, metadata: Dict[str, Any], memory_id: str) -> str`: Adds a new memory to the database.
*   `retrieve_relevant_memories(query_text: str, n_results: int) -> List[MemoryQueryResult]`: Retrieves memories that are relevant to the given query text.
*   `clear_memory()`: Clears all memories from the database.

## ChromaDBService

The `ChromaDBService` is a service that provides an interface for interacting with a ChromaDB vector store. It is used by the `MemoryManager` to store and retrieve memories.

### Configuration

The `ChromaDBService` is configured using a `ChromaDBConfig` object. This object allows you to specify the path to the ChromaDB database, as well as other configuration options.

```python
from karo.memory.services.chromadb_service import ChromaDBService, ChromaDBConfig

# Configure ChromaDB
chroma_config = ChromaDBConfig(path="./my_agent_db", collection_name="my_agent_memory")

# Initialize the ChromaDBService
db_service = ChromaDBService(config=chroma_config)
```

### Usage

The `ChromaDBService` provides the following methods:

*   `add_memory(id: str, text: str, metadata: Dict[str, Any])`: Adds a new memory to the database.
*   `query_memories(query_text: str, n_results: int, where: Dict) -> List[Dict]`: Queries the database for memories that are relevant to the given query text.
*   `reset_database()`: Resets the entire ChromaDB database (use with caution!).
*   `clear_collection()`: Deletes and recreates the collection, effectively clearing it.

## Ingestion (Offline Step)

*   First, you need to populate the memory store (ChromaDB) with your knowledge base documents (e.g., FAQs, policies, product manuals).
*   This typically involves a separate script, which you can create by inheriting from `karo/utils/base_ingestion_script.py`. This base script provides a template for:
    *   Loading environment variables (e.g., OPENAI\_API\_KEY).
    *   Initializing ChromaDBService and MemoryManager.
    *   Using DocumentReaderTool to read files from a directory.
    *   Basic chunking strategy.
    *   Adding document chunks to the MemoryManager with metadata.
*   To create your own ingestion script:
    1.  Copy `karo/utils/base_ingestion_script.py` to your project (e.g., into a 'scripts' directory).
    2.  Modify the CONFIGURATION section to point to your knowledge base directory, database path, and collection name.
    3.  Customize the chunking strategy and metadata as needed.
    4.  Ensure necessary dependencies are installed (karo, python-dotenv, pypdf, python-docx).
    5.  Set your OPENAI\_API\_KEY (or other provider key) in a .env file accessible from where you run the script.
    6.  Run the script: `python path/to/your/copied_ingestion_script.py`
*   During storage, the `ChromaDBService` automatically uses its configured embedding function (defaulting to OpenAI's `text-embedding-3-small`) to create a vector embedding for each chunk. The text, metadata, and embedding are stored together in ChromaDB.
*   This ingestion process only needs to be run once initially and then again whenever your knowledge base documents change.

## Memory Models

The `karo.memory.memory_models` module defines the data models used for representing memories.

### MemoryQueryResult

The `MemoryQueryResult` class represents a single memory that is retrieved from the database. It contains the following attributes:

*   `id: str`: The ID of the memory.
*   `text: str`: The text content of the memory.
*   `metadata: Dict[str, Any]`: The metadata associated with the memory.
*   `similarity: float`: The similarity score between the query text and the memory.