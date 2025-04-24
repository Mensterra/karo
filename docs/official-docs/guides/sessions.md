# Session Management in Karo

Karo includes a session management system to maintain conversation history and state across multiple interactions with an agent, typically via the FastAPI server.

## Core Concepts

*   **BaseSession:** A Pydantic model representing a single conversation session. It stores:
    *   `id`: Unique session identifier.
    *   `user_id`: Identifier for the user associated with the session.
    *   `app_name`: Identifier for the agent/application.
    *   `state`: A dictionary for storing arbitrary session-specific data.
    *   `events`: A list of `BaseEvent` objects representing the conversation turns.
    *   `created_at`, `last_update_time`: Timestamps.
*   **BaseEvent:** A Pydantic model representing a single turn in the conversation (e.g., a user message or an assistant response). It stores:
    *   `id`: Unique event identifier.
    *   `role`: "user" or "assistant".
    *   `content`: The text content of the message.
    *   `timestamp`: When the event occurred.
*   **BaseSessionService:** An abstract base class defining the interface for session storage and retrieval. Key methods include `create_session`, `get_session`, `update_session`, `delete_session`, `list_sessions`.
*   **InMemorySessionService:** An implementation of `BaseSessionService` that stores sessions in a Python dictionary in memory. **Note:** Sessions are lost when the server restarts.

## Server Integration (`/invoke` Endpoint)

The FastAPI server (`karo.serving.server`) integrates session management into the `/invoke` endpoint:

1.  **Request:** The `InvokeRequest` model accepts an optional `session_id`.
2.  **Authentication:** The endpoint requires JWT authentication. The user ID (`sub` claim) from the token is used to associate the session with the user.
3.  **Session Handling:**
    *   If a `session_id` is provided in the request:
        *   The server attempts to retrieve the session using `session_service.get_session()`.
        *   It verifies that the retrieved session belongs to the authenticated user and the expected application.
        *   If the session is not found or doesn't match, a warning is logged, and a *new* session is created.
    *   If no `session_id` is provided, or if retrieval failed, a new session is created using `session_service.create_session()`.
4.  **Event Recording:**
    *   The incoming user message (`chat_message`) is added as a `BaseEvent` (role="user") to the session's `events` list.
5.  **Agent Execution:**
    *   The recent conversation history (as a list of dictionaries like `{"role": "user", "content": "..."}`) is extracted from `session.events`.
    *   The current session `state` dictionary is retrieved.
    *   The `agent.run()` method is called, passing the `input_data`, `history`, and `state`.
6.  **Response Handling:**
    *   The agent's response (or error) is processed.
    *   An appropriate `BaseEvent` (role="assistant") is created with the response content (or error message).
    *   This assistant event is added to `session.events`.
    *   *(Future Enhancement: If the agent modifies the `state` dictionary and returns it, the server should update `session.state`)*.
    *   The session is saved using `session_service.update_session()`.
7.  **Response:** The `InvokeResponse` includes the `session_id` (either the one provided or the newly generated one) along with the agent's output or error.

## Agent Integration (`BaseAgent`)

The `BaseAgent` (`karo.core.base_agent`) has been modified:

*   It no longer manages conversation history internally (`self.conversation_history` and `max_history_messages` config are removed).
*   The `run` method now accepts optional `history: List[Dict]` and `state: Dict` arguments.
*   The `_create_prompt_with_history` method uses the `history` argument passed to `run` when constructing the prompt for the LLM.
*   *(Future Enhancement: The agent could be designed to read from and potentially modify the passed `state` dictionary)*.

## Usage

To maintain a conversation across multiple API calls:

1.  Make the first POST request to `/invoke` without a `session_id`.
2.  Extract the `session_id` from the response.
3.  For all subsequent requests in the same conversation, include the received `session_id` in the JSON body of your POST request to `/invoke`.

## Limitations (In-Memory Implementation)

*   **Persistence:** The `InMemorySessionService` loses all session data when the server process stops or restarts.
*   **Scalability:** Storing all sessions in a single server's memory does not scale horizontally across multiple server instances.

For persistent and scalable session management, a different implementation of `BaseSessionService` would be required (e.g., using a database like Redis, PostgreSQL, or Firestore).