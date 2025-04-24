from typing import Optional
import click
import click
import click
from karo.utils.logging_config import setup_logging
import uvicorn
import os
import logging
from dotenv import load_dotenv
# Import the setup function


# Assuming logging setup utility will be created later
# from karo.karo.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

@click.command()
@click.option(
    '--config', '-c',
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to the agent definition YAML configuration file."
)
@click.option(
    '--host',
    default='127.0.0.1',
    show_default=True,
    help="Host address to bind the server to."
)
@click.option(
    '--port',
    default=8000,
    type=int,
    show_default=True,
    help="Port number to bind the server to."
)
@click.option(
    '--workers',
    default=1,
    type=int,
    show_default=True,
    help="Number of Uvicorn worker processes."
)
@click.option(
    '--log-level',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False),
    default='INFO',
    show_default=True,
    help="Set the logging level."
)
@click.option(
    '--log-file',
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Path to a file to write logs to. If not provided, logs go to stderr."
)
def serve(config: str, host: str, port: int, workers: int, log_level: str, log_file: Optional[str]):
    """
    Serve a Karo agent defined by a configuration file via a FastAPI server.
    """
    # 0. Setup Logging FIRST
    # Convert string level to logging level constant
    log_level_int = getattr(logging, log_level.upper(), logging.INFO)
    setup_logging(level=log_level_int, log_file=log_file) # Use the setup function

    logger.info(f"Attempting to serve agent from config: {config}")

    # 1. Load .env file from the karo directory
    #    Assumes the command is run from the parent directory (/Users/darkmage/karo-redone)
    #    or that the relative path works correctly.
    dotenv_path = os.path.join('karo', '.env') # Path relative to CWD where command is run
    if os.path.exists(dotenv_path):
        loaded = load_dotenv(dotenv_path=dotenv_path)
        logger.info(f"Loaded environment variables from {dotenv_path}: {loaded}")
    else:
        logger.warning(f".env file not found at '{dotenv_path}'. Relying on system environment variables.")


    # 1. Check for JWT Secret Key
    jwt_secret = os.getenv("KARO_JWT_SECRET")
    if not jwt_secret:
        logger.error("FATAL: Environment variable KARO_JWT_SECRET is not set.")
        click.echo("Error: KARO_JWT_SECRET environment variable must be set for API authentication.", err=True)
        raise click.Abort() # Exit CLI

    # 2. Set environment variables for server
    # Use absolute paths to avoid issues with CWD
    abs_config_path = os.path.abspath(config)
    os.environ["KARO_AGENT_CONFIG_PATH"] = abs_config_path
    logger.info(f"Set KARO_AGENT_CONFIG_PATH to: {abs_config_path}")
    if log_file:
        abs_log_path = os.path.abspath(log_file)
        os.environ["KARO_LOG_FILE_PATH"] = abs_log_path
        logger.info(f"Set KARO_LOG_FILE_PATH to: {abs_log_path}")
    elif "KARO_LOG_FILE_PATH" in os.environ:
        # Unset if --log-file is not provided but env var exists from previous run
        del os.environ["KARO_LOG_FILE_PATH"]
        logger.info("Unset KARO_LOG_FILE_PATH as --log-file was not specified.")


    # Logging setup is now done above

    # 4. Launch Uvicorn server
    # Note: Uvicorn needs the import string for the FastAPI app object
    app_import_string = "karo.karo.serving.server:app"
    logger.info(f"Starting Uvicorn server for '{app_import_string}' on {host}:{port} with {workers} worker(s)...")

    try:
        uvicorn.run(
            app_import_string,
            host=host,
            port=port,
            workers=workers,
            # reload=True # Useful for development, but disable for production/multiple workers
        )
    except Exception as e:
         logger.error(f"Failed to start Uvicorn server: {e}", exc_info=True)
         click.echo(f"Error starting server: {e}", err=True)
         raise click.Abort()