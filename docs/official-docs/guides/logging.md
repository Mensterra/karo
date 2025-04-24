# Guide: Logging in Karo

Karo utilizes Python's standard `logging` module for flexible and configurable logging across the framework and applications built with it.

## Core Concepts

*   **Standard Library:** Relies on the built-in `logging` module. No custom logging framework is introduced.
*   **Loggers:** Components like `BaseAgent`, providers, tools, etc., should obtain a logger instance using `logging.getLogger(__name__)`.
*   **Configuration:** Logging behavior (level, destination, format) is configured centrally, typically once at the application's entry point.

## Configuring Logging

Karo provides a utility function to simplify common logging setups.

**`setup_logging` Function:**

Located in `karo.karo.utils.logging_config`, this function configures the root logger.

```python
from karo.karo.utils.logging_config import setup_logging
import logging

# Example: Log INFO and above to stderr (console)
setup_logging(level=logging.INFO)

# Example: Log DEBUG and above to a rotating file
# setup_logging(level=logging.DEBUG, log_file="/path/to/your/karo_app.log")

# Example: Custom format and file rotation settings
# custom_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
# setup_logging(
#     level=logging.INFO,
#     log_file="/path/to/your/karo_app.log",
#     log_format=custom_format,
#     max_bytes=5*1024*1024, # 5 MB
#     backup_count=3
# )
```

**Parameters:**

*   `level`: The minimum logging level to output (e.g., `logging.DEBUG`, `logging.INFO`, `logging.WARNING`, `logging.ERROR`, `logging.CRITICAL`). Default is `logging.INFO`.
*   `log_file`: Optional path to a file. If provided, logs are written to this file using a `RotatingFileHandler`. If `None`, logs go to stderr. Default is `None`.
*   `log_format`: The format string for log messages. Defaults to `LOGGING_FORMAT` defined in the module.
*   `max_bytes`: Max size (in bytes) of the log file before rotation (default: 10MB).
*   `backup_count`: Number of backup log files to keep during rotation (default: 5).

**Important:** Call `setup_logging` early in your application's entry point (e.g., in your main script or server startup) to ensure all subsequent log messages are captured correctly.

## Logging in the Deployment Server (`karo serve`)

The `karo serve` CLI command provides options to control logging when running the FastAPI server:

*   `--log-level LEVEL`: Sets the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Case-insensitive. Defaults to INFO.
*   `--log-file PATH`: Specifies a file path to write logs to. If omitted, logs go to stderr.

**Examples:**

```bash
# Run server with DEBUG level logging to console
python -m karo.karo.cli.main serve --config path/to/config.yaml --log-level DEBUG

# Run server with INFO level logging to a file
python -m karo.karo.cli.main serve --config path/to/config.yaml --log-level INFO --log-file /var/log/karo_agent.log
```

The `serve` command automatically calls `setup_logging` with the provided options before starting the Uvicorn server process.

## Retrieving Logs via API (`/logs`)

When the server is configured to log to a file (using `--log-file`), you can retrieve recent log entries via the `/logs` API endpoint.

**Request:**

*   **Method:** `GET`
*   **URL:** `http://<host>:<port>/logs`
*   **Headers:**
    *   `Authorization: Bearer <YOUR_JWT_TOKEN>` (Requires valid JWT authentication)
*   **Query Parameters:**
    *   `limit` (optional, integer): Maximum number of lines to return (default: 100, max: 1000).
    *   `since` (optional, string): ISO 8601 timestamp. If provided, only returns log lines *after* this time (Note: This filtering might be basic and depend on the log format containing a standard timestamp).

**Response:**

*   **Success (Status Code 200):**
    ```json
    [
      "2025-04-22 16:47:58,017 - INFO - karo.karo.serving.server - server.py:100 - Received invocation request: {'chat_message': 'Test log endpoint again'}",
      "2025-04-22 16:47:58,930 - INFO - httpx - _client.py:1025 - HTTP Request: POST https://api.openai.com/v1/embeddings \"HTTP/1.1 200 OK\"",
      "...",
      "2025-04-22 16:48:00,985 - INFO - karo.karo.serving.server - server.py:154 - Agent action 'ANSWER' requires direct response."
    ]
    ```
    (A JSON array of strings, where each string is a log line).
*   **Error (Status Code 401):** Invalid or missing JWT token.
*   **Error (Status Code 404):** Server was not started with the `--log-file` option, or the log file doesn't exist/is empty.
*   **Error (Status Code 500):** Internal server error while reading the log file.

This endpoint is useful for monitoring deployed agents or integrating log viewing into a frontend application.