import uuid
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field

class BaseEvent(BaseModel):
    """
    Represents a single event or turn within a Karo session.
    Initially focused on user/assistant messages. Can be extended later
    to include tool calls/results or state changes if needed.
    """
    role: Literal["user", "assistant"] = Field(..., description="The role responsible for this event content.")
    content: str = Field(..., description="The textual content of the event (user message or assistant response).")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the event was created.")
    id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4()}", description="Unique identifier for the event.")

    model_config = {
        "frozen": True, # Events should be immutable once created
        "extra": "forbid"
    }