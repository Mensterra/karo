import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
from datetime import datetime, timezone
import threading

# Use absolute path for consistency
from karo.sessions.session import BaseSession

logger = logging.getLogger(__name__)

class BaseSessionService(ABC):
    """Abstract base class for session management services."""

    @abstractmethod
    def create_session(
        self,
        user_id: str,
        app_name: str,
        initial_state: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> BaseSession:
        """Creates and stores a new session."""
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[BaseSession]:
        """Retrieves a session by its ID."""
        pass

    @abstractmethod
    def update_session(self, session: BaseSession) -> None:
        """Updates an existing session."""
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """Deletes a session by its ID. Returns True if deleted, False otherwise."""
        pass

    @abstractmethod
    def list_sessions(self, user_id: Optional[str] = None, app_name: Optional[str] = None) -> List[BaseSession]:
        """Lists sessions, optionally filtering by user_id and/or app_name."""
        pass


class InMemorySessionService(BaseSessionService):
    """
    An in-memory implementation of the session service.
    Stores sessions in a Python dictionary. Sessions are lost on restart.
    Includes basic thread safety for concurrent access.
    """
    def __init__(self):
        self._sessions: Dict[str, BaseSession] = {}
        self._lock = threading.Lock() # Lock for thread safety
        logger.info("InMemorySessionService initialized.")

    def create_session(
        self,
        user_id: str,
        app_name: str,
        initial_state: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> BaseSession:
        with self._lock:
            if session_id and session_id in self._sessions:
                logger.warning(f"Attempted to create session with existing ID: {session_id}. Returning existing.")
                # Ensure we return a copy if returning existing session
                return self._sessions[session_id].model_copy(deep=True)

            # Only pass id to constructor if it's provided, otherwise let default_factory work
            session_kwargs = {
                "user_id": user_id,
                "app_name": app_name,
                "state": initial_state or {}
            }
            if session_id:
                session_kwargs["id"] = session_id

            session = BaseSession(**session_kwargs)
            # Ensure the generated ID is used if session_id was None
            if session_id is None:
                 session_id = session.id # Get the generated ID

            self._sessions[session.id] = session # Store using the potentially generated ID
            logger.info(f"Created new session: ID={session.id}, User={user_id}, App={app_name}")
            # Return a copy to prevent external modification
            return session.model_copy(deep=True)

    def get_session(self, session_id: str) -> Optional[BaseSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                logger.debug(f"Retrieved session: ID={session_id}")
                # Return a copy to prevent external modification of the stored object?
                # For in-memory, direct access might be acceptable, but copy is safer.
                return session.model_copy(deep=True)
            else:
                logger.debug(f"Session not found: ID={session_id}")
                return None

    def update_session(self, session: BaseSession) -> None:
        if not isinstance(session, BaseSession):
             raise TypeError("session must be an instance of BaseSession")
        with self._lock:
            if session.id not in self._sessions:
                logger.warning(f"Attempted to update non-existent session: ID={session.id}")
                # Optionally create it? Or raise error? Let's just log for now.
                # self._sessions[session.id] = session # Create if not exists?
                return # Don't update if it doesn't exist

            # Update timestamp before storing
            session.last_update_time = datetime.now(timezone.utc)
            self._sessions[session.id] = session
            logger.debug(f"Updated session: ID={session.id}")

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Deleted session: ID={session_id}")
                return True
            else:
                logger.warning(f"Attempted to delete non-existent session: ID={session_id}")
                return False

    def list_sessions(self, user_id: Optional[str] = None, app_name: Optional[str] = None) -> List[BaseSession]:
        with self._lock:
            # Return copies to prevent external modification
            sessions = [s.model_copy(deep=True) for s in self._sessions.values()]
            if user_id:
                sessions = [s for s in sessions if s.user_id == user_id]
            if app_name:
                sessions = [s for s in sessions if s.app_name == app_name]
            logger.debug(f"Listed {len(sessions)} sessions (User: {user_id}, App: {app_name})")
            return sessions