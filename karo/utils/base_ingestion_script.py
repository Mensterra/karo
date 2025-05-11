
import logging

from abc import ABC, abstractmethod
from typing import List, Dict, Any

# Abstract base class for ingestion scripts
class BaseIngestionScript(ABC):
    """
    Abstract base class for ingestion scripts.
    """

    def __init__(self, kb_dir: str, chroma_db_path: str, collection_name: str, dotenv_path: str, openai_api_key: str):
        self.kb_dir = kb_dir
        self.chroma_db_path = chroma_db_path
        self.collection_name = collection_name
        self.dotenv_path = dotenv_path
        self.openai_api_key = openai_api_key
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def load_data(self) -> List[Dict[str, Any]]:
        """Abstract method to load data from a source (e.g., JSON, CSV)."""
        pass

    @abstractmethod
    def process_data(self, data: List[Dict[str, Any]]):
        """Abstract method to process the loaded data and prepare it for ingestion."""
        pass

    @abstractmethod
    def ingest_data(self):
        """Abstract method to ingest the processed data into the ChromaDB."""
        pass

    def run(self):
        """Runs the ingestion process."""
        try:
            # 1. Load data
            data = self.load_data()
            if not data:
                self.logger.warning("No data loaded. Exiting.")
                return

            # 2. Process data
            processed_data = self.process_data(data)
            if not processed_data:
                self.logger.warning("No data processed. Exiting.")
                return

            # 3. Ingest data
            self.ingest_data()

        except Exception as e:
            self.logger.error(f"An error occurred during the ingestion process: {e}", exc_info=True)