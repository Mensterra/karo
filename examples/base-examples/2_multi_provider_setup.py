import os
from dotenv import load_dotenv
from pydantic import SecretStr

# Import Karo components
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
from karo.providers.anthropic_provider import AnthropicProvider, AnthropicProviderConfig  # Import Anthropic
from karo.providers.ollama_provider import OllamaProvider, OllamaProviderConfig
from karo.prompts.system_prompt_builder import SystemPromptBuilder
from karo.schemas.base_schemas import BaseInputSchema

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Ensure you have OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY (for Gemini), and OLLAMA_BASE_URL in your .env file

# 1. OpenAI Configuration
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("Warning: OPENAI_API_KEY not found in environment variables.")
openai_config = OpenAIProviderConfig(
    model="gpt-4o-mini",
    api_key=SecretStr(openai_api_key) if openai_api_key else None,
)

# 2. Anthropic Configuration
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key:
    print("Warning: ANTHROPIC_API_KEY not found in environment variables.")
anthropic_config = AnthropicProviderConfig(
    model="claude-3-haiku-20240307",  # Use a cost-effective model
    api_key=SecretStr(anthropic_api_key) if anthropic_api_key else None,
)

# 3. Gemini Configuration (using OpenAIProvider with compatibility endpoint)
gemini_api_key = os.getenv("GOOGLE_API_KEY")  # Google uses GOOGLE_API_KEY
if not gemini_api_key:
    print("Warning: GOOGLE_API_KEY not found in environment variables (needed for Gemini).")
gemini_config = OpenAIProviderConfig(
    model="gemini-1.5-flash-latest",  # Or other compatible Gemini model
    api_key=SecretStr(gemini_api_key) if gemini_api_key else None,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",  # Gemini's OpenAI-compatible endpoint
)

# 4. Ollama Configuration
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
if not ollama_base_url:
    print("Warning: OLLAMA_BASE_URL not found in environment variables. Using default http://localhost:11434")
ollama_config = OllamaProviderConfig(
    model="llama2",
    base_url=ollama_base_url if ollama_base_url else "http://localhost:11434",
)

# --- Provider Initialization ---
providers = {}
try:
    if openai_config.api_key:
        providers["openai"] = OpenAIProvider(config=openai_config)
        print(f"Initialized OpenAI Provider with model: {providers['openai'].get_model_name()}")
    else:
        print("Skipping OpenAI initialization (no API key).")
except Exception as e:
    print(f"Error initializing OpenAI Provider: {e}")

try:
    if anthropic_config.api_key:
        providers["anthropic"] = AnthropicProvider(config=anthropic_config)
        print(f"Initialized Anthropic Provider with model: {providers['anthropic'].get_model_name()}")
    else:
        print("Skipping Anthropic initialization (no API key).")
except Exception as e:
    print(f"Error initializing Anthropic Provider: {e}")

try:
    if gemini_config.api_key:
        # Use OpenAIProvider for Gemini's compatible endpoint
        providers["gemini"] = OpenAIProvider(config=gemini_config)
        print(f"Initialized Gemini Provider (via OpenAI compatibility) with model: {providers['gemini'].get_model_name()}")
    else:
        print("Skipping Gemini initialization (no API key).")
except Exception as e:
    print(f"Error initializing Gemini Provider (via OpenAI compatibility): {e}")

try:
    # Initialize Ollama provider
    providers["ollama"] = OllamaProvider(config=ollama_config)
    print(f"Initialized Ollama Provider with model: {providers['ollama'].get_model_name()}")
except Exception as e:
    print(f"Error initializing Ollama Provider: {e}")


# --- Agent Setup & Testing Loop ---
print("\n--- Testing Initialized Providers ---")

for provider_key, selected_provider in providers.items():
    print(f"\n--- Running Agent with {provider_key.upper()} ---")

    # Basic Prompt Builder
    prompt_builder = SystemPromptBuilder(
        role_description=f"You are a helpful assistant running on the {provider_key} provider.",  # Use the loop variable 'provider_key'
        core_instructions="Answer concisely.",
    )

    # Agent Config
    agent_config = BaseAgentConfig(
        provider_config=selected_provider.config,
        prompt_builder_config={
            "role_description": f"You are a helpful assistant running on the {provider_key} provider.",
            "core_instructions": "Answer concisely.",
        },
    )
    # Create Agent
    agent = BaseAgent(config=agent_config)

    # Run Agent
    user_message = "What is the capital of France?"
    input_data = BaseInputSchema(chat_message=user_message)
    print(f"User: {user_message}")

    try:
        result = agent.run(input_data)
        if hasattr(result, "response_message"):
            print(f"Agent ({provider_key}): {result.response_message}")  # Use loop variable
        else:
            print(f"Agent ({provider_key}) Raw Output: {result}")  # Use loop variable
    except Exception as e:
        print(f"Agent ({provider_key}) Error: {e}")  # Use loop variable

# End of loop
if not providers:
    print("\nNo providers were successfully initialized. Cannot run agent tests.")

print("\nMulti-provider setup example finished.")