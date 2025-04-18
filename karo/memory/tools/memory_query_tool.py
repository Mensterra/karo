from pydantic import Field
from typing import Optional, Dict, Any, List, Type
from datetime import datetime, timezone
import logging

# Import BaseTool components
from karo.tools.base_tool import BaseTool, BaseToolInputSchema, BaseToolOutputSchema

from karo.memory.services.chromadb_service import ChromaDBService
from karo.memory.memory_models import MemoryRecord, MemoryQueryResult # Use models for structure

logger = logging.getLogger(__name__)

# --- Tool Schemas ---

class MemoryQueryInput(BaseToolInputSchema): # Inherit from base
    """Input schema for the MemoryQueryTool."""
    query_text: str = Field(..., description="The text to search for similar memories.")
    n_results: int = Field(default=5, description="The maximum number of results to return.", gt=0)
    where_filter: Optional[Dict[str, Any]] = Field(None, description="Optional ChromaDB 'where' filter for metadata.")
    # Could add where_document filter later if needed

class MemoryQueryOutput(BaseToolOutputSchema): # Inherit from base
    """Output schema for the MemoryQueryTool."""
    results: List[MemoryQueryResult] = Field(default_factory=list, description="List of retrieved memory results, sorted by relevance.")
    # success and error_message are inherited

# --- Tool Implementation ---

class MemoryQueryTool(BaseTool): # Inherit from BaseTool
    """
    A tool for querying relevant memories from the persistent memory system (ChromaDB).
    Takes a query text and returns semantically similar memories.
    """
    # --- Class attributes ---
    input_schema: Type[MemoryQueryInput] = MemoryQueryInput
    output_schema: Type[MemoryQueryOutput] = MemoryQueryOutput
    name: str = "memory_query"
    description: str = "Queries the persistent memory database for information relevant to the query text, optionally filtering by metadata."

    # Keep track of the service instance
    chroma_service: ChromaDBService

    def __init__(self, config: Optional[Dict[str, Any]] = None, chroma_service: Optional[ChromaDBService] = None):
        """
        Initializes the MemoryQueryTool.

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
            raise ValueError("MemoryQueryTool requires an initialized ChromaDBService instance passed via config or keyword argument.")

        self.chroma_service = service
        logger.info("MemoryQueryTool initialized.")

    def run(self, input_data: MemoryQueryInput) -> MemoryQueryOutput:
        """
        Executes the memory query operation.

        Args:
            input_data: An instance of MemoryQueryInput.

        Returns:
            An instance of MemoryQueryOutput containing the results or an error.
        """
        if not isinstance(input_data, self.input_schema):
            logger.error(f"Invalid input type for MemoryQueryTool: {type(input_data)}")
            return self.output_schema(success=False, error_message="Invalid input data format.")

        try:
            # Query ChromaDB via the service
            raw_results = self.chroma_service.query_memories(
                query_text=input_data.query_text,
                n_results=input_data.n_results,
                where=input_data.where_filter
            )

            # Process results into MemoryQueryResult objects
            processed_results = []
            for res in raw_results:
                 try: # Add inner try-except for parsing individual records
                     # Reconstruct MemoryRecord from the result dictionary
                     timestamp_str = res.get('metadata', {}).get('created_at')
                     # Use timezone-aware UTC time
                     timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now(timezone.utc)

                     record = MemoryRecord(
                         id=res.get('id'),
                         text=res.get('text'),
                         metadata=res.get('metadata', {}),
                         timestamp=timestamp,
                         importance_score=res.get('metadata', {}).get('importance_score')
                     )
                     query_result = MemoryQueryResult(
                         record=record,
                         distance=res.get('distance'),
                         # Calculate similarity if needed (e.g., for cosine distance)
                         # similarity_score = 1 - res.get('distance') if res.get('distance') is not None else None
                     )
                     processed_results.append(query_result)
                 except Exception as parse_err:
                      logger.warning(f"Skipping memory result due to parsing error: {parse_err} - Data: {res}", exc_info=True)


            logger.info(f"Query '{input_data.query_text[:50]}...' returned {len(processed_results)} results.")
            return self.output_schema(success=True, results=processed_results)

        except Exception as e:
            logger.error(f"Failed to query memories: {e}", exc_info=True)
            return self.output_schema(success=False, error_message=str(e))

# Example Usage (for testing)
if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    # from datetime import datetime # Already imported above

    # Load .env file from root
    dotenv_path = os.path.join(os.path.dirname(__file__), '../../../../.env') # Adjust path
    load_dotenv(dotenv_path=dotenv_path)

    # Basic configuration for ChromaDBService
    from karo.memory.services.chromadb_service import ChromaDBConfig
    chroma_config = ChromaDBConfig() # Uses defaults

    try:
        service = ChromaDBService(config=chroma_config)
        query_tool = MemoryQueryTool(chroma_service=service)

        # --- Pre-populate some data (assuming MemoryStoreTool example ran or similar data exists) ---
        print("Ensuring some data exists...")
        try:
             ts1 = datetime.now(timezone.utc).isoformat()
             ts2 = datetime.now(timezone.utc).isoformat()
             ts3 = datetime.now(timezone.utc).isoformat()
             service.add_memory(id="query_test_1", text="Blueberries are blue.", metadata={"topic": "fruit", "color": "blue", "created_at": ts1})
             service.add_memory(id="query_test_2", text="Apples can be red or green.", metadata={"topic": "fruit", "color": "red", "created_at": ts2})
             service.add_memory(id="query_test_3", text="The Python language is powerful.", metadata={"topic": "programming", "created_at": ts3})
        except Exception as add_err:
             print(f"Note: Error adding test data (might already exist): {add_err}")


        # --- Test Case 1: General query ---
        print("\n--- Test Case 1: Query 'fruit colors' ---")
        input1 = MemoryQueryInput(query_text="fruit colors", n_results=3)
        output1 = query_tool.run(input1)
        print(f"Output 1 Success: {output1.success}")
        if output1.success:
            for res in output1.results:
                print(f"  - ID: {res.record.id}, Dist: {res.distance:.4f}, Text: {res.record.text}")
        else:
            print(f"  Error: {output1.error_message}")

        # --- Test Case 2: Query with filter ---
        print("\n--- Test Case 2: Query 'fruit' with filter {'color': 'blue'} ---")
        input2 = MemoryQueryInput(query_text="fruit", n_results=3, where_filter={"color": "blue"})
        output2 = query_tool.run(input2)
        print(f"Output 2 Success: {output2.success}")
        if output2.success:
            for res in output2.results:
                print(f"  - ID: {res.record.id}, Dist: {res.distance:.4f}, Text: {res.record.text}, Meta: {res.record.metadata}")
                assert res.record.metadata.get("color") == "blue"
        else:
            print(f"  Error: {output2.error_message}")

        # --- Test Case 3: Query for something else ---
        print("\n--- Test Case 3: Query 'programming' ---")
        input3 = MemoryQueryInput(query_text="programming", n_results=2)
        output3 = query_tool.run(input3)
        print(f"Output 3 Success: {output3.success}")
        if output3.success:
            for res in output3.results:
                print(f"  - ID: {res.record.id}, Dist: {res.distance:.4f}, Text: {res.record.text}")
        else:
            print(f"  Error: {output3.error_message}")


    except Exception as e:
        print(f"\nAn error occurred during example execution: {e}")