import pytest
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime, timezone # Added timezone
import uuid

# Modules to test
from karo.memory.memory_manager import MemoryManager
from karo.memory.services.chromadb_service import ChromaDBService # Needed for type hint and mocking
from karo.memory.memory_models import MemoryRecord, MemoryQueryResult # Needed for checking results

# --- Fixtures ---

@pytest.fixture
def mock_chroma_service():
    """Provides a MagicMock for the ChromaDBService."""
    service = MagicMock(spec=ChromaDBService)
    return service

@pytest.fixture
def memory_manager(mock_chroma_service):
    """Provides an instance of MemoryManager with a mocked service."""
    return MemoryManager(chroma_service=mock_chroma_service)

# --- Test Cases ---

def test_memory_manager_init(mock_chroma_service):
    """Tests successful initialization."""
    manager = MemoryManager(chroma_service=mock_chroma_service)
    assert manager.chroma_service == mock_chroma_service

def test_memory_manager_init_type_error():
    """Tests that initialization raises TypeError with wrong service type."""
    with pytest.raises(TypeError):
        MemoryManager(chroma_service="not a service")

# No longer need to patch MemoryRecord here as it's not directly called in the refactored add_memory
def test_add_memory_success(memory_manager, mock_chroma_service):
    """Tests successfully adding a memory via the manager."""
    text = "Manager test memory"
    metadata = {"component": "manager"}
    score = 0.6
    # We can't easily predict the generated ID or timestamp anymore without mocking uuid/datetime,
    # so we'll use ANY for those in the assertion.

    result_id = memory_manager.add_memory(text=text, metadata=metadata, importance_score=score)

    # Check service was called correctly
    mock_chroma_service.add_memory.assert_called_once_with(
        id=ANY, # ID is generated internally now
        text=text,
        metadata={
            "component": "manager",
            "created_at": ANY, # Timestamp is added internally
            "importance_score": score
        }
    )
    # Check returned ID is a string (UUID)
    assert isinstance(result_id, str)
    assert len(result_id) > 0 # Basic check for non-empty string ID

@patch('karo.memory.memory_manager.MemoryRecord') # Patch MemoryRecord for this specific test
def test_add_memory_failure(mock_memory_record_class, memory_manager, mock_chroma_service):
    """Tests add_memory failure when the service fails."""
    # Mock the MemoryRecord instantiation within the manager method to avoid validation error
    # before the service call exception is tested.
    mock_memory_record_class.return_value = MagicMock(id="dummy_id", text="dummy", metadata={}, timestamp=datetime.now(timezone.utc), importance_score=None) # Use timezone-aware UTC time

    mock_chroma_service.add_memory.side_effect = Exception("DB write error")

    result_id = memory_manager.add_memory(text="This will fail")

    assert result_id is None
    # We still expect add_memory to be called once, even though it fails
    mock_chroma_service.add_memory.assert_called_once()

def test_retrieve_relevant_memories_success(memory_manager, mock_chroma_service):
    """Tests successfully retrieving memories."""
    query = "find relevant info"
    n_results = 2
    where = {"topic": "relevant"}

    # Mock the raw results from the service
    ts1 = datetime.now(timezone.utc).isoformat()
    ts2 = datetime.now(timezone.utc).isoformat()
    mock_raw_results = [
        {'id': 'rel1', 'text': 'Relevant 1', 'metadata': {'topic': 'relevant', 'created_at': ts1}, 'distance': 0.15},
        {'id': 'rel2', 'text': 'Relevant 2', 'metadata': {'topic': 'relevant', 'created_at': ts2, 'importance_score': 0.7}, 'distance': 0.25},
    ]
    mock_chroma_service.query_memories.return_value = mock_raw_results

    results = memory_manager.retrieve_relevant_memories(query_text=query, n_results=n_results, where_filter=where)

    # Check service call
    mock_chroma_service.query_memories.assert_called_once_with(
        query_text=query,
        n_results=n_results,
        where=where
    )

    # Check processed results
    assert len(results) == 2
    assert isinstance(results[0], MemoryQueryResult)
    assert isinstance(results[0].record, MemoryRecord)
    assert results[0].record.id == 'rel1'
    assert results[0].record.text == 'Relevant 1'
    assert results[0].distance == 0.15
    assert results[1].record.id == 'rel2'
    assert results[1].record.importance_score == 0.7

def test_retrieve_relevant_memories_failure(memory_manager, mock_chroma_service):
    """Tests retrieval failure when the service fails."""
    mock_chroma_service.query_memories.side_effect = Exception("DB query error")

    results = memory_manager.retrieve_relevant_memories(query_text="This query fails")

    assert results == [] # Should return empty list on error
    mock_chroma_service.query_memories.assert_called_once()

def test_get_memory_by_id_success(memory_manager, mock_chroma_service):
    """Tests getting a memory by ID successfully."""
    test_id = "get_me"
    ts_get = datetime.now(timezone.utc).isoformat()
    mock_raw_result = {
        'id': test_id,
        'text': 'Found me!',
        'metadata': {'source': 'get_test', 'created_at': ts_get}
    }
    mock_chroma_service.get_memory_by_id.return_value = mock_raw_result

    result_record = memory_manager.get_memory_by_id(memory_id=test_id)

    mock_chroma_service.get_memory_by_id.assert_called_once_with(test_id)
    assert isinstance(result_record, MemoryRecord)
    assert result_record.id == test_id
    assert result_record.text == 'Found me!'
    assert result_record.metadata['source'] == 'get_test'

def test_get_memory_by_id_not_found(memory_manager, mock_chroma_service):
    """Tests getting a memory by ID when it's not found."""
    mock_chroma_service.get_memory_by_id.return_value = None
    test_id = "not_found"

    result_record = memory_manager.get_memory_by_id(memory_id=test_id)

    mock_chroma_service.get_memory_by_id.assert_called_once_with(test_id)
    assert result_record is None

def test_get_memory_by_id_service_error(memory_manager, mock_chroma_service):
    """Tests getting a memory by ID when the service fails."""
    mock_chroma_service.get_memory_by_id.side_effect = Exception("DB get error")
    test_id = "error_id"

    # Depending on implementation, might return None or raise error.
    # Current service implementation logs error and returns None.
    result_record = memory_manager.get_memory_by_id(memory_id=test_id)
    assert result_record is None
    mock_chroma_service.get_memory_by_id.assert_called_once_with(test_id)


def test_delete_memory(memory_manager, mock_chroma_service):
    """Tests deleting a memory."""
    test_id = "delete_me"
    memory_manager.delete_memory(memory_id=test_id)
    mock_chroma_service.delete_memory.assert_called_once_with(test_id)