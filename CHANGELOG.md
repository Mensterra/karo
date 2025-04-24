# Changelog (karo)

This changelog tracks modifications made specifically to the `karo` version of the Karo framework, starting after its duplication from the original `karo` directory.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased] - YYYY-MM-DD

### Added
- **Deployment Framework (FastAPI):**
    - Added `karo/karo/serving/` module with FastAPI server (`server.py`), API models (`models.py`), JWT authentication (`auth.py`), and agent configuration loading from YAML (`config.py`).
    - Added `karo/karo/cli/` module with `click`-based CLI (`main.py`).
    - Implemented `karo serve` command (`cli/serve_command.py`) to launch the FastAPI server, loading agents via YAML config.
    - Implemented `karo generate-token` command (`cli/token_command.py`) for creating JWT API tokens.
    - Added optional `[serve]` dependencies (`fastapi`, `uvicorn`, `python-jose`, `pyyaml`, `click`) to `pyproject.toml`.
- **Logging System:**
    - Added `karo/karo/utils/logging_config.py` with `setup_logging` function for configurable logging (stderr or file).
    - Added `--log-level` and `--log-file` options to the `karo serve` CLI command.
    - Added `/logs` API endpoint to `serving/server.py` for retrieving recent log file entries (requires JWT auth).
- **Conversation History:**
    - Added `karo/karo/memory/conversation_history.py` with `ConversationHistory` class for short-term memory buffer.
    - Added `max_history_messages` option to `BaseAgentConfig`.
    - Integrated `ConversationHistory` into `BaseAgent` for automatic history management (instantiated internally).
    - Added `BaseAgent.reset_history()` method.
- **New Example (`order-chatbot`):**
    - Created `karo/examples/order-chatbot/` with `main.py`, `csv_order_reader_tool.py`, `orders.csv`, `faq_data.json`, `agent_definition.yaml`, `pyproject.toml`, and `tutorial.md`.
    - Demonstrates external tool orchestration, FAQ retrieval via `MemoryManager`, and multi-turn conversation using `ConversationHistory`.
- **Containerization:**
    - Added `karo/Dockerfile` for building a container image of the FastAPI server.
    - Added `karo/.dockerignore` to exclude unnecessary files from the build context.
- **Session Management (In-Memory):**
    - Added `karo/karo/sessions/` module with `KaroSession`, `KaroEvent` models and `BaseSessionService`, `InMemorySessionService`.
    - Added `/karo/docs/official-docs/guides/sessions.md` documentation.

### Changed
- **BREAKING (Session Management Integration):**
    - Modified `karo/karo/serving/server.py` (`/invoke` endpoint) to integrate `InMemorySessionService` for session creation, history/state passing, and event logging.
    - Modified `karo/karo/serving/models.py` (`InvokeRequest`, `InvokeResponse`) to include `session_id`.
    - Modified `karo/karo/core/base_agent.py` (`BaseAgent`, `BaseAgentConfig`) to remove internal history management and accept history/state via the `run` method.
- **BREAKING (Tool Handling Refactor):**
    - Removed internal tool execution logic from `karo/karo/core/base_agent.py`.
    - Removed `tools` and `max_tool_iterations` from `BaseAgentConfig`.
    - `BaseAgent.run` now relies on the agent's `output_schema` to indicate tool use for external orchestration.
- Updated `karo/karo/providers/` (OpenAI, Anthropic) to remove unused tool parameters.
- Refactored `karo/examples/base-examples/4_agent_with_tools.py` to use external tool orchestration.
- Refactored `karo/examples/order-chatbot/main.py` to use internal `ConversationHistory`.
- Updated documentation files within `karo/docs/` (deployment, logging, agents, tools, quickstart, core concepts) to reflect refactored tool handling, new features (history, logging, deployment server), and Dockerization.
- Changed imports in core modules (`base_agent.py`, `memory_manager.py`, `serving/config.py`) and examples (`csv_order_reader_tool.py`, `order-chatbot/main.py`) to use consistent absolute paths (`karo.karo...`) to resolve Pydantic validation issues.
- Updated default paths in `karo/examples/order-chatbot/agent_definition.yaml` to be suitable for container environment (`/app/data/...`).

### Fixed
- Corrected `AttributeError` in `karo/examples/base-examples/5_system_prompt_builder_example.py`.
- Fixed import path issues causing `TypeError` during agent loading in `karo/karo/serving/config.py`.
- Fixed `NameError` for `Query` import in `karo/karo/serving/server.py`.
- Fixed `.env` file path loading in `karo/karo/cli/serve_command.py`.
- Removed unused `bot_response_for_history` variable in `karo/examples/order-chatbot/main.py` after implementing internal history management.
- Fixed Pydantic validation error in `InMemorySessionService.create_session` when handling `session_id=None`.
- Fixed extraction of assistant response content for session event logging in `karo/karo/serving/server.py`.