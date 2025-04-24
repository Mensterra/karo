import logging
import logging.handlers
import os
from typing import Optional

# Default logging format
LOGGING_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s'

def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_format: str = LOGGING_FORMAT,
    max_bytes: int = 10*1024*1024, # 10 MB
    backup_count: int = 5
):
    """
    Configures the root logger for the Karo application.

    Args:
        level: The logging level (e.g., logging.INFO, logging.DEBUG).
        log_file: Optional path to a file for logging. If None, logs to stderr.
        log_format: The format string for log messages.
        max_bytes: Maximum size in bytes for log file before rotation.
        backup_count: Number of backup log files to keep.
    """
    root_logger = logging.getLogger()
    # Clear existing handlers to avoid duplicate logs if called multiple times
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter(log_format)

    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir: # Check if path includes a directory
            os.makedirs(log_dir, exist_ok=True)

        # Use RotatingFileHandler for file logging
        handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        print(f"Logging configured to file: {log_file}") # Print to console during setup
    else:
        # Use StreamHandler for stderr logging
        handler = logging.StreamHandler()
        print(f"Logging configured to stderr.") # Print to console during setup

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    logging.info(f"Logging setup complete. Level: {logging.getLevelName(level)}, Destination: {'File' if log_file else 'stderr'}")