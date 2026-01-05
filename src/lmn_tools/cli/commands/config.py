"""
Configuration management commands.

Provides commands for viewing and managing lmn configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.core.config import LMCredentials, get_settings, reset_settings

app = typer.Typer(help="Manage lmn configuration")
console = Console()


@app.command("show")
def show_config() -> None:
    """Show current configuration."""
    settings = get_settings()

    # General settings
    console.print("\n[bold cyan]General Settings[/bold cyan]")
    table = Table(show_header=False, box=None)
    table.add_column("Setting", style="dim")
    table.add_column("Value")

    table.add_row("Config directory", str(settings.config_dir))
    table.add_row("Cache directory", str(settings.cache_dir))
    table.add_row("Debug mode", str(settings.debug))
    table.add_row("Log level", settings.log_level)
    console.print(table)

    # LogicMonitor settings
    console.print("\n[bold cyan]LogicMonitor API[/bold cyan]")
    lm_table = Table(show_header=False, box=None)
    lm_table.add_column("Setting", style="dim")
    lm_table.add_column("Value")

    lm_table.add_row("Company", settings.company or "[dim]Not set[/dim]")
    if settings.access_id:
        lm_table.add_row("Access ID", f"{settings.access_id[:8]}...")
    else:
        lm_table.add_row("Access ID", "[dim]Not set[/dim]")
    lm_table.add_row("Access Key", "[dim]****[/dim]" if settings.access_key.get_secret_value() else "[dim]Not set[/dim]")
    lm_table.add_row("API Timeout", f"{settings.api_timeout}s")
    console.print(lm_table)

    # Status
    console.print()
    if settings.has_credentials:
        console.print("[green]✓ LogicMonitor credentials configured[/green]")
    else:
        console.print("[yellow]⚠ LogicMonitor credentials not configured[/yellow]")
        console.print("\nSet these environment variables:")
        console.print("  export LM_COMPANY=your-company")
        console.print("  export LM_ACCESS_ID=your-access-id")
        console.print("  export LM_ACCESS_KEY=your-access-key")


@app.command("init")
def init_config(
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing config"),
    ] = False,
) -> None:
    """Initialize configuration directories."""
    settings = get_settings()

    # Create directories
    settings.ensure_dirs()
    console.print(f"[green]✓[/green] Created config directory: {settings.config_dir}")
    console.print(f"[green]✓[/green] Created cache directory: {settings.cache_dir}")

    # Create example env file
    env_example = settings.config_dir / ".env.example"
    if not env_example.exists() or force:
        env_content = """# LogicMonitor API credentials
LM_COMPANY=your-company
LM_ACCESS_ID=your-access-id
LM_ACCESS_KEY=your-access-key

# Optional settings
LM_API_TIMEOUT=30
LM_DEBUG=false
LM_LOG_LEVEL=INFO
"""
        env_example.write_text(env_content)
        console.print(f"[green]✓[/green] Created example env file: {env_example}")

    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"1. Copy {env_example} to .env in your project")
    console.print("2. Fill in your LogicMonitor credentials")
    console.print("3. Run 'lmn config show' to verify")


@app.command("test")
def test_connection() -> None:
    """Test LogicMonitor API connection."""
    settings = get_settings()

    if not settings.has_credentials:
        console.print("[red]✗ LogicMonitor credentials not configured[/red]")
        console.print("Run 'lmn config show' for setup instructions")
        raise typer.Exit(1)

    console.print(f"Testing connection to {settings.company}.logicmonitor.com...")

    try:
        from lmn_tools.api.client import LMClient

        client = LMClient.from_credentials(settings.credentials)  # type: ignore

        # Try a simple API call
        response = client.get("/device/devices", params={"size": 1})
        total = response.get("data", {}).get("total", 0)

        console.print(f"[green]✓ Connected successfully![/green]")
        console.print(f"  Found {total} devices in LogicMonitor")

    except Exception as e:
        console.print(f"[red]✗ Connection failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("path")
def show_paths() -> None:
    """Show configuration file paths."""
    settings = get_settings()

    console.print("\n[bold]Configuration Paths:[/bold]")
    console.print(f"  Config directory: {settings.config_dir}")
    console.print(f"  Cache directory: {settings.cache_dir}")

    # Check which paths exist
    console.print("\n[bold]Existing Files:[/bold]")
    config_files = list(settings.config_dir.glob("*")) if settings.config_dir.exists() else []
    if config_files:
        for f in config_files:
            console.print(f"  {f}")
    else:
        console.print("  [dim]No config files found[/dim]")


@app.command("reset")
def reset_config_cache() -> None:
    """Reset cached configuration (reload from environment)."""
    reset_settings()
    console.print("[green]✓ Configuration cache reset[/green]")
    console.print("Run 'lmn config show' to see current configuration")
