import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone # Added timezone

# Modules to test
from karo.memory.tools.memory_query_tool import MemoryQueryTool, MemoryQueryInput
from karo.memory.services.chromadb_service import ChromaDBService # Needed for type hint and mocking
from karo.memory.memory_models import MemoryRecord, MemoryQueryResult # Needed for output structure

# --- Fixtures ---

@pytest.fixture
def mock_chroma_service():
    """Provides a MagicMock for the ChromaDBService."""
    service = MagicMock(spec=ChromaDBService)
    return service

@pytest.fixture
def memory_query_tool(mock_chroma_service):
    """Provides an instance of MemoryQueryTool with a mocked service."""
    return MemoryQueryTool(chroma_service=mock_chroma_service)

# --- Test Cases ---

def test_memory_query_tool_init(mock_chroma_service):
    """Tests successful initialization."""
    tool = MemoryQueryTool(chroma_service=mock_chroma_service)
    assert tool.chroma_service == mock_chroma_service

def test_memory_query_tool_init_type_error():
    """Tests that initialization raises ValueError with wrong service type."""
    with pytest.raises(ValueError, match="requires an initialized ChromaDBService"):
        MemoryQueryTool(chroma_service="not a service")

def test_memory_query_tool_run_success(memory_query_tool, mock_chroma_service):
    """Tests successful run and result processing."""
    query_text = "search for this"
    n_results = 3
    where_filter = {"topic": "test"}
    input_data = MemoryQueryInput(query_text=query_text, n_results=n_results, where_filter=where_filter)

    # Mock the raw results from the service
    ts1 = datetime.now(timezone.utc).isoformat()
    ts2 = datetime.now(timezone.utc).isoformat()
    mock_raw_results = [
        {'id': 'res1', 'text': 'Result 1 text', 'metadata': {'topic': 'test', 'created_at': ts1}, 'distance': 0.1},
        {'id': 'res2', 'text': 'Result 2 text', 'metadata': {'topic': 'test', 'created_at': ts2, 'importance_score': 0.5}, 'distance': 0.2},
    ]
    mock_chroma_service.query_memories.return_value = mock_raw_results

    output = memory_query_tool.run(input_data)

    # Check that service was called correctly
    mock_chroma_service.query_memories.assert_called_once_with(
        query_text=query_text,
        n_results=n_results,
        where=where_filter
    )

    # Check output structure and content
    assert output.success is True
    assert output.error_message is None
    assert len(output.results) == 2

    # Check first result processing
    assert isinstance(output.results[0], MemoryQueryResult)
    assert isinstance(output.results[0].record, MemoryRecord)
    assert output.results[0].record.id == 'res1'
    assert output.results[0].record.text == 'Result 1 text'
    assert output.results[0].record.metadata['topic'] == 'test'
    assert output.results[0].distance == 0.1

    # Check second result processing (with importance score)
    assert isinstance(output.results[1], MemoryQueryResult)
    assert isinstance(output.results[1].record, MemoryRecord)
    assert output.results[1].record.id == 'res2'
    assert output.results[1].record.importance_score == 0.5
    assert output.results[1].distance == 0.2

def test_memory_query_tool_run_no_results(memory_query_tool, mock_chroma_service):
    """Tests run when the service returns no results."""
    query_text = "nothing found"
    input_data = MemoryQueryInput(query_text=query_text)
    mock_chroma_service.query_memories.return_value = [] # Empty list

    output = memory_query_tool.run(input_data)

    mock_chroma_service.query_memories.assert_called_once_with(
        query_text=query_text,
        n_results=5, # Default n_results
        where=None
    )
    assert output.success is True
    assert output.error_message is None
    assert len(output.results) == 0

def test_memory_query_tool_run_service_error(memory_query_tool, mock_chroma_service):
    """Tests run failure when chroma_service raises an exception."""
    error_message = "Chroma query failed"
    mock_chroma_service.query_memories.side_effect = Exception(error_message)

    input_data = MemoryQueryInput(query_text="query that fails")
    output = memory_query_tool.run(input_data)

    assert output.success is False
    assert output.error_message == error_message
    assert len(output.results) == 0
    mock_chroma_service.query_memories.assert_called_once() # Ensure it was called

def test_memory_query_tool_run_invalid_input(memory_query_tool, mock_chroma_service):
    """Tests run failure with invalid input type."""
    invalid_input = {"query": "this is not a MemoryQueryInput object"}
    output = memory_query_tool.run(invalid_input) # type: ignore

    assert output.success is False
    assert output.error_message == "Invalid input data format."
    assert len(output.results) == 0
    mock_chroma_service.query_memories.assert_not_called()