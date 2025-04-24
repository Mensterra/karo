import pytest
from unittest.mock import MagicMock, ANY


# Modules to test
from karo.memory.tools.memory_store_tool import MemoryStoreTool, MemoryStoreInput
from karo.memory.services.chromadb_service import ChromaDBService # Needed for type hint and mocking

# --- Fixtures ---

@pytest.fixture
def mock_chroma_service():
    """Provides a MagicMock for the ChromaDBService."""
    service = MagicMock(spec=ChromaDBService)
    return service

@pytest.fixture
def memory_store_tool(mock_chroma_service):
    """Provides an instance of MemoryStoreTool with a mocked service."""
    return MemoryStoreTool(chroma_service=mock_chroma_service)

# --- Test Cases ---

def test_memory_store_tool_init(mock_chroma_service):
    """Tests successful initialization."""
    tool = MemoryStoreTool(chroma_service=mock_chroma_service)
    assert tool.chroma_service == mock_chroma_service

def test_memory_store_tool_init_type_error():
    """Tests that initialization raises ValueError with wrong service type."""
    with pytest.raises(ValueError, match="requires an initialized ChromaDBService"):
        MemoryStoreTool(chroma_service="not a service")

# Remove patch - MemoryRecord is no longer instantiated directly in the run method
def test_memory_store_tool_run_success_no_id(memory_store_tool, mock_chroma_service):
    """Tests successful run when no ID is provided."""
    input_data = MemoryStoreInput(memory_text="Test memory text")
    output = memory_store_tool.run(input_data)

    # Check that chroma_service.add_memory was called correctly
    # We use ANY for id and created_at as they are generated internally
    mock_chroma_service.add_memory.assert_called_once_with(
        id=ANY,
        text="Test memory text",
        metadata={"created_at": ANY} # Only timestamp added if no other meta/score
    )
    # Check output
    assert output.success is True
    assert isinstance(output.memory_id, str) # Check an ID was generated/returned
    assert len(output.memory_id) > 0
    assert output.error_message is None

# Remove patch
def test_memory_store_tool_run_success_with_id_meta_score(memory_store_tool, mock_chroma_service):
    """Tests successful run with provided ID, metadata, and score."""
    provided_id = "custom-id-456"
    provided_meta = {"source": "test"}
    provided_score = 0.9

    input_data = MemoryStoreInput(
        memory_id=provided_id,
        memory_text="Another test memory",
        metadata=provided_meta,
        importance_score=provided_score
    )
    output = memory_store_tool.run(input_data)

    # Check that chroma_service.add_memory was called correctly
    mock_chroma_service.add_memory.assert_called_once_with(
        id=provided_id,
        text="Another test memory",
        metadata={
            "source": "test",
            "created_at": ANY, # Timestamp is added internally
            "importance_score": provided_score
        }
    )
    # Check output
    assert output.success is True
    assert output.memory_id == provided_id
    assert output.error_message is None

# Remove patch
def test_memory_store_tool_run_service_error(memory_store_tool, mock_chroma_service):
    """Tests run failure when chroma_service raises an exception."""
    error_message = "ChromaDB connection failed"
    mock_chroma_service.add_memory.side_effect = Exception(error_message)

    input_data = MemoryStoreInput(memory_text="Memory that will fail")
    output = memory_store_tool.run(input_data)

    assert output.success is False
    # memory_id might be None or the generated one depending on where exception occurs,
    # but error message is more important here. Let's check it matches the service error.
    assert output.error_message == error_message
    # We still expect add_memory to be called once, even though it fails
    mock_chroma_service.add_memory.assert_called_once()

def test_memory_store_tool_run_invalid_input(memory_store_tool, mock_chroma_service):
    """Tests run failure with invalid input type."""
    invalid_input = {"text": "this is not a MemoryStoreInput object"}
    output = memory_store_tool.run(invalid_input) # type: ignore

    assert output.success is False
    assert output.error_message == "Invalid input data format."
    mock_chroma_service.add_memory.assert_not_called()