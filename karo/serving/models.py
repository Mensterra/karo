from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class InvokeRequest(BaseModel):
    """
    Request model for the /invoke endpoint.
    """
    chat_message: str = Field(..., description="The user's message or query for the agent.")
    session_id: Optional[str] = Field(None, description="Optional session identifier to continue an existing conversation. If None, a new session is created.")
    # Add other potential fields like user_id (if not using JWT sub), specific config overrides, etc. if needed later

class InvokeResponse(BaseModel):
    """
    Response model for the /invoke endpoint.
    """
    session_id: str = Field(..., description="The session identifier for this conversation turn.")
    success: bool = Field(..., description="Indicates whether the agent invocation and any subsequent actions were successful.")
    response_data: Optional[Dict[str, Any]] = Field(None, description="The structured output from the agent (conforming to its output_schema) or the result from a tool execution, serialized as a dictionary.")
    error: Optional[str] = Field(None, description="An error message if the invocation failed.")