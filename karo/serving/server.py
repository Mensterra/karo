import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Query 
from karo.schemas.base_schemas import AgentErrorSchema
from pydantic import ValidationError


try:
    from karo.sessions.service import InMemorySessionService, BaseSessionService
    from karo.core.base_agent import BaseAgent
    from karo.tools.base_tool import BaseTool
    from karo.sessions.session import BaseSession
    from karo.sessions.event import BaseEvent
    from .config import load_agent_from_config
    from .models import InvokeRequest, InvokeResponse
    from .auth import verify_jwt_token
except ImportError as e:
    raise ImportError(f"Ensure Karo serving components are accessible: {e}")

logger = logging.getLogger(__name__)

# --- Application State ---
# Use a simple dictionary for app state to hold loaded agent and tools
app_state: Dict[str, Any] = {
    "agent": None,
    "tools": None,
    "agent_input_schema": None,
    "agent_output_schema": None,
    "session_service": None, # Add state for session service
    "log_file_path": None, # Add state for log file path
}

# --- Lifespan Management (Load Agent on Startup) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load agent configuration on startup
    logger.info("Server starting up...")
    config_path = os.getenv("KARO_AGENT_CONFIG_PATH")
    if not config_path:
        logger.critical("FATAL: KARO_AGENT_CONFIG_PATH environment variable not set. Cannot load agent.")
        app_state["agent"] = None
        app_state["tools"] = {}
        app_state["log_file_path"] = None
    else:
        try:
            agent_instance, tools_dict = load_agent_from_config(config_path)
            app_state["agent"] = agent_instance
            app_state["tools"] = tools_dict
            app_state["agent_input_schema"] = agent_instance.config.input_schema
            app_state["agent_output_schema"] = agent_instance.config.output_schema
            app_state["log_file_path"] = os.getenv("KARO_LOG_FILE_PATH") # Get log path from env
            logger.info(f"Agent loaded successfully from {config_path}.")
            logger.info(f"Log file path for API retrieval: {app_state['log_file_path']}")
        except Exception as e:
            logger.critical(f"FATAL: Failed to load agent from config '{config_path}': {e}", exc_info=True)
            app_state["agent"] = None
            app_state["tools"] = {}
            app_state["log_file_path"] = None

    # Instantiate Session Service on startup
    try:
        session_service = InMemorySessionService()
        app_state["session_service"] = session_service
        logger.info("InMemorySessionService initialized.")
    except Exception as e:
        logger.critical(f"FATAL: Failed to initialize Session Service: {e}", exc_info=True)
        app_state["session_service"] = None


    yield # Server runs here

    # Clean up resources on shutdown (if any)
    logger.info("Server shutting down...")
    # Add cleanup logic here if needed

# --- FastAPI App ---
app = FastAPI(
    title="Karo Agent Server",
    description="API for interacting with configured Karo agents.",
    version="0.1.0", # Consider linking to Karo version
    lifespan=lifespan
)

# --- API Endpoints ---
@app.post("/invoke", response_model=InvokeResponse)
async def invoke_agent(
    request: InvokeRequest,
    # verify_jwt_token will raise HTTPException 401 if token is invalid/missing
    current_user_payload: Any = Depends(verify_jwt_token)
) -> InvokeResponse:
    """
    Invoke the configured Karo agent with the provided input message.
    Handles session management and external tool orchestration.
    """
    agent: Optional[BaseAgent] = app_state.get("agent")
    tools: Dict[str, BaseTool] = app_state.get("tools", {})
    session_service: Optional[BaseSessionService] = app_state.get("session_service")
    InputSchema = app_state.get("agent_input_schema")
    OutputSchema = app_state.get("agent_output_schema")

    if not agent or not InputSchema or not OutputSchema:
        logger.error("/invoke called but agent is not loaded.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Agent not loaded or configuration error.")
    if not session_service:
         logger.error("/invoke called but session service is not available.")
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Session service not available.")

    logger.info(f"Received invocation request: Session={request.session_id}, Message='{request.chat_message[:50]}...'")

    # --- Session Handling ---
    session: Optional[BaseSession] = None
    # Extract user identifier from JWT payload (assuming 'sub' claim holds user ID)
    user_id = current_user_payload.get("sub", "default_user") # Provide a default if 'sub' is missing
    if not user_id: # Ensure we have some user identifier
        logger.error("Could not determine user identifier from JWT payload.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authentication token payload.")

    app_name = "karo_agent_server" # Example app name, could be configurable

    if request.session_id:
        session = session_service.get_session(request.session_id)
        if not session:
            logger.warning(f"Session ID '{request.session_id}' provided but not found. Creating new session.")
            # Fall through to create new session
        elif session.user_id != user_id or session.app_name != app_name:
             logger.error(f"Session '{request.session_id}' mismatch for user '{user_id}' / app '{app_name}'.")
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session mismatch.")
        else:
             logger.info(f"Loaded existing session: {session.id}")

    if not session:
        session = session_service.create_session(user_id=user_id, app_name=app_name)
        logger.info(f"Created new session: {session.id}")

    # --- Agent Execution ---
    try:
        # 1. Prepare Agent Input & Add User Event
        input_data = InputSchema(chat_message=request.chat_message)
        user_event = BaseEvent(role="user", content=request.chat_message)
        session.add_event(user_event) # Add event before running agent

        # 2. Prepare History & State for Agent
        # Simple truncation for now, more sophisticated logic possible
        # Note: BaseAgent needs update to accept history/state
        history_limit = getattr(agent.config, 'max_history_messages', 10) # Safely get history limit
        history_for_agent = session.events[-history_limit:]
        # Convert BaseEvents back to simple dicts for the prompt builder/LLM call
        history_dicts = [{"role": evt.role, "content": evt.content} for evt in history_for_agent]
        current_state = session.state.copy() # Pass a copy

        # 3. Run the Agent (passing history and state)
        agent_output = agent.run(
            input_data=input_data,
            history=history_dicts,
            state=current_state
            # Note: BaseAgent.run needs to be updated to accept history/state
        )

        # 4. Process Agent Output & Update Session
        if isinstance(agent_output, OutputSchema):
            agent_output_dict = agent_output.model_dump()
            action = agent_output_dict.get("action")
            response_text = agent_output_dict.get("response_text", agent_output_dict.get("message")) # Try common fields

            if action == "LOOKUP_ORDER":
                tool_name = "csv_order_reader" # Hardcoded for this specific agent/schema
                tool_params_dict = agent_output_dict.get("tool_parameters")
                logger.info(f"Agent requested tool action: {action} (Tool: {tool_name})")
                tool_instance = tools.get(tool_name)

                if not tool_instance:
                    logger.error(f"Configured tool '{tool_name}' not found for action {action}")
                    # Add assistant error event before returning
                    err_event = BaseEvent(role="assistant", content=f"Server configuration error: Tool '{tool_name}' not found.")
                    session.add_event(err_event)
                    session_service.update_session(session)
                    return InvokeResponse(session_id=session.id, success=False, error=f"Server configuration error: Tool '{tool_name}' not found.")

                if tool_params_dict is None:
                    logger.error(f"Agent requested tool '{tool_name}' but provided no parameters.")
                    err_event = BaseEvent(role="assistant", content=f"Error: Agent did not provide parameters for tool '{tool_name}'.")
                    session.add_event(err_event)
                    session_service.update_session(session)
                    return InvokeResponse(session_id=session.id, success=False, error=f"Agent did not provide parameters for tool '{tool_name}'.")

                # Wrap tool parameter validation and execution in try/except
                try:
                    ToolInputSchema = tool_instance.get_input_schema()
                    tool_input_data = ToolInputSchema(**tool_params_dict)
                    logger.info(f"Executing tool '{tool_name}' with params: {tool_input_data}")
                    tool_result = tool_instance.run(tool_input_data)
                    logger.info(f"Tool '{tool_name}' executed. Success: {tool_result.success}")

                    # Add assistant event with tool result (or error) before returning
                    # This assumes tool_result has a meaningful string representation or specific fields
                    tool_content = f"Tool {tool_name} result: {tool_result.model_dump()}" # Example content
                    assistant_event = BaseEvent(role="assistant", content=tool_content)
                    session.add_event(assistant_event)
                    session_service.update_session(session)

                    # Return the tool's result directly (as per original logic)
                    # In a more complex flow, you might feed this back to the agent
                    return InvokeResponse(session_id=session.id, success=tool_result.success, response_data=tool_result.model_dump(), error=tool_result.error_message)

                except ValidationError as e:
                     logger.error(f"Tool parameter validation failed for {tool_name}: {e}")
                     err_event = BaseEvent(role="assistant", content=f"Error: Invalid parameters for tool {tool_name}: {e}")
                     session.add_event(err_event)
                     session_service.update_session(session)
                     return InvokeResponse(session_id=session.id, success=False, error=f"Invalid parameters provided by agent for tool {tool_name}: {e}")
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                    err_event = BaseEvent(role="assistant", content=f"Error executing tool {tool_name}: {e}")
                    session.add_event(err_event)
                    session_service.update_session(session)
                    return InvokeResponse(session_id=session.id, success=False, error=f"Error executing tool {tool_name}: {e}")

            elif action == "ANSWER" or action == "REQUEST_INFO":
                logger.info(f"Agent action '{action}' requires direct response.")
                # Extract the actual response text - prioritize 'response_message'
                response_content = agent_output_dict.get("response_message") \
                                or agent_output_dict.get("response_text") \
                                or agent_output_dict.get("message")

                if response_content is None:
                     # If no specific text field found, serialize the whole output data as content
                     logger.warning(f"Agent action '{action}' but no standard response text field found. Using full response_data.")
                     import json
                     response_content = json.dumps(agent_output_dict) # Fallback to full JSON
                elif not isinstance(response_content, str):
                     logger.warning(f"Found response content field, but it's not a string ({type(response_content)}). Converting to string.")
                     response_content = str(response_content) # Ensure content is string

                assistant_event = BaseEvent(role="assistant", content=response_content)
                session.add_event(assistant_event)
                # Check if agent modified state (requires agent.run to return modified state)
                # Example: if 'updated_state' in agent_output_dict: session.update_state(agent_output_dict['updated_state'])
                session_service.update_session(session)
                return InvokeResponse(session_id=session.id, success=True, response_data=agent_output.model_dump())
            else:
                 logger.warning(f"Agent returned output schema with unexpected action '{action}' or missing data: {agent_output.model_dump()}")
                 assistant_event = BaseEvent(role="assistant", content="An unexpected response occurred.")
                 session.add_event(assistant_event)
                 session_service.update_session(session)
                 return InvokeResponse(session_id=session.id, success=True, response_data=agent_output.model_dump(), error=f"Agent returned unclear action: {action}")


        elif isinstance(agent_output, AgentErrorSchema):
            logger.error(f"Agent run failed: {agent_output.error_type} - {agent_output.error_message}")
            assistant_event = BaseEvent(role="assistant", content=f"Error: {agent_output.error_message}")
            session.add_event(assistant_event)
            session_service.update_session(session)
            return InvokeResponse(session_id=session.id, success=False, error=f"Agent Error: {agent_output.error_message}")
        else:
            # Should not happen if provider validation works
            logger.error(f"Agent returned unexpected type: {type(agent_output)}")
            err_event = BaseEvent(role="assistant", content="Error: Agent returned unexpected output type.")
            session.add_event(err_event)
            session_service.update_session(session) # Save session even on unexpected output
            return InvokeResponse(session_id=session.id, success=False, error="Agent returned unexpected output type.")

    except Exception as e:
        logger.error(f"Unexpected error during agent invocation: {e}", exc_info=True)
        # Attempt to save session state even if an unexpected error occurs mid-processing
        if session and session_service:
            try:
                err_event = BaseEvent(role="assistant", content=f"Internal Server Error: {e}")
                session.add_event(err_event)
                session_service.update_session(session)
                logger.info(f"Session {session.id} saved after encountering unexpected error.")
            except Exception as save_err:
                logger.error(f"Failed to save session {session.id} after error: {save_err}", exc_info=True)

        # Don't expose internal errors directly unless needed
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during agent invocation.")


# --- Helper for Log Reading ---
def read_log_file_tail(file_path: str, limit: int = 100) -> List[str]:
    """Reads the last 'limit' lines from a file."""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            return lines[-limit:]
    except FileNotFoundError:
        logger.warning(f"Log file not found at {file_path} for tail reading.")
        return []
    except Exception as e:
        logger.error(f"Error reading log file tail {file_path}: {e}", exc_info=True)
        return []

# --- Log Retrieval Endpoint ---
@app.get("/logs", response_model=List[str])
async def get_logs(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of log lines to return."),
    # Add 'since' filtering later if needed
    current_user_payload: Any = Depends(verify_jwt_token) # Secure this endpoint
) -> List[str]:
    """
    Retrieve recent log entries from the configured log file.
    Requires authentication.
    """
    log_file_path = app_state.get("log_file_path") # Get path set during startup

    if not log_file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not configured for file logging.")

    log_lines = read_log_file_tail(log_file_path, limit)

    if not log_lines and not os.path.exists(log_file_path):
         # Check again in case file was just created but is empty
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log file not found or is empty.")

    return log_lines


# Add other endpoints later (e.g., /auth)