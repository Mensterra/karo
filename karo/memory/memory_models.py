from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class MemoryRecord(BaseModel):
    """
    Represents a single record stored in the memory system.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the memory record.")
    text: str = Field(..., description="The textual content of the memory.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the memory (e.g., source, topic, timestamp).")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the memory was created (UTC).")
    importance_score: Optional[float] = Field(None, description="Optional score indicating the importance of the memory (e.g., assigned by an LLM).")
    embedding: Optional[List[float]] = Field(None, description="Optional embedding vector (usually handled by ChromaDB directly).") # Usually not stored directly here if using Chroma's EF

    class Config:
        # Allow population by field name or alias if needed later
        populate_by_name = True
        # Make immutable if desired after creation?
        # frozen = True

class MemoryQueryResult(BaseModel):
    """
    Represents a result returned from a memory query, including distance/similarity.
    """
    record: MemoryRecord = Field(..., description="The retrieved memory record.")
    distance: Optional[float] = Field(None, description="The distance score from the query (lower is typically more similar).")
    similarity_score: Optional[float] = Field(None, description="Optional similarity score (e.g., 1 - distance for cosine).")

# You might add other models here later, e.g., for memory formation requests/responses
# class MemoryFormationRequest(BaseModel):
#     conversation_history: List[Dict[str, str]]
#     max_memories_to_form: int = 3

# class FormedMemory(BaseModel):
#     memory_text: str
#     importance: float
#     keywords: List[str]

# class MemoryFormationResponse(BaseModel):
#     formed_memories: List[FormedMemory]