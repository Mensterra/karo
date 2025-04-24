import pytest
from unittest.mock import MagicMock, patch, ANY
import os

# Modules to test
from karo.memory.services.chromadb_service import ChromaDBService, ChromaDBConfig

# --- Fixtures ---

@pytest.fixture(scope="function") # Use function scope to reset mocks for each test
def mock_chromadb_client():
    """Provides a MagicMock for the chromadb client API."""
    client = MagicMock()
    # Mock the collection object and its methods
    mock_collection = MagicMock()
    client.get_or_create_collection.return_value = mock_collection
    client.heartbeat.return_value = 1 # Simulate successful connection
    return client, mock_collection

# Removed mock_openai_ef fixture as it's not needed due to @patch

@pytest.fixture
def chroma_config():
    """Provides a basic ChromaDBConfig for local persistence."""
    # Ensure API key is set for embedding function initialization test
    os.environ["OPENAI_API_KEY"] = "test-key-from-env"
    return ChromaDBConfig(
        path="./.test_chroma_db", # Use a test-specific path
        collection_name="test_collection",
        # openai_api_key=SecretStr("test-api-key") # Or set via config
    )

# --- Test Class ---

# Use patch decorators to replace external dependencies during tests
@patch('karo.memory.services.chromadb_service.chromadb.PersistentClient')
@patch('karo.memory.services.chromadb_service.embedding_functions.OpenAIEmbeddingFunction')
class TestChromaDBService:

    def test_initialization_persistent(self, mock_openai_ef_class, mock_persistent_client_class, mock_chromadb_client, chroma_config):
        """Tests successful initialization with a persistent client."""
        mock_client_instance, mock_collection_instance = mock_chromadb_client
        mock_persistent_client_class.return_value = mock_client_instance
        # The patch decorator provides the mock class, get the instance via return_value
        mock_openai_ef_instance = mock_openai_ef_class.return_value

        service = ChromaDBService(config=chroma_config)

        mock_persistent_client_class.assert_called_once_with(path=chroma_config.path, settings=ANY)
        mock_client_instance.heartbeat.assert_called_once()
        mock_openai_ef_class.assert_called_once_with(api_key="test-key-from-env", model_name=chroma_config.embedding_model_name)
        mock_client_instance.get_or_create_collection.assert_called_once_with(
            name=chroma_config.collection_name,
            embedding_function=mock_openai_ef_instance
        )
        assert service._client == mock_client_instance
        assert service._ef == mock_openai_ef_instance
        assert service._collection == mock_collection_instance
        assert service.collection == mock_collection_instance # Test property access

    # Add test for HTTP client initialization if needed

    def test_initialization_missing_api_key(self, mock_openai_ef_class, mock_persistent_client_class, chroma_config):
        """Tests initialization failure when OpenAI API key is missing."""
        # Unset env var for this test
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        chroma_config.openai_api_key = None # Ensure config doesn't provide it either

        with pytest.raises(ValueError, match="OpenAI API key not found"):
            ChromaDBService(config=chroma_config)

        # Restore env var if it existed
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key

    def test_add_memory(self, mock_openai_ef_class, mock_persistent_client_class, mock_chromadb_client, chroma_config):
        """Tests adding a single memory."""
        mock_client_instance, mock_collection_instance = mock_chromadb_client
        mock_persistent_client_class.return_value = mock_client_instance
        # No need to call mock_openai_ef()

        service = ChromaDBService(config=chroma_config)
        test_id = "mem1"
        test_text = "This is memory 1."
        test_metadata = {"topic": "test"}

        service.add_memory(id=test_id, text=test_text, metadata=test_metadata)

        mock_collection_instance.add.assert_called_once_with(
            ids=[test_id],
            documents=[test_text],
            metadatas=[test_metadata]
        )

    def test_add_memories(self, mock_openai_ef_class, mock_persistent_client_class, mock_chromadb_client, chroma_config):
        """Tests adding multiple memories."""
        mock_client_instance, mock_collection_instance = mock_chromadb_client
        mock_persistent_client_class.return_value = mock_client_instance
        # No need to call mock_openai_ef()

        service = ChromaDBService(config=chroma_config)
        test_ids = ["m1", "m2"]
        test_texts = ["Memory 1", "Memory 2"]
        test_metadatas = [{"t": 1}, {"t": 2}]

        service.add_memories(ids=test_ids, texts=test_texts, metadatas=test_metadatas)

        mock_collection_instance.add.assert_called_once_with(
            ids=test_ids,
            documents=test_texts,
            metadatas=test_metadatas
        )

    def test_query_memories(self, mock_openai_ef_class, mock_persistent_client_class, mock_chromadb_client, chroma_config):
        """Tests querying memories."""
        mock_client_instance, mock_collection_instance = mock_chromadb_client
        mock_persistent_client_class.return_value = mock_client_instance
        # No need to call mock_openai_ef()

        # Simulate the structure returned by collection.query
        mock_query_results = {
            'ids': [['res1', 'res2']],
            'documents': [['Doc 1', 'Doc 2']],
            'metadatas': [[{'topic': 'a'}, {'topic': 'b'}]],
            'distances': [[0.1, 0.2]]
        }
        mock_collection_instance.query.return_value = mock_query_results

        service = ChromaDBService(config=chroma_config)
        query_text = "find stuff"
        n_results = 2
        where_filter = {"topic": "a"}

        results = service.query_memories(query_text=query_text, n_results=n_results, where=where_filter)

        mock_collection_instance.query.assert_called_once_with(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter,
            include=['metadatas', 'documents', 'distances']
        )
        assert len(results) == 2
        assert results[0]['id'] == 'res1'
        assert results[0]['text'] == 'Doc 1'
        assert results[0]['metadata'] == {'topic': 'a'}
        assert results[0]['distance'] == 0.1
        assert results[1]['id'] == 'res2'

    def test_get_memory_by_id(self, mock_openai_ef_class, mock_persistent_client_class, mock_chromadb_client, chroma_config):
         """Tests getting a memory by ID."""
         mock_client_instance, mock_collection_instance = mock_chromadb_client
         mock_persistent_client_class.return_value = mock_client_instance
         # No need to call mock_openai_ef()

         mock_get_result = {
             'ids': ['mem_abc'],
             'documents': ['Document abc'],
             'metadatas': [{'source': 'test'}]
         }
         mock_collection_instance.get.return_value = mock_get_result

         service = ChromaDBService(config=chroma_config)
         test_id = "mem_abc"
         result = service.get_memory_by_id(id=test_id)

         mock_collection_instance.get.assert_called_once_with(ids=[test_id], include=['metadatas', 'documents'])
         assert result is not None
         assert result['id'] == test_id
         assert result['text'] == 'Document abc'
         assert result['metadata'] == {'source': 'test'}

    def test_delete_memory(self, mock_openai_ef_class, mock_persistent_client_class, mock_chromadb_client, chroma_config):
         """Tests deleting a memory."""
         mock_client_instance, mock_collection_instance = mock_chromadb_client
         mock_persistent_client_class.return_value = mock_client_instance
         # No need to call mock_openai_ef()

         service = ChromaDBService(config=chroma_config)
         test_id = "mem_to_delete"
         service.delete_memory(id=test_id)

         mock_collection_instance.delete.assert_called_once_with(ids=[test_id])

# Clean up environment variable if set
@pytest.fixture(autouse=True, scope="session")
def cleanup_env():
    yield
    if "OPENAI_API_KEY" in os.environ and os.environ["OPENAI_API_KEY"] == "test-key-from-env":
        del os.environ["OPENAI_API_KEY"]