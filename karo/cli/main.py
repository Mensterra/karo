import click
import sys

# Add sibling directories to path if needed for imports when run as module
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    # Import commands from other files
    from .serve_command import serve
    from .token_command import generate_token
    # Import logging setup utility
    from ..utils.logging_config import setup_logging # Use relative import
except ImportError as e:
     # This might happen if run directly without installing karo
     print(f"Import Error: {e}. Ensure karo is installed or run using 'python -m karo.karo.cli.main'")
     sys.exit(1)

# Setup basic logging for the CLI entry point itself.
# Commands can override this later using their own options.
setup_logging() # Call with defaults (INFO level to stderr)
# logger = logging.getLogger(__name__) # Get logger if needed at this level

@click.group()
def main():
    """Karo Agent Framework CLI Tool."""
    pass

# Add commands to the main group
main.add_command(serve)
main.add_command(generate_token)

if __name__ == '__main__':
    main()