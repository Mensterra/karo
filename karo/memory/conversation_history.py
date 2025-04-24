from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConversationHistory:
    """
    Manages the short-term conversation history for an agent.

    Stores messages in the format expected by LLM providers (e.g., OpenAI)
    and handles buffer limits.
    """
    def __init__(self, max_messages: Optional[int] = None):
        """
        Initializes the conversation history buffer.

        Args:
            max_messages: The maximum number of messages (user + assistant turns)
                          to retain. If None, history is unlimited (use with caution).
        """
        self.history: List[Dict[str, Any]] = []
        self.max_messages = max_messages
        logger.info(f"ConversationHistory initialized with max_messages={max_messages}")

    def add_message(self, role: str, content: Any):
        """
        Adds a message to the history.

        Args:
            role: The role of the message sender ('user' or 'assistant').
            content: The message content. Can be a string or a Pydantic model
                     (will be converted to dict if not already a string).
                     Tool call/result messages might need specific formatting
                     depending on the provider and how they are handled.
                     Currently assumes simple string content or dict representation.
        """
        if not isinstance(role, str) or role not in ["user", "assistant", "tool"]: # Allow tool role for future?
             logger.warning(f"Invalid role '{role}' provided for conversation history. Must be 'user' or 'assistant'. Skipping.")
             # Or raise ValueError("Role must be 'user' or 'assistant'")
             return

        message_content = content
        # Basic handling if content is a Pydantic model - convert to dict
        # More sophisticated serialization might be needed for complex objects or tool calls
        if hasattr(content, 'model_dump'):
            try:
                # Use model_dump for Pydantic v2+
                message_content = content.model_dump(exclude_unset=True, exclude_none=True)
                # If the schema only had one field (like response_message), extract it?
                # This might be too opinionated. Let's keep the dict for now.
                # Example: if isinstance(content, BaseOutputSchema): message_content = content.response_message
            except Exception as e:
                logger.warning(f"Could not serialize Pydantic model for history content: {e}. Using string representation.")
                message_content = str(content)
        elif not isinstance(content, (str, dict, list)): # Allow lists for Anthropic format
             logger.warning(f"Unsupported content type {type(content)} for history. Converting to string.")
             message_content = str(content)

        message = {"role": role, "content": message_content}
        self.history.append(message)
        logger.debug(f"Added message to history: Role={role}, Content Type={type(message_content)}")

        self._enforce_limit()

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Returns the current conversation history list.
        """
        return self.history.copy() # Return a copy

    def clear(self):
        """Clears the conversation history."""
        self.history = []
        logger.info("Conversation history cleared.")

    def _enforce_limit(self):
        """Removes oldest messages if the history exceeds max_messages."""
        if self.max_messages is not None and len(self.history) > self.max_messages:
            num_to_remove = len(self.history) - self.max_messages
            self.history = self.history[num_to_remove:]
            logger.debug(f"History limit enforced. Removed {num_to_remove} oldest messages.")

    def __len__(self):
        return len(self.history)

    def __repr__(self):
        return f"ConversationHistory(max_messages={self.max_messages}, current_length={len(self.history)})"