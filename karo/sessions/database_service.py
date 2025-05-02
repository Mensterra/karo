import logging
import uuid
import json # For storing state as JSON
from datetime import datetime, timezone
from typing import Dict, Optional, List, Any

# SQLAlchemy imports
from sqlalchemy import create_engine, func, inspect, select, delete, update
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column, relationship, Session as DbSessionType, selectinload
from sqlalchemy import String, Text, DateTime, JSON, ForeignKey, MetaData
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, NoResultFound

# Your framework's base classes and models
from karo.sessions.service import BaseSessionService # Adjust path if needed
from karo.sessions.session import BaseSession                     # Adjust path if needed
from karo.sessions.event import BaseEvent                         # Adjust path if needed

logger = logging.getLogger(__name__)

# --- Database Schema Definition using SQLAlchemy ORM ---

class Base(DeclarativeBase):
    """Base class for our database tables."""
    pass

class DbSession(Base):
    """SQLAlchemy ORM model for storing session data."""
    __tablename__ = "karo_sessions" # Choose a table name

    # Match BaseSession fields
    id: Mapped[str] = mapped_column(String(50), primary_key=True) # Length based on f"sid_{uuid.uuid4()}"
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    app_name: Mapped[str] = mapped_column(String(255), index=True)
    state: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default={}) # Store state as JSON
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_update_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationship to events (optional but useful for ORM features)
    # cascade="all, delete-orphan" means deleting a session deletes its events
    events: Mapped[List["DbEvent"]] = relationship(
        "DbEvent",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="DbEvent.timestamp" # Keep events ordered
    )

    def __repr__(self):
        return f"<DbSession(id={self.id}, user_id={self.user_id}, app_name={self.app_name})>"

    def to_pydantic(self, include_events: bool = True) -> BaseSession:
        """Converts SQLAlchemy model to Pydantic BaseSession model."""
        event_list = [db_event.to_pydantic() for db_event in self.events] if include_events else []
        return BaseSession(
            id=self.id,
            user_id=self.user_id,
            app_name=self.app_name,
            state=self.state or {}, # Ensure state is a dict
            events=event_list,
            created_at=self.created_at.replace(tzinfo=timezone.utc), # Ensure UTC
            last_update_time=self.last_update_time.replace(tzinfo=timezone.utc) # Ensure UTC
        )


class DbEvent(Base):
    """SQLAlchemy ORM model for storing event data."""
    __tablename__ = "karo_events" # Choose a table name

    # Match BaseEvent fields
    id: Mapped[str] = mapped_column(String(50), primary_key=True) # Length based on f"evt_{uuid.uuid4()}"
    role: Mapped[str] = mapped_column(String(50), nullable=False) # user, assistant, etc.
    content: Mapped[str] = mapped_column(Text, nullable=False) # Store content as simple text
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Foreign key to link to the session
    session_id: Mapped[str] = mapped_column(ForeignKey("karo_sessions.id", ondelete="CASCADE"), index=True)

    # Relationship back to the session (optional)
    session: Mapped["DbSession"] = relationship("DbSession", back_populates="events")

    def __repr__(self):
        return f"<DbEvent(id={self.id}, session_id={self.session_id}, role={self.role})>"

    def to_pydantic(self) -> BaseEvent:
        """Converts SQLAlchemy model to Pydantic BaseEvent model."""
        return BaseEvent(
            id=self.id,
            role=self.role, # Should already match Literal["user", "assistant"]
            content=self.content,
            timestamp=self.timestamp.replace(tzinfo=timezone.utc) # Ensure UTC
        )

# --- Database Session Service Implementation ---

class DatabaseSessionService(BaseSessionService):
    """
    A session service implementation using SQLAlchemy to persist sessions
    and events defined by BaseSession and BaseEvent models.
    """
    def __init__(self, db_url: str):
        """
        Initializes the DatabaseSessionService.

        Args:
            db_url: The database connection URL (e.g.,
                    "postgresql://user:pass@host/dbname",
                    "sqlite:///./sessions.db").
        """
        try:
            self.engine = create_engine(db_url, echo=False) # Set echo=True for SQL logging
            self._ensure_tables_exist()
            # expire_on_commit=False is recommended when passing ORM objects outside the session
            self.SessionFactory = sessionmaker(bind=self.engine, expire_on_commit=False)
            logger.info(f"DatabaseSessionService initialized with URL: {db_url}")
        except ImportError as e:
            logger.error(f"Missing database driver for URL '{db_url}': {e}")
            raise ValueError(f"Missing database driver for URL '{db_url}'. Please install the required package (e.g., psycopg2-binary, mysql-connector-python).") from e
        except SQLAlchemyError as e:
            logger.error(f"Failed to connect or initialize database at '{db_url}': {e}")
            raise ConnectionError(f"Failed to connect or initialize database at '{db_url}'") from e

    def _ensure_tables_exist(self):
        """Creates the necessary database tables if they don't exist."""
        logger.debug("Ensuring database tables exist...")
        metadata = Base.metadata
        try:
            metadata.create_all(self.engine)
            logger.debug("Database tables checked/created successfully.")
        except SQLAlchemyError as e:
            logger.error(f"Error creating database tables: {e}", exc_info=True)
            raise RuntimeError("Could not create database tables.") from e

    # --- Implementing BaseSessionService Methods ---

    def create_session(
        self,
        user_id: str,
        app_name: str,
        initial_state: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> BaseSession:
        """Creates and stores a new session in the database."""
        if not session_id:
            session_id = f"sid_{uuid.uuid4()}" # Generate ID consistent with BaseSession default

        db_sess: Optional[DbSession] = None
        with self.SessionFactory() as db_session:
            try:
                # Check if session with this ID already exists
                existing = db_session.get(DbSession, session_id)
                if existing:
                    logger.warning(f"Session ID '{session_id}' already exists. Returning existing session.")
                    # Detach from session before returning to avoid expiry issues if expire_on_commit=True
                    # db_session.expunge(existing) # Needed if expire_on_commit=True
                    return existing.to_pydantic(include_events=False) # Don't load events for existing

                # Create new session instance
                db_sess = DbSession(
                    id=session_id,
                    user_id=user_id,
                    app_name=app_name,
                    state=initial_state or {},
                    # created_at and last_update_time use server defaults
                )
                db_session.add(db_sess)
                db_session.commit()
                db_session.refresh(db_sess) # Load server-set defaults like timestamps
                logger.info(f"Created new session: ID={db_sess.id}, User={user_id}, App={app_name}")
                pydantic_session = db_sess.to_pydantic(include_events=False) # No events yet
                return pydantic_session
            except IntegrityError as e:
                 logger.error(f"Integrity error creating session {session_id} (possibly duplicate): {e}", exc_info=True)
                 db_session.rollback()
                 raise ValueError(f"Could not create session {session_id}, possibly due to duplicate ID.") from e
            except SQLAlchemyError as e:
                logger.error(f"Database error creating session {session_id}: {e}", exc_info=True)
                db_session.rollback()
                raise ConnectionError("Failed to create session due to database error.") from e

    def get_session(self, session_id: str) -> Optional[BaseSession]:
        """Retrieves a session and its events by its ID."""
        logger.debug(f"Attempting to retrieve session: ID={session_id}")
        with self.SessionFactory() as db_session:
            try:
                # Use .options(selectinload(DbSession.events)) for efficient event loading
                # db_sess = db_session.query(DbSession).options(selectinload(DbSession.events)).get(session_id) # If using query API
                stmt = select(DbSession).where(DbSession.id == session_id).options(selectinload(DbSession.events))
                db_sess = db_session.scalars(stmt).first()

                if db_sess:
                    logger.debug(f"Retrieved session: ID={session_id}")
                    pydantic_session = db_sess.to_pydantic(include_events=True)
                    return pydantic_session
                else:
                    logger.debug(f"Session not found: ID={session_id}")
                    return None
            except SQLAlchemyError as e:
                logger.error(f"Database error retrieving session {session_id}: {e}", exc_info=True)
                raise ConnectionError("Failed to retrieve session due to database error.") from e

    def update_session(self, session: BaseSession) -> None:
        """
        Updates an existing session's state and last_update_time in the database.
        NOTE: This method primarily updates the 'state' and 'last_update_time'.
              It does NOT synchronize the 'events' list. Use 'append_event' for events.
        """
        if not isinstance(session, BaseSession):
            raise TypeError("session must be an instance of BaseSession")

        logger.debug(f"Attempting to update session: ID={session.id}")
        with self.SessionFactory() as db_session:
            try:
                # Fetch the existing session
                db_sess = db_session.get(DbSession, session.id)
                if not db_sess:
                    logger.warning(f"Attempted to update non-existent session: ID={session.id}")
                    return # Or raise an error?

                # Update fields - *especially state*
                db_sess.state = session.state
                # Update last_update_time using database function via onupdate trigger
                # If onupdate isn't reliable or used, set manually:
                # db_sess.last_update_time = datetime.now(timezone.utc)

                db_session.commit()
                logger.debug(f"Updated session: ID={session.id}")

            except SQLAlchemyError as e:
                logger.error(f"Database error updating session {session.id}: {e}", exc_info=True)
                db_session.rollback()
                raise ConnectionError("Failed to update session due to database error.") from e

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session and its associated events by its ID."""
        logger.debug(f"Attempting to delete session: ID={session_id}")
        with self.SessionFactory() as db_session:
            try:
                # Fetch the session to ensure it exists before deleting
                db_sess = db_session.get(DbSession, session_id)
                if db_sess:
                    db_session.delete(db_sess)
                    db_session.commit()
                    logger.info(f"Deleted session: ID={session_id}")
                    return True
                else:
                    logger.warning(f"Attempted to delete non-existent session: ID={session_id}")
                    return False
            except SQLAlchemyError as e:
                logger.error(f"Database error deleting session {session_id}: {e}", exc_info=True)
                db_session.rollback()
                raise ConnectionError("Failed to delete session due to database error.") from e

    def list_sessions(self, user_id: Optional[str] = None, app_name: Optional[str] = None) -> List[BaseSession]:
        """Lists sessions, optionally filtering by user_id and/or app_name."""
        logger.debug(f"Listing sessions (User: {user_id}, App: {app_name})")
        with self.SessionFactory() as db_session:
            try:
                stmt = select(DbSession)
                if user_id:
                    stmt = stmt.where(DbSession.user_id == user_id)
                if app_name:
                    stmt = stmt.where(DbSession.app_name == app_name)
                stmt = stmt.order_by(DbSession.last_update_time.desc()) # Optional ordering

                results = db_session.scalars(stmt).all()

                # Convert to Pydantic models (without events for efficiency)
                pydantic_sessions = [db_sess.to_pydantic(include_events=False) for db_sess in results]
                logger.debug(f"Found {len(pydantic_sessions)} sessions matching criteria.")
                return pydantic_sessions
            except SQLAlchemyError as e:
                logger.error(f"Database error listing sessions: {e}", exc_info=True)
                raise ConnectionError("Failed to list sessions due to database error.") from e

    # --- Additional Method specific to persistent storage ---

    def append_event(self, session_id: str, event: BaseEvent) -> BaseEvent:
        """
        Appends a new event to the specified session and updates the
        session's last_update_time.
        """
        if not isinstance(event, BaseEvent):
            raise TypeError("event must be an instance of BaseEvent")

        logger.debug(f"Attempting to append event: ID={event.id} to session: ID={session_id}")
        with self.SessionFactory() as db_session:
            try:
                 # Check if session exists first (optional but good practice)
                session_exists = db_session.query(DbSession.id).filter_by(id=session_id).first() is not None
                if not session_exists:
                    logger.error(f"Cannot append event: Session {session_id} not found.")
                    raise ValueError(f"Session with ID {session_id} not found.")

                # Create DbEvent instance from BaseEvent
                db_event = DbEvent(
                    id=event.id,
                    session_id=session_id,
                    role=event.role,
                    content=event.content,
                    timestamp=event.timestamp # Ensure it's timezone-aware UTC
                )

                # Add the event
                db_session.add(db_event)

                # Manually trigger the update of last_update_time on the session
                # This ensures the timestamp reflects the *event append time*
                stmt = (
                    update(DbSession)
                    .where(DbSession.id == session_id)
                    .values(last_update_time=datetime.now(timezone.utc)) # Use explicit timestamp
                )
                db_session.execute(stmt)

                # Commit transaction to save event and session update
                db_session.commit()
                logger.debug(f"Appended event: ID={event.id} to session: ID={session_id}")
                return event # Return the original event object

            except IntegrityError as e:
                 logger.error(f"Integrity error appending event {event.id} to session {session_id} (duplicate event ID?): {e}", exc_info=True)
                 db_session.rollback()
                 raise ValueError(f"Could not append event {event.id}, possibly due to duplicate ID.") from e
            except SQLAlchemyError as e:
                logger.error(f"Database error appending event {event.id} to session {session_id}: {e}", exc_info=True)
                db_session.rollback()
                raise ConnectionError("Failed to append event due to database error.") from e

# --- Example Usage (Optional) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Example using SQLite in-memory for testing
    # Replace with your actual DB URL (e.g., postgresql://..., mysql://...)
    TEST_DB_URL = "sqlite:///:memory:"
    # TEST_DB_URL = "sqlite:///./test_karo_sessions.db" # For a file

    try:
        session_service = DatabaseSessionService(TEST_DB_URL)

        # --- Test Create ---
        print("--- Testing Create ---")
        initial_state = {"theme": "dark", "prefs": [1, 2]}
        session1 = session_service.create_session(
            user_id="user123",
            app_name="my_chatbot",
            initial_state=initial_state
        )
        print(f"Created session 1: {session1.id}")
        session2 = session_service.create_session(user_id="user456", app_name="my_chatbot")
        print(f"Created session 2: {session2.id}")

        # --- Test Get ---
        print("\n--- Testing Get ---")
        retrieved_session1 = session_service.get_session(session1.id)
        if retrieved_session1:
            print(f"Retrieved session 1: ID={retrieved_session1.id}, State={retrieved_session1.state}")
            assert retrieved_session1.state == initial_state
        else:
            print(f"Session {session1.id} not found!")

        # --- Test Append Event ---
        print("\n--- Testing Append Event ---")
        event1 = BaseEvent(role="user", content="Hello there!")
        event2 = BaseEvent(role="assistant", content="Hi! How can I help?")
        session_service.append_event(session1.id, event1)
        session_service.append_event(session1.id, event2)
        print(f"Appended 2 events to session {session1.id}")

        retrieved_session1_with_events = session_service.get_session(session1.id)
        if retrieved_session1_with_events:
             print(f"Retrieved session 1 events: {len(retrieved_session1_with_events.events)}")
             for ev in retrieved_session1_with_events.events:
                 print(f"  - {ev.role}: {ev.content} ({ev.timestamp})")
             assert len(retrieved_session1_with_events.events) == 2

        # --- Test Update ---
        print("\n--- Testing Update ---")
        retrieved_session1_with_events.state["theme"] = "light" # Modify state
        retrieved_session1_with_events.state["new_key"] = True
        session_service.update_session(retrieved_session1_with_events)
        print(f"Updated session {session1.id} state")

        retrieved_session1_updated = session_service.get_session(session1.id)
        if retrieved_session1_updated:
             print(f"Retrieved updated state: {retrieved_session1_updated.state}")
             assert retrieved_session1_updated.state["theme"] == "light"
             assert retrieved_session1_updated.state["new_key"] is True

        # --- Test List ---
        print("\n--- Testing List ---")
        all_sessions = session_service.list_sessions(app_name="my_chatbot")
        print(f"Total sessions for 'my_chatbot': {len(all_sessions)}")
        assert len(all_sessions) == 2

        user1_sessions = session_service.list_sessions(user_id="user123", app_name="my_chatbot")
        print(f"Sessions for user 'user123': {len(user1_sessions)}")
        assert len(user1_sessions) == 1
        assert user1_sessions[0].id == session1.id

        # --- Test Delete ---
        print("\n--- Testing Delete ---")
        deleted = session_service.delete_session(session2.id)
        print(f"Deleted session {session2.id}: {deleted}")
        assert deleted is True
        not_found_session = session_service.get_session(session2.id)
        assert not_found_session is None
        print(f"Session {session2.id} not found after delete: {not_found_session is None}")

        remaining_sessions = session_service.list_sessions(app_name="my_chatbot")
        print(f"Remaining sessions for 'my_chatbot': {len(remaining_sessions)}")
        assert len(remaining_sessions) == 1

    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")