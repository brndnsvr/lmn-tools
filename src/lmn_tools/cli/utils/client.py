"""
Client utilities for CLI commands.

Provides authenticated API client access with consistent error handling.
"""

from __future__ import annotations

import typer
from rich.console import Console

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import get_settings

# Default console for error output
_console = Console()


def get_client(console: Console | None = None) -> LMClient:
    """Get authenticated LogicMonitor API client.

    Checks for valid credentials and returns a configured client.
    Exits with error message if credentials are not configured.

    Args:
        console: Console for error output (uses default if None)

    Returns:
        Configured LMClient instance

    Raises:
        typer.Exit: If credentials not configured
    """
    console = console or _console
    settings = get_settings()

    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        console.print("Run 'lmn config show' for setup instructions")
        raise typer.Exit(1)

    return LMClient.from_credentials(settings.credentials)  # type: ignore
