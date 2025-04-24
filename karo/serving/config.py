from karo.memory.memory_manager import MemoryManagerConfig
import yaml
import importlib
import logging
import os
from typing import Dict, Optional, Tuple, Type


# Import base types needed for validation and return types
# Use absolute paths to avoid ambiguity during dynamic loading
try:
    from karo.core.base_agent import BaseAgent, BaseAgentConfig
    from karo.tools.base_tool import BaseTool
    from karo.memory.services.chromadb_service import ChromaDBConfig
    from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema
except ImportError as e:
     raise ImportError(f"Ensure Karo framework components are accessible: {e}")
# Specific implementations will be imported dynamically within the function

logger = logging.getLogger(__name__)

def _import_class(class_path: str) -> Type:
    """Dynamically imports a class from a dotted path string."""
    try:
        module_path, class_name = class_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError, ValueError) as e:
        logger.error(f"Failed to import class '{class_path}': {e}")
        raise ImportError(f"Could not import class '{class_path}'. Ensure it's correct and installed.") from e

def load_agent_from_config(config_path: str) -> Tuple[BaseAgent, Dict[str, BaseTool]]:
    """
    Loads and instantiates an agent, its components, and tools from a YAML configuration file.

    Args:
        config_path: Path to the agent definition YAML file.

    Returns:
        A tuple containing the instantiated BaseAgent and a dictionary of its available tools.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        yaml.YAMLError: If the config file has invalid YAML syntax.
        ImportError: If specified classes cannot be imported.
        ValueError: If the configuration is invalid or missing required fields.
        Exception: For other unexpected errors during instantiation.
    """
    logger.info(f"Loading agent configuration from: {config_path}")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Agent configuration file not found: {config_path}")

    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration file '{config_path}': {e}")
        raise

    if not isinstance(config_data, dict):
        raise ValueError("Invalid configuration format: Root should be a dictionary.")

    # --- Prepare Provider Config ---
    provider_config_dict = config_data.get('provider_config')
    if not provider_config_dict or not isinstance(provider_config_dict, dict):
        raise ValueError("Missing or invalid 'provider_config' section in configuration.")
    if 'type' not in provider_config_dict:
         raise ValueError("Provider config must include a 'type' field (e.g., 'openai', 'anthropic').")
    # The provider_config_dict itself will be passed to BaseAgentConfig for validation/instantiation

    # --- Prepare Memory Manager Config (Optional) ---
    memory_manager_config_obj: Optional[MemoryManagerConfig] = None
    memory_config_dict = config_data.get('memory_config')
    if memory_config_dict and isinstance(memory_config_dict, dict):
        db_type = memory_config_dict.get('db_type', 'chromadb').lower()
        if db_type == 'chromadb':
            try:
                # We need to create the nested ChromaDBConfig first
                chromadb_config = ChromaDBConfig(**memory_config_dict)
                # Then create the MemoryManagerConfig containing it
                memory_manager_config_obj = MemoryManagerConfig(
                    db_type='chromadb',
                    chromadb_config=chromadb_config
                )
                logger.info("MemoryManagerConfig prepared for ChromaDB.")
            except Exception as mem_cfg_err:
                 logger.error(f"Failed to prepare MemoryManagerConfig: {mem_cfg_err}", exc_info=True)
                 # Decide whether to raise or just skip memory
                 logger.warning("Skipping MemoryManager due to config error.")
        else:
            logger.warning(f"Unsupported db_type '{db_type}' in memory_config. Skipping MemoryManager.")
    else:
        logger.info("No memory_config found. MemoryManager will not be used.")


    # --- Prepare Conversation History Config ---
    history_config = config_data.get('history_config', {})
    max_history = history_config.get('max_history_messages', 10) # Default to 10

    # --- Prepare Prompt Builder Config ---
    # This is already expected as a dict by BaseAgentConfig
    prompt_builder_config_dict = config_data.get('prompt_config', {})
    logger.info("Prompt builder config prepared.")


    # --- Instantiate Tools (Optional) --- # This part remains the same
    tools_dict: Dict[str, BaseTool] = {}
    tools_config_list = config_data.get('tools', [])
    if isinstance(tools_config_list, list):
        for i, tool_conf in enumerate(tools_config_list):
            if not isinstance(tool_conf, dict) or 'tool_class_path' not in tool_conf:
                logger.warning(f"Invalid tool configuration at index {i}. Skipping. Config: {tool_conf}")
                continue
            tool_class_path = tool_conf['tool_class_path']
            tool_specific_config = tool_conf.get('config', {})
            try:
                ToolClass = _import_class(tool_class_path)
                if not issubclass(ToolClass, BaseTool):
                     raise TypeError(f"Class '{tool_class_path}' is not a subclass of BaseTool.")
                # Pass specific config if the tool's __init__ accepts it
                # This requires tools to handle their own config dict or specific args
                tool_instance = ToolClass(config=tool_specific_config)
                tool_name = tool_instance.get_name()
                if tool_name in tools_dict:
                     logger.warning(f"Duplicate tool name '{tool_name}'. Overwriting previous instance.")
                tools_dict[tool_name] = tool_instance
                logger.info(f"Tool '{tool_name}' ({tool_class_path}) instantiated.")
            except (ImportError, TypeError, Exception) as e:
                logger.error(f"Failed to instantiate tool '{tool_class_path}': {e}", exc_info=True)
                # Decide whether to raise error or just skip the tool
                # raise ValueError(f"Failed to instantiate tool: {tool_class_path}") from e
    else:
        logger.warning("Invalid 'tools' format in config (expected a list). No tools loaded.")

    # --- Load Agent Class and Schemas --- # This part remains the same
    agent_class_path = config_data.get('agent_class_path')
    input_schema_path = config_data.get('input_schema_path')
    output_schema_path = config_data.get('output_schema_path')

    if not agent_class_path or not output_schema_path: # Input schema defaults in BaseAgentConfig
        raise ValueError("Configuration must include 'agent_class_path' and 'output_schema_path'.")

    AgentClass = _import_class(agent_class_path)
    OutputSchemaClass = _import_class(output_schema_path)
    InputSchemaClass = _import_class(input_schema_path) if input_schema_path else BaseInputSchema

    if not issubclass(AgentClass, BaseAgent):
        raise TypeError(f"Class '{agent_class_path}' is not a subclass of BaseAgent.")
    if not issubclass(OutputSchemaClass, BaseOutputSchema):
         raise TypeError(f"Class '{output_schema_path}' is not a subclass of BaseOutputSchema.")
    if not issubclass(InputSchemaClass, BaseInputSchema):
         raise TypeError(f"Class '{input_schema_path}' is not a subclass of BaseInputSchema.")

    # --- Instantiate Agent Config and Agent ---
    try:
        # Pass the prepared config objects/dicts to BaseAgentConfig
        agent_config = BaseAgentConfig(
            provider_config=provider_config_dict, # Pass the dict for provider config
            memory_manager_config=memory_manager_config_obj, # Pass the MemoryManagerConfig object or None
            max_history_messages=max_history,
            input_schema=InputSchemaClass,
            output_schema=OutputSchemaClass,
            prompt_builder_config=prompt_builder_config_dict, # Pass the dict for prompt builder
            memory_query_results=config_data.get('memory_query_results', 3)
        )
        # BaseAgent.__init__ will now instantiate components from the agent_config
        agent_instance = AgentClass(config=agent_config)
        logger.info(f"Agent '{agent_instance.__class__.__name__}' instantiated successfully.")
    except Exception as e:
        logger.error(f"Failed to instantiate agent or its config: {e}", exc_info=True)
        raise ValueError("Failed during agent/config instantiation.") from e

    return agent_instance, tools_dict