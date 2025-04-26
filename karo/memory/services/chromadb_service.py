import chromadb
from chromadb.config import Settings
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions
from pydantic import BaseModel, Field, SecretStr
from typing import List, Dict, Optional, Any, Protocol
import os
import logging

class EmbeddingFunction(Protocol):
    """
    A generic interface for embedding functions.
    """
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        ...

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
class ChromaDBConfig(BaseModel):
    """Configuration for the ChromaDB service."""
    host: Optional[str] = Field(None, description="Hostname for ChromaDB server (if running remotely).")
    port: Optional[int] = Field(None, description="Port for ChromaDB server (if running remotely).")
    path: Optional[str] = Field("./.karo_chroma_db", description="Path for local ChromaDB persistence.")
    collection_name: str = Field("karo_memory", description="Default collection name for memories.")
    embedding_model_name: str = Field("text-embedding-3-small", description="Name of the OpenAI embedding model.")
    openai_api_key: Optional[SecretStr] = Field(None, description="OpenAI API key for embeddings. Uses OPENAI_API_KEY env var if None.")
    embedding_function: Optional[EmbeddingFunction] = Field(None, description="A custom embedding function to use.")
    # Add other Chroma settings if needed (e.g., tenant, database)
    class Config:
        arbitrary_types_allowed = True

# --- Service ---
class ChromaDBService:
    """
    Handles interactions with a ChromaDB vector store for persistent memory.
    Manages client connection, collection access, embedding generation, and CRUD operations.
    """
    _client: Optional[chromadb.ClientAPI] = None
    _collection: Optional[Collection] = None
    _ef: Optional[embedding_functions.EmbeddingFunction] = None

    def __init__(self, config: ChromaDBConfig):
        """
        Initializes the ChromaDB service and connects to the database.

        Args:
            config: A ChromaDBConfig instance.
        """
        self.config = config
        self._initialize_client()
        self._initialize_embedding_function()
        self._get_or_create_collection()

    def _initialize_client(self):
        """Initializes the ChromaDB client (persistent or HTTP)."""
        if self._client:
            return

        try:
            if self.config.host and self.config.port:
                logger.info(f"Connecting to remote ChromaDB at {self.config.host}:{self.config.port}")
                self._client = chromadb.HttpClient(
                    host=self.config.host,
                    port=self.config.port,
                    settings=Settings(anonymized_telemetry=False) # Optional: disable telemetry
                )
            else:
                logger.info(f"Initializing persistent ChromaDB client at path: {self.config.path}")
                self._client = chromadb.PersistentClient(
                    path=self.config.path,
                    settings=Settings(anonymized_telemetry=False)
                )
            # Verify connection (e.g., by listing collections or checking heartbeat)
            self._client.heartbeat() # Raises exception if connection fails
            logger.info("ChromaDB client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}", exc_info=True)
            raise ConnectionError(f"Could not connect to ChromaDB: {e}") from e

    def _initialize_embedding_function(self):
        """Initializes the embedding function."""
        if self._ef:
            return

        if self.config.embedding_function:
            self._ef = self.config.embedding_function
            logger.info("Using provided embedding function.")
            if self.config.openai_api_key or self.config.embedding_model_name:
                logger.warning("Both embedding_function and openai_api_key/embedding_model_name are provided. Using embedding_function.")
            return

        api_key = self.config.openai_api_key.get_secret_value() if self.config.openai_api_key else os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found. Set via config or OPENAI_API_KEY environment variable.")

        try:
            self._ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name=self.config.embedding_model_name
            )
            logger.info(f"OpenAI embedding function initialized with model: {self.config.embedding_model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embedding function: {e}", exc_info=True)
            raise ValueError(f"Could not initialize OpenAI embedding function: {e}. Ensure OPENAI_API_KEY is set correctly.") from e

    def _get_or_create_collection(self) -> Collection:
        """Gets or creates the ChromaDB collection."""
        if self._collection:
            return self._collection
        if not self._client:
             raise ConnectionError("ChromaDB client not initialized.")
        if not self._ef:
             raise ValueError("Embedding function not initialized.")

        try:
            self._collection = self._client.get_or_create_collection(
                name=self.config.collection_name,
                embedding_function=self._ef # Pass the initialized function
                # metadata={"hnsw:space": "cosine"} # Optional: configure index settings
            )
            logger.info(f"Using ChromaDB collection: '{self.config.collection_name}'")
            return self._collection
        except Exception as e:
            logger.error(f"Failed to get or create ChromaDB collection '{self.config.collection_name}': {e}", exc_info=True)
            raise RuntimeError(f"Could not access ChromaDB collection: {e}") from e

    @property
    def collection(self) -> Collection:
        """Provides access to the initialized ChromaDB collection."""
        if not self._collection:
            return self._get_or_create_collection()
        return self._collection

    def add_memory(self, id: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Adds a single memory (document) to the collection.
        Embeddings are generated automatically by ChromaDB using the configured function.

        Args:
            id: A unique identifier for the memory.
            text: The text content of the memory.
            metadata: Optional dictionary of metadata associated with the memory.
        """
        try:
            self.collection.add(
                ids=[id],
                documents=[text],
                metadatas=[metadata] if metadata else None
            )
            logger.debug(f"Added memory with ID: {id}")
        except Exception as e:
            logger.error(f"Failed to add memory (ID: {id}): {e}", exc_info=True)
            # Optionally re-raise or handle specific ChromaDB errors

    def add_memories(self, ids: List[str], texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None):
        """
        Adds multiple memories (documents) to the collection in a batch.

        Args:
            ids: A list of unique identifiers for the memories.
            texts: A list of text contents for the memories.
            metadatas: Optional list of metadata dictionaries. Must match length of ids/texts if provided.
        """
        if metadatas and len(metadatas) != len(ids):
            raise ValueError("Length of metadatas must match length of ids and texts.")
        try:
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            logger.debug(f"Added {len(ids)} memories.")
        except Exception as e:
            logger.error(f"Failed to add batch of memories: {e}", exc_info=True)

    def query_memories(self, query_text: str, n_results: int = 5, where: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Queries the collection for memories similar to the query text.

        Args:
            query_text: The text to search for similar memories.
            n_results: The maximum number of results to return.
            where: Optional metadata filter clause (ChromaDB 'where' dictionary).

        Returns:
            A list of dictionaries, each containing 'id', 'text', 'metadata', and 'distance'
            for the matched memories, sorted by relevance (distance). Returns empty list if no results.
        """
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                include=['metadatas', 'documents', 'distances'] # Specify fields to include
            )

            # Process results into a more usable format
            processed_results = []
            # Results structure can be complex, adjust parsing as needed based on ChromaDB version
            if results and results.get('ids') and results['ids'][0]:
                for i, mem_id in enumerate(results['ids'][0]):
                    processed_results.append({
                        'id': mem_id,
                        'text': results['documents'][0][i] if results.get('documents') and results['documents'][0] else None,
                        'metadata': results['metadatas'][0][i] if results.get('metadatas') and results['metadatas'][0] else None,
                        'distance': results['distances'][0][i] if results.get('distances') and results['distances'][0] else None,
                    })
            logger.debug(f"Query returned {len(processed_results)} memories for: '{query_text[:50]}...'")
            return processed_results
        except Exception as e:
            logger.error(f"Failed to query memories: {e}", exc_info=True)
            return [] # Return empty list on error

    def get_memory_by_id(self, id: str) -> Optional[Dict[str, Any]]:
         """Gets a specific memory by its ID."""
         try:
             result = self.collection.get(ids=[id], include=['metadatas', 'documents'])
             if result and result.get('ids') and result['ids']:
                 return {
                     'id': result['ids'][0],
                     'text': result['documents'][0] if result.get('documents') else None,
                     'metadata': result['metadatas'][0] if result.get('metadatas') else None,
                 }
             return None
         except Exception as e:
             logger.error(f"Failed to get memory by ID ({id}): {e}", exc_info=True)
             return None

    def delete_memory(self, id: str):
        """Deletes a memory by its ID."""
        try:
            self.collection.delete(ids=[id])
            logger.debug(f"Deleted memory with ID: {id}")
        except Exception as e:
            logger.error(f"Failed to delete memory (ID: {id}): {e}", exc_info=True)

    def reset_database(self):
        """Resets the entire ChromaDB database (use with caution!)."""
        if not self._client:
             raise ConnectionError("ChromaDB client not initialized.")
        logger.warning("Resetting ChromaDB database...")
        self._client.reset()
        self._collection = None # Force re-creation on next access
        logger.info("ChromaDB database reset.")

    def clear_collection(self):
        """Deletes and recreates the collection, effectively clearing it."""
        if not self._client:
             raise ConnectionError("ChromaDB client not initialized.")
        if not self._collection:
            logger.info(f"Collection '{self.config.collection_name}' not initialized, nothing to clear.")
            return

        collection_name = self.config.collection_name
        logger.warning(f"Clearing ChromaDB collection: '{collection_name}'...")
        try:
            self._client.delete_collection(name=collection_name)
            self._collection = None # Force re-creation
            self._get_or_create_collection() # Recreate it immediately
            logger.info(f"Collection '{collection_name}' cleared and recreated.")
        except Exception as e:
             logger.error(f"Failed to clear collection '{collection_name}': {e}", exc_info=True)
             # Attempt to recreate just in case deletion failed partially
             self._collection = None
             self._get_or_create_collection()


# Example Usage (for testing or direct use)
if __name__ == "__main__":
    # Load .env file from root if running directly
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '../../../.env') # Adjust path as needed
    load_dotenv(dotenv_path=dotenv_path)

    # Basic configuration (uses local persistence and env var for API key)
    config = ChromaDBConfig()

    try:
        service = ChromaDBService(config=config)

        # Add some memories
        print("\nAdding memories...")
        service.add_memory(id="mem1", text="The sky is blue during the day.", metadata={"topic": "nature", "source": "common_knowledge"})
        service.add_memory(id="mem2", text="Python is a versatile programming language.", metadata={"topic": "programming", "source": "wikipedia"})
        service.add_memory(id="mem3", text="ChromaDB is a vector database.", metadata={"topic": "database", "source": "chromadb_docs"})
        print("Memories added.")

        # Query memories
        print("\nQuerying memories for 'programming language'...")
        results = service.query_memories(query_text="programming language", n_results=2)
        for res in results:
            print(f"  - ID: {res['id']}, Distance: {res['distance']:.4f}, Text: {res['text']}")

        print("\nQuerying memories for 'sky color'...")
        results_sky = service.query_memories(query_text="sky color", n_results=1)
        for res in results_sky:
            print(f"  - ID: {res['id']}, Distance: {res['distance']:.4f}, Text: {res['text']}")

        # Get by ID
        print("\nGetting memory by ID 'mem3'...")
        mem3 = service.get_memory_by_id("mem3")
        print(f"  - Found: {mem3}")

        # Delete a memory
        # print("\nDeleting memory 'mem1'...")
        # service.delete_memory("mem1")
        # print("Memory deleted.")
        # mem1_after = service.get_memory_by_id("mem1")
        # print(f"  - Memory 'mem1' after delete: {mem1_after}")

        # Clear collection (use carefully)
        # print("\nClearing collection...")
        # service.clear_collection()
        # print("Collection cleared.")
        # results_after_clear = service.query_memories(query_text="database", n_results=1)
        # print(f"  - Query results after clear: {results_after_clear}")


    except (ValueError, ConnectionError, RuntimeError) as e:
        print(f"\nAn error occurred: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")