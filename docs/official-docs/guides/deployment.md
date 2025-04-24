# Guide: Deploying Karo Agents via Docker

This guide explains how to containerize your Karo agent application using Docker, allowing you to run it consistently locally or deploy it to any container hosting platform (like Google Cloud Run, AWS Fargate, Kubernetes, etc.).

## Prerequisites

*   Karo framework (`karo`) code available.
*   Docker installed and running ([Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine).
*   Required environment variables available on your host machine for testing (e.g., `OPENAI_API_KEY`, `KARO_JWT_SECRET`).
*   Serving dependencies installed locally if you need to run `karo generate-token` (run `poetry install --with serve` in `karo`).

## Overview

We provide a `Dockerfile` that packages the Karo FastAPI server and its dependencies. You build this Dockerfile to create an image, which can then be run as a container. The container runs the `karo serve` command internally, loading an agent configuration specified via an environment variable or volume mount. This makes your agent portable and easy to deploy.

## 1. Agent Configuration (YAML)

You define the agent to be served using a YAML configuration file (e.g., `agent_definition.yaml`). This file specifies the agent class, components, schemas, prompt, and tools.

**Important for Docker:**
*   **Paths:** Paths within this file (e.g., for ChromaDB `path`, tool `file_path` referenced in prompts or tool configs) must be valid *inside* the container. Use paths relative to the application root (`/app`) or standard container paths like `/data`.
*   **Volume Mounting (Recommended):** Instead of copying your specific `agent_definition.yaml` and data files (like `orders.csv`) into the image during build, it's highly recommended to mount them into the container at runtime using Docker volumes (`-v` flag). This keeps your image generic and allows you to easily change configurations or data without rebuilding.

**Example (`agent_definition.yaml` - using conventional container paths):**

```yaml
# Sample Agent Definition for Karo Serving (Container Paths)
agent_class_path: karo.karo.core.base_agent.BaseAgent
input_schema_path: karo.karo.schemas.base_schemas.BaseInputSchema
output_schema_path: karo.examples.order-chatbot.main.OrderBotOutputSchema

provider_config:
  type: openai
  model: gpt-4o-mini

memory_config:
  db_type: chromadb
  path: /app/data/.karo_orderbot_db # Path inside container - mount a host volume here for persistence
  collection_name: orderbot_faq

history_config:
  max_history_messages: 10

prompt_config:
  role_description: |
    You are an Order Support Chatbot...
    (Prompt text here)
    ...populate 'tool_parameters' with 'file_path' ('/app/data/orders.csv')... # Mount orders.csv to /app/data/orders.csv

tools:
  - tool_class_path: karo.examples.order-chatbot.csv_order_reader_tool.CsvOrderReaderTool
    config: {}

memory_query_results: 3
```
*(See `karo/examples/order-chatbot/agent_definition.yaml` for a full example)*

## 2. Dockerfile and .dockerignore

A `Dockerfile` and `.dockerignore` file are provided in the `karo` directory.

*   **`Dockerfile`:** Uses a multi-stage build to install dependencies using Poetry and copies the application code into a slim Python image. It sets the default `CMD` to run `karo serve`, using the `KARO_AGENT_CONFIG_PATH` environment variable (defaulting to `/app/examples/order-chatbot/agent_definition.yaml`).
*   **`.dockerignore`:** Excludes unnecessary files like `.git`, `.venv`, `__pycache__` to keep the image size small and avoid copying sensitive information.

## 3. Building the Docker Image

Navigate to the `karo` directory in your terminal and run the build command:

```bash
# In karo directory
docker build -t karo-agent-server:latest .
```

*   Replace `karo-agent-server:latest` with your desired image name and tag (e.g., `gcr.io/my-project/karo-orderbot:v1.0` if pushing to Google Container Registry).

## 4. Running the Container Locally

To test the built image locally using `docker run`:

```bash
# Make sure KARO_JWT_SECRET and OPENAI_API_KEY are set in your *host* environment
# or pass them explicitly with -e

# Example 1: Running with the default config baked into the image
# (Assumes the default config and its data paths are valid inside the image)
docker run -p 8000:8000 \
  -e KARO_JWT_SECRET="${KARO_JWT_SECRET}" \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  --rm --name karo_server_local \
  karo-agent-server:latest

# Example 2: Mounting local config and data files (Recommended)
# Assumes you are in the karo-redone directory (parent of karo)
# 1. Create a directory for persistent DB data on host: mkdir -p ./karo_data/db
# 2. Create a directory for config/data mounts: mkdir -p ./karo_data/config
# 3. Copy your agent_definition.yaml, orders.csv, faq_data.json into ./karo_data/config/
docker run -p 8000:8000 \
  -e KARO_JWT_SECRET="${KARO_JWT_SECRET}" \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -e KARO_AGENT_CONFIG_PATH="/app/config/agent_definition.yaml" `# Tells serve command where to find config inside container` \
  # Mount your config file (read-only)
  -v "$(pwd)/karo_data/config/agent_definition.yaml:/app/config/agent_definition.yaml:ro" \
  # Mount your data files (read-only)
  -v "$(pwd)/karo_data/config/orders.csv:/app/data/orders.csv:ro" \
  -v "$(pwd)/karo_data/config/faq_data.json:/app/data/faq_data.json:ro" \
  # Mount a host directory to persist the ChromaDB data
  -v "$(pwd)/karo_data/db:/app/data/.karo_orderbot_db" \
  --rm --name karo_server_local \
  karo-agent-server:latest
```

*   `-p 8000:8000`: Maps port 8000 inside the container to port 8000 on your host.
*   `-e VAR_NAME="VALUE"`: Sets environment variables inside the container. **Crucially, set `KARO_JWT_SECRET` and any required API keys.**
*   `-v /host/path:/container/path:ro`: Mounts a file or directory from your host into the container. Use `:ro` for read-only mounts (good for config/input data). Use a writable mount for data that needs to persist (like the database directory). This allows changing config/data without rebuilding.
*   `--rm`: Automatically removes the container when it stops.
*   `--name`: Assigns a name to the running container.

## 5. API Authentication (JWT)

The server running inside the container requires JWT authentication.

*   **Secret Key:** Ensure the `KARO_JWT_SECRET` environment variable passed to `docker run` matches the secret used to generate your tokens.
*   **Generating Tokens:** Use the CLI on your host machine (where Karo is installed):
    ```bash
    # Run from the project root (e.g., karo-redone)
    python -m karo.karo.cli.main generate-token --expires-in 1h
    ```
    Copy the generated token.

## 6. Interacting with the API (`/invoke`)

Send `POST` requests to `http://127.0.0.1:8000/invoke` (or the appropriate host/port if changed).

**Example using `curl`:**

```bash
curl -X POST http://127.0.0.1:8000/invoke \
-H "Content-Type: application/json" \
-H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
-d '{
  "chat_message": "What is the status for ORD1002, email is bob@example.com?"
}'
```

*(Replace `<YOUR_JWT_TOKEN>` with the actual token)*

Refer to the API Models (`serving/models.py`) for the expected request (`InvokeRequest`) and response (`InvokeResponse`) structures.

## 7. Deploying to Hosting Platforms

Once you have built and tested your Docker image, you can push it to a container registry (like Google Artifact Registry, Docker Hub, AWS ECR) and deploy it to your preferred hosting platform: