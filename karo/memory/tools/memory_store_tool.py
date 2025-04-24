from pydantic import Field
from typing import Optional, Dict, Any, Type # Added Type
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import uuid # Import uuid

# Import BaseTool components
from karo.tools.base_tool import BaseTool, BaseToolInputSchema, BaseToolOutputSchema

from karo.memory.services.chromadb_service import ChromaDBService

logger = logging.getLogger(__name__)

# --- Tool Schemas ---

class MemoryStoreInput(BaseToolInputSchema): # Inherit from base
    """Input schema for the MemoryStoreTool."""
    memory_text: str = Field(..., description="The text content of the memory to store.")
    memory_id: Optional[str] = Field(None, description="Optional unique ID for the memory. If None, one will be generated.")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata associated with the memory.")
    importance_score: Optional[float] = Field(None, description="Optional importance score for the memory.")

class MemoryStoreOutput(BaseToolOutputSchema): # Inherit from base
    """Output schema for the MemoryStoreTool."""
    memory_id: Optional[str] = Field(None, description="The ID of the stored memory (generated if not provided).")
    # success and error_message are inherited

# --- Tool Implementation ---

class MemoryStoreTool(BaseTool): # Inherit from BaseTool
    """
    A tool for storing memories in the persistent memory system (ChromaDB).
    Takes memory text and optional metadata/ID, adds it to the vector store.
    """
    # --- Class attributes ---
    input_schema: Type[MemoryStoreInput] = MemoryStoreInput
    output_schema: Type[MemoryStoreOutput] = MemoryStoreOutput
    name: str = "memory_store"
    description: str = "Stores a piece of text (memory) in the persistent memory database, optionally with metadata and an importance score."

    # Keep track of the service instance
    chroma_service: ChromaDBService

    def __init__(self, config: Optional[Dict[str, Any]] = None, chroma_service: Optional[ChromaDBService] = None):
        """
        Initializes the MemoryStoreTool.

        Requires a ChromaDBService instance. Can be passed via config dict
        with key 'chroma_service' or directly as a keyword argument.

        Args:
            config: Optional configuration dictionary. Expected key: 'chroma_service'.
            chroma_service: Optional direct instance of ChromaDBService.
        """
        service = None
        if chroma_service:
            service = chroma_service
        elif config and 'chroma_service' in config:
            service = config['chroma_service']

        if not isinstance(service, ChromaDBService):
            raise ValueError("MemoryStoreTool requires an initialized ChromaDBService instance passed via config or keyword argument.")

        self.chroma_service = service
        logger.info("MemoryStoreTool initialized.")

    def run(self, input_data: MemoryStoreInput) -> MemoryStoreOutput:
        """
        Executes the memory storage operation.

        Args:
            input_data: An instance of MemoryStoreInput.

        Returns:
            An instance of MemoryStoreOutput indicating success or failure.
        """
        if not isinstance(input_data, self.input_schema):
            # This validation might be redundant if the calling agent already validates
            logger.error(f"Invalid input type for MemoryStoreTool: {type(input_data)}")
            return self.output_schema(success=False, error_message="Invalid input data format.")

        try:
            # 1. Generate ID if not provided
            mem_id = input_data.memory_id if input_data.memory_id is not None else str(uuid.uuid4())

            # 2. Prepare metadata dictionary
            metadata_to_store = input_data.metadata.copy() if input_data.metadata else {}

            # 3. Add timestamp and importance score
            metadata_to_store['created_at'] = datetime.now().isoformat() # Consider timezone.utc later
            if input_data.importance_score is not None:
                 metadata_to_store['importance_score'] = input_data.importance_score

            # 4. Call the service method directly
            self.chroma_service.add_memory(
                id=mem_id,
                text=input_data.memory_text,
                metadata=metadata_to_store
            )

            logger.info(f"Successfully stored memory with ID: {mem_id}")
            return self.output_schema(success=True, memory_id=mem_id)

        except Exception as e:
            logger.error(f"Failed to store memory: {e}", exc_info=True)
            return self.output_schema(success=False, memory_id=input_data.memory_id, error_message=str(e))

# Example Usage (for testing)
if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    # Load .env file from root
    dotenv_path = os.path.join(os.path.dirname(__file__), '../../../../.env') # Adjust path
    load_dotenv(dotenv_path=dotenv_path)

    # Basic configuration for ChromaDBService
    from karo.memory.services.chromadb_service import ChromaDBConfig
    chroma_config = ChromaDBConfig() # Uses defaults (local path, env var for key)

    try:
        service = ChromaDBService(config=chroma_config)
        store_tool = MemoryStoreTool(chroma_service=service)

        # --- Test Case 1: Simple memory ---
        print("\n--- Test Case 1: Simple Memory ---")
        input1 = MemoryStoreInput(memory_text="The first test memory.")
        output1 = store_tool.run(input1)
        print(f"Output 1: {output1}")
        assert output1.success
        assert output1.memory_id is not None

        # --- Test Case 2: Memory with metadata and ID ---
        print("\n--- Test Case 2: Memory with Metadata & ID ---")
        test_id = "custom-mem-id-123"
        input2 = MemoryStoreInput(
            memory_id=test_id,
            memory_text="A memory with custom ID and metadata.",
            metadata={"source": "test_case_2", "priority": 5},
            importance_score=0.8
        )
        output2 = store_tool.run(input2)
        print(f"Output 2: {output2}")
        assert output2.success
        assert output2.memory_id == test_id

        # Verify storage (optional)
        print("\nVerifying storage...")
        retrieved1 = service.get_memory_by_id(output1.memory_id)
        retrieved2 = service.get_memory_by_id(output2.memory_id)
        print(f"Retrieved mem 1: {retrieved1}")
        print(f"Retrieved mem 2: {retrieved2}")
        assert retrieved1 is not None
        assert retrieved2 is not None
        assert retrieved2['metadata'].get('source') == 'test_case_2'
        assert retrieved2['metadata'].get('importance_score') == 0.8

    except Exception as e:
        print(f"\nAn error occurred during example execution: {e}")