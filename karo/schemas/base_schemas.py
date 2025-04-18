from pydantic import BaseModel, Field
from typing import Optional

class BaseInputSchema(BaseModel):
    """
    Base input schema for Karo agents.
    Requires a chat message as input.
    """
    chat_message: str = Field(..., description="The input message from the user.")

class BaseOutputSchema(BaseModel):
    """
    Base output schema for Karo agents.
    Provides the agent's response message.
    """
    response_message: str = Field(..., description="The output message from the agent.")

class AgentErrorSchema(BaseModel):
    """
    Schema for reporting errors during agent execution.
    """
    error_type: str = Field(..., description="The type of error that occurred.")
    error_message: str = Field(..., description="A detailed message describing the error.")
    details: Optional[str] = Field(None, description="Optional additional details about the error context.")