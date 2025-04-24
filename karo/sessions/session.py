import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from pydantic import BaseModel, Field

# Use absolute path for consistency
from karo.sessions.event import BaseEvent

class BaseSession(BaseModel):
    """
    Represents a single conversation session, including its history and state.
    """
    id: str = Field(default_factory=lambda: f"sid_{uuid.uuid4()}", description="Unique identifier for the session.")
    user_id: str = Field(..., description="Identifier for the user associated with this session.")
    app_name: str = Field(..., description="Identifier for the agent or application this session belongs to.")
    state: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary dictionary to hold session-specific state.")
    events: List[BaseEvent] = Field(default_factory=list, description="Ordered list of events (user messages, assistant responses) in the session.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the session was created.")
    last_update_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the session was last updated.")

    model_config = {
        "extra": "forbid"
    }

    def add_event(self, event: BaseEvent):
        """Adds an event to the session's history and updates timestamp."""
        self.events.append(event)
        self.last_update_time = datetime.now(timezone.utc)

    def update_state(self, new_state: Dict[str, Any]):
        """Updates the session state dictionary."""
        self.state.update(new_state)
        self.last_update_time = datetime.now(timezone.utc)