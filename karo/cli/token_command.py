import click
import logging
from datetime import timedelta, datetime, timezone

from karo.serving.auth import SECRET_KEY

# Assuming auth utilities are accessible
try:
    from karo.serving.auth import SECRET_KEY, create_access_token
except ImportError as e:
    raise ImportError(f"Ensure Karo serving components are accessible: {e}")

logger = logging.getLogger(__name__)

def parse_duration(duration_str: str) -> timedelta:
    """Parses a duration string (e.g., '30d', '1h', '15m') into a timedelta."""
    unit = duration_str[-1].lower()
    try:
        value = int(duration_str[:-1])
        if unit == 'd':
            return timedelta(days=value)
        elif unit == 'h':
            return timedelta(hours=value)
        elif unit == 'm':
            return timedelta(minutes=value)
        else:
            raise ValueError("Invalid duration unit. Use 'd', 'h', or 'm'.")
    except (ValueError, IndexError):
        raise ValueError(f"Invalid duration format: '{duration_str}'. Use format like '30d', '1h', '15m'.")

@click.command('generate-token')
@click.option(
    '--expires-in',
    default='30d',
    show_default=True,
    help="Token expiration duration (e.g., '30d' for 30 days, '1h' for 1 hour, '15m' for 15 minutes)."
)
@click.option(
    '--payload',
    '-p',
    multiple=True,
    help="Add custom key=value pairs to the JWT payload (e.g., -p user=admin -p scope=read)."
)
def generate_token(expires_in: str, payload: tuple):
    """
    Generate a JWT API token for accessing the Karo Agent Server.

    Requires the KARO_JWT_SECRET environment variable to be set.
    """
    if not SECRET_KEY:
        logger.error("FATAL: Environment variable KARO_JWT_SECRET is not set.")
        click.echo("Error: KARO_JWT_SECRET environment variable must be set to generate tokens.", err=True)
        raise click.Abort()

    try:
        delta = parse_duration(expires_in)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()

    # Build custom payload from options
    custom_payload = {}
    for item in payload:
        if '=' not in item:
            click.echo(f"Error: Invalid payload format '{item}'. Use key=value.", err=True)
            raise click.Abort()
        key, value = item.split('=', 1)
        custom_payload[key] = value

    try:
        token = create_access_token(data=custom_payload, expires_delta=delta)
        expires_at = datetime.now(timezone.utc) + delta
        click.echo("Generated API Token:")
        click.echo(token)
        click.echo(f"\nExpires at: {expires_at.isoformat()}")
        if custom_payload:
            click.echo(f"Custom Payload: {custom_payload}")
    except Exception as e:
        logger.error(f"Failed to generate token: {e}", exc_info=True)
        click.echo(f"Error generating token: {e}", err=True)
        raise click.Abort()