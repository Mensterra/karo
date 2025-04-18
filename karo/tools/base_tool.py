from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Type, Any, Optional

class BaseToolInputSchema(BaseModel):
    """Base schema for tool inputs. Tools should subclass this."""
    pass

class BaseToolOutputSchema(BaseModel):
    """Base schema for tool outputs. Tools should subclass this."""
    success: bool = True
    error_message: Optional[str] = None

class BaseTool(ABC):
    """
    Abstract Base Class for tools within the Karo framework.
    Defines the basic structure and interface for tools that agents can use.
    """

    # --- Class attributes for schema definition ---
    # Subclasses MUST define these
    input_schema: Type[BaseToolInputSchema]
    output_schema: Type[BaseToolOutputSchema]

    # --- Optional descriptive attributes ---
    name: Optional[str] = None # A unique name for the tool
    description: Optional[str] = None # Description for the LLM to understand the tool's purpose

    @abstractmethod
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize the tool, potentially with configuration.
        """
        pass

    @abstractmethod
    def run(self, input_data: BaseToolInputSchema) -> BaseToolOutputSchema:
        """
        Executes the tool's main logic.

        Args:
            input_data: An instance of the tool's specific input schema.

        Returns:
            An instance of the tool's specific output schema.
            Should include success status and potentially an error message on failure.
        """
        raise NotImplementedError("Tool subclass must implement the 'run' method.")

    # --- Helper methods for schema access ---
    @classmethod
    def get_input_schema(cls) -> Type[BaseToolInputSchema]:
        if not hasattr(cls, 'input_schema'):
            raise NotImplementedError(f"Tool '{cls.__name__}' must define an 'input_schema' class attribute.")
        return cls.input_schema

    @classmethod
    def get_output_schema(cls) -> Type[BaseToolOutputSchema]:
        if not hasattr(cls, 'output_schema'):
            raise NotImplementedError(f"Tool '{cls.__name__}' must define an 'output_schema' class attribute.")
        return cls.output_schema

    @classmethod
    def get_name(cls) -> str:
        """Returns the tool's name, defaulting to the class name if not set."""
        return cls.name or cls.__name__

    @classmethod
    def get_description(cls) -> Optional[str]:
        """Returns the tool's description."""
        return cls.description