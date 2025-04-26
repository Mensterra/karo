"""
Base template script for ingesting documents into a Karo MemoryManager (ChromaDB).

This script demonstrates:
- Loading environment variables (e.g., OPENAI_API_KEY).
- Initializing ChromaDBService and MemoryManager.
- Using DocumentReaderTool to read files from a directory.
- Basic chunking strategy.
- Adding document chunks to the MemoryManager with metadata.

**How to Use:**
1. Copy this script to your project (e.g., into a 'scripts' directory).
2. Modify the CONFIGURATION section below (KB_DIR, DB_PATH, COLLECTION_NAME).
3. Ensure necessary dependencies are installed (karo, python-dotenv, pypdf, python-docx).
4. Set your OPENAI_API_KEY in a .env file accessible from where you run the script.
5. Run the script: `python path/to/your/copied_ingestion_script.py`
"""

import os
import glob
import logging
import sys
from dotenv import load_dotenv

# --- Import Karo Components ---
try:
    from karo.memory.services.chromadb_service import ChromaDBService, ChromaDBConfig
    from karo.memory.memory_manager import MemoryManager, MemoryManagerConfig
    from karo.tools.document_reader_tool import DocumentReaderTool, DocumentReaderInput
    from karo.utils.logging_config import setup_logging # Assuming setup_logging exists
except ImportError as e:
    print(f"Import Error: Failed to import Karo components: {e}")
    print("Please ensure 'karo' is installed.")
    print("Also ensure required dependencies (`pypdf`, `python-docx`) are installed if using PDF/DOCX.")
    sys.exit(1)

# --- Configuration ---
# MODIFY THESE VALUES FOR YOUR PROJECT
KB_DIR = "path/to/your/knowledge_base_files"  # Directory containing files to ingest
DB_PATH = "./.my_agent_karo_db"             # Path to store ChromaDB data (relative to script)
COLLECTION_NAME = "my_agent_kb"             # Name for the ChromaDB collection
DOTENV_PATH = os.path.join(os.getcwd(), ".env") # Path to your .env file

# Optional: Chunking parameters
CHUNK_SEPARATOR = "\n\n" # How to split documents (e.g., double newline for paragraphs)
MIN_CHUNK_LENGTH = 50    # Minimum characters for a chunk to be considered meaningful

# Setup logging
setup_logging(level=logging.INFO) # Use the utility if available
logger = logging.getLogger(__name__)

# --- Main Ingestion Logic ---
def ingest_knowledge_base():
    """Loads documents, chunks them, and adds them to the MemoryManager."""
    logger.info(f"Starting knowledge base ingestion from directory: {KB_DIR}")

    # Load environment variables (needed for OpenAI API key for embeddings)
    if load_dotenv(dotenv_path=DOTENV_PATH):
        logger.info(f"Loaded environment variables from {DOTENV_PATH}")
    else:
        logger.warning(f".env file not found at {DOTENV_PATH}. Relying on system environment variables.")

    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not found in environment variables. Please set it. Cannot generate embeddings.")
        return

    # 1. Initialize Karo Memory Components
    try:
        logger.info(f"Initializing ChromaDB at: {DB_PATH}")
        chroma_config = ChromaDBConfig(path=DB_PATH, collection_name=COLLECTION_NAME)
        mem_manager_config = MemoryManagerConfig(db_type='chromadb', chromadb_config=chroma_config)
        memory_manager = MemoryManager(config=mem_manager_config)
        doc_reader_tool = DocumentReaderTool()
        logger.info("Karo components initialized successfully.")

        # Optional: Clear existing collection before ingestion
        # logger.warning(f"Clearing existing collection '{COLLECTION_NAME}'...")
        # memory_manager.db_service.clear_collection() # Access service via manager

    except Exception as e:
        logger.error(f"Failed to initialize Karo components: {e}", exc_info=True)
        return

    # 2. Find and Process Files
    supported_extensions = ["*.txt", "*.md", "*.pdf", "*.docx"] # Add/remove as needed
    files_processed = 0
    chunks_added = 0

    if not os.path.exists(KB_DIR):
        logger.error(f"Knowledge base directory not found: {KB_DIR}")
        return

    logger.info(f"Searching for files with extensions {supported_extensions} in {KB_DIR}")
    for extension in supported_extensions:
        search_path = os.path.join(KB_DIR, extension)
        for file_path in glob.glob(search_path):
            logger.info(f"Processing file: {file_path}")
            files_processed += 1
            try:
                # Use DocumentReaderTool to get content
                read_input = DocumentReaderInput(file_path=file_path)
                read_output = doc_reader_tool.run(read_input)

                if read_output.success and read_output.content:
                    # Simple Chunking Strategy
                    chunks = read_output.content.split(CHUNK_SEPARATOR)
                    chunk_num = 0
                    for chunk in chunks:
                        chunk = chunk.strip()
                        if len(chunk) >= MIN_CHUNK_LENGTH:
                            chunk_num += 1
                            # Create a unique ID for the chunk
                            chunk_id = f"{os.path.basename(file_path)}-chunk{chunk_num}"
                            # Define metadata for the chunk
                            metadata = {"source_file": os.path.basename(file_path), "chunk_num": chunk_num}
                            # Add memory to the manager
                            added_id = memory_manager.add_memory(text=chunk, metadata=metadata, memory_id=chunk_id)
                            if added_id:
                                chunks_added += 1
                                logger.debug(f"Added chunk {chunk_num} from {file_path} with ID {added_id}")
                            else:
                                logger.warning(f"Failed to add chunk {chunk_num} from {file_path}")
                elif not read_output.success:
                    logger.error(f"Failed to read file {file_path}: {read_output.error_message}")

            except Exception as e:
                logger.error(f"An error occurred processing file {file_path}: {e}", exc_info=True)

    logger.info(f"Ingestion complete. Processed {files_processed} files, added {chunks_added} chunks to collection '{COLLECTION_NAME}'.")

if __name__ == "__main__":
    ingest_knowledge_base()