import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid # Import uuid module
from karo.memory.memory_models import MemoryQueryResult, MemoryRecord
from karo.memory.services.chromadb_service import ChromaDBConfig, ChromaDBService
from pydantic import BaseModel, Field # Import BaseModel and Field


logger = logging.getLogger(__name__)

# --- Configuration Model ---
class MemoryManagerConfig(BaseModel):
    """Configuration for MemoryManager."""
    # Currently only supports ChromaDB, add type discriminator if more are added
    db_type: str = Field("chromadb", description="Type of database service to use.")
    chromadb_config: ChromaDBConfig = Field(..., description="Configuration for ChromaDBService.")
    # Add other DB type configs here using Union if needed later

# --- Memory Manager Class ---
class MemoryManager:
    """
    Manages the agent's persistent memory operations.
    Acts as an interface to the underlying memory storage and retrieval service (e.g., ChromaDBService).
    Future versions might include logic for deciding what/when to store/retrieve.
    """
    db_service: ChromaDBService # Type hint for the instantiated service

    def __init__(self, config: MemoryManagerConfig):
        """
        Initializes the MemoryManager based on configuration.

        Args:
            config: An instance of MemoryManagerConfig.
        """
        self.config = config
        if config.db_type.lower() == "chromadb":
            # Instantiate the service based on the config object
            self.db_service = ChromaDBService(config=config.chromadb_config)
            logger.info(f"MemoryManager initialized with ChromaDBService (Path: {config.chromadb_config.path}, Collection: {config.chromadb_config.collection_name}).")
        else:
            # Handle other potential db_types here
            raise ValueError(f"Unsupported db_type in MemoryManagerConfig: {config.db_type}")

    def add_memory(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        memory_id: Optional[str] = None,
        importance_score: Optional[float] = None
    ) -> Optional[str]:
        """
        Adds a memory to the persistent store.

        Args:
            text: The content of the memory.
            metadata: Optional metadata dictionary.
            memory_id: Optional specific ID for the memory. If None, generated automatically.
            importance_score: Optional importance score.

        Returns:
            The ID of the stored memory, or None if storage failed.
        """
        try:
            # 1. Generate ID if not provided
            mem_id = memory_id if memory_id is not None else str(uuid.uuid4())

            # 2. Prepare metadata dictionary
            metadata_to_store = metadata.copy() if metadata else {}

            # 3. Add timestamp and importance score
            metadata_to_store['created_at'] = datetime.now().isoformat() # Consider timezone.utc later
            if importance_score is not None:
                 metadata_to_store['importance_score'] = importance_score

            # 4. Call the service method directly
            self.db_service.add_memory(
                id=mem_id,
                text=text,
                metadata=metadata_to_store
            )
            logger.info(f"Memory added via MemoryManager with ID: {mem_id}")
            return mem_id # Return the definite ID
        except Exception as e:
            logger.error(f"MemoryManager failed to add memory: {e}", exc_info=True)
            return None

    def retrieve_relevant_memories(
        self,
        query_text: str,
        n_results: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[MemoryQueryResult]:
        """
        Retrieves memories relevant to a given query text.

        Args:
            query_text: The text to search for similar memories.
            n_results: The maximum number of results.
            where_filter: Optional metadata filter for the query.

        Returns:
            A list of MemoryQueryResult objects, sorted by relevance.
        """
        try:
            raw_results = self.db_service.query_memories(
                query_text=query_text,
                n_results=n_results,
                where=where_filter
            )

            # Process results into MemoryQueryResult objects
            processed_results = []
            for res in raw_results:
                try:
                    # Reconstruct MemoryRecord
                    record = MemoryRecord(
                        id=res.get('id'),
                        text=res.get('text'),
                        metadata=res.get('metadata', {}),
                        timestamp=datetime.fromisoformat(res['metadata']['created_at']) if res.get('metadata') and 'created_at' in res['metadata'] else datetime.utcnow(),
                        importance_score=res['metadata'].get('importance_score') if res.get('metadata') else None
                    )
                    query_result = MemoryQueryResult(
                        record=record,
                        distance=res.get('distance')
                    )
                    processed_results.append(query_result)
                except Exception as parse_err:
                    logger.warning(f"Skipping memory result due to parsing error: {parse_err} - Data: {res}", exc_info=True)


            logger.info(f"MemoryManager retrieved {len(processed_results)} memories for query: '{query_text[:50]}...'")
            return processed_results

        except Exception as e:
            logger.error(f"MemoryManager failed to retrieve memories: {e}", exc_info=True)
            return []

    def get_memory_by_id(self, memory_id: str) -> Optional[MemoryRecord]:
        """Gets a specific memory by its ID."""
        try:
            # Try getting the raw result from the service
            raw_result = self.db_service.get_memory_by_id(memory_id)
        except Exception as service_err:
            # Handle errors during the service call
            logger.error(f"MemoryManager failed to get memory by ID ({memory_id}) from service: {service_err}", exc_info=True)
            return None

        # If service call succeeded, proceed with parsing
        if raw_result:
            try:
                # Try parsing the raw result into a MemoryRecord
                record = MemoryRecord(
                    id=raw_result.get('id'),
                    text=raw_result.get('text'),
                    metadata=raw_result.get('metadata', {}),
                    # Consider using timezone.utc if available/appropriate
                    timestamp=datetime.fromisoformat(raw_result['metadata']['created_at']) if raw_result.get('metadata') and 'created_at' in raw_result['metadata'] else datetime.utcnow(),
                    importance_score=raw_result['metadata'].get('importance_score') if raw_result.get('metadata') else None
                )
                return record
            except Exception as parse_err:
                # Handle errors during parsing
                logger.warning(f"Failed to parse memory record from get_memory_by_id: {parse_err} - Data: {raw_result}", exc_info=True)
                return None
        else:
            # Handle case where service call succeeded but memory was not found
            logger.debug(f"Memory with ID {memory_id} not found.")
            return None

    def delete_memory(self, memory_id: str):
        """Deletes a memory by its ID."""
        self.db_service.delete_memory(memory_id)
        logger.info(f"MemoryManager deleted memory with ID: {memory_id}")


# Example Usage (for testing)
if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    # Load .env file from root
    dotenv_path = os.path.join(os.path.dirname(__file__), '../../../.env') # Adjust path
    load_dotenv(dotenv_path=dotenv_path)

    # Basic configuration for ChromaDBService
    chroma_config = ChromaDBConfig() # Uses defaults

    try:
        # Create MemoryManager config
        mem_config = MemoryManagerConfig(chromadb_config=chroma_config)
        # Instantiate manager using the config
        manager = MemoryManager(config=mem_config)

        # --- Test Adding Memory ---
        print("\n--- Testing Add Memory ---")
        mem_id = manager.add_memory(
            text="The MemoryManager provides an interface.",
            metadata={"component": "MemoryManager", "status": "testing"},
            importance_score=0.7
        )
        print(f"Added memory with ID: {mem_id}")
        assert mem_id is not None

        # --- Test Retrieving Memory ---
        print("\n--- Testing Retrieve Memory ---")
        query = "What does the MemoryManager do?"
        results = manager.retrieve_relevant_memories(query_text=query, n_results=1)
        print(f"Retrieved {len(results)} memories for query: '{query}'")
        if results:
            print(f"  - Top Result ID: {results[0].record.id}")
            print(f"  - Top Result Text: {results[0].record.text}")
            print(f"  - Top Result Distance: {results[0].distance:.4f}")
            print(f"  - Top Result Metadata: {results[0].record.metadata}")
            assert results[0].record.id == mem_id

        # --- Test Get By ID ---
        print("\n--- Testing Get By ID ---")
        retrieved_record = manager.get_memory_by_id(mem_id)
        print(f"Retrieved record by ID: {retrieved_record}")
        assert retrieved_record is not None
        assert retrieved_record.id == mem_id
        assert retrieved_record.metadata.get("component") == "MemoryManager"

        # --- Test Deleting Memory ---
        # print("\n--- Testing Delete Memory ---")
        # manager.delete_memory(mem_id)
        # print(f"Deleted memory: {mem_id}")
        # retrieved_after_delete = manager.get_memory_by_id(mem_id)
        # print(f"Record after delete: {retrieved_after_delete}")
        # assert retrieved_after_delete is None


    except Exception as e:
        print(f"\nAn error occurred during example execution: {e}")