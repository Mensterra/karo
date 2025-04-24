# --- Builder Stage ---
FROM python:3.13-slim as builder

# Set environment variables for non-interactive use and no venv creation
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    # Pin Poetry version for reproducibility
    POETRY_VERSION=1.8.3

# Install poetry
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# Set work directory
WORKDIR /app

# Copy only dependency definition files to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Install dependencies including the 'serve' group and base dependencies
# Exclude development dependencies
RUN poetry install --no-dev --extras serve --no-root

# --- Final Stage ---
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV APP_HOME=/app
WORKDIR $APP_HOME

# Copy installed dependencies from builder stage's site-packages
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
# Copy potentially needed executables installed by dependencies (less common)
# COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the application code from the current directory to the workdir
# Ensure .dockerignore is present in the build context (karo directory)
COPY . $APP_HOME

# Expose the port the app runs on (should match the port in CMD)
EXPOSE 8000

# Define the default agent config path within the container
# Users can override this with -e KARO_AGENT_CONFIG_PATH=/path/to/mounted/config.yaml
ENV KARO_AGENT_CONFIG_PATH=/app/examples/order-chatbot/agent_definition.yaml

# Define the command to run the application using the CLI entrypoint
# Runs the server on 0.0.0.0 to be accessible from outside the container
CMD ["python", "-m", "karo.karo.cli.main", "serve", "--config", "${KARO_AGENT_CONFIG_PATH}", "--host", "0.0.0.0", "--port", "8000"]

# Note: For production, consider using gunicorn:
# CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "karo.karo.serving.server:app", "--bind", "0.0.0.0:8000"]
# This would require adding gunicorn to the [serve] dependencies.