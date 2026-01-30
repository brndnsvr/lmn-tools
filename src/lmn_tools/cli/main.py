"""
Main CLI entry point for lmn-tools.

Provides the `lmn` command with subcommands for:
- config: Configuration management
- discover: Active Discovery on devices
- collect: Metric collection from devices
- datasource: DataSource management (alias: ds)
- propertysource: PropertySource management (alias: ps)
- eventsource: EventSource management (alias: es)
- configsource: ConfigSource management (alias: cs)
- topologysource: TopologySource management (alias: ts)
- device: Device management
- group: Device group management
- alert: Alert management (includes history, trends)
- alertrule: Alert rule management (alias: ar)
- chain: Escalation chain management
- integration: Integration management
- sdt: SDT/maintenance window management
- collector: Collector management
- dashboard: Dashboard management
- website: Website/synthetic monitoring
- user: User management (read-only)
- report: Report management
- api: Raw API access
- widget: Dashboard widget management
- opsnote: Operational notes management
- netscan: Network discovery scan management
- batch: Batch job management
- recipient: Recipient group management
- token: API token management
- accessgroup: Access group (RBAC) management
- audit: Audit log viewing
- topology: Topology/resource map management
- service: Service Insight management
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler

from lmn_tools import __version__
from lmn_tools.cli.commands import (
    accessgroup,
    alert,
    alertrule,
    api,
    audit,
    batch,
    chain,
    collect,
    collector,
    config,
    configsource,
    dashboard,
    datasource,
    device,
    discover,
    eventsource,
    group,
    integration,
    netscan,
    opsnote,
    propertysource,
    recipient,
    report,
    sdt,
    service,
    token,
    topology,
    topologysource,
    user,
    website,
    widget,
)
from lmn_tools.core.config import get_settings

# Main CLI app
app = typer.Typer(
    name="lmn",
    help="LogicMonitor Network Tools - Unified CLI for LM operations",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Rich console for formatted output
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"lmn version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            "-d",
            envvar="LM_DEBUG",
            help="Enable debug output",
        ),
    ] = False,
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to config file",
        ),
    ] = None,
) -> None:
    """
    LMN - LogicMonitor Network Tools.

    A unified CLI for LogicMonitor operations including device discovery,
    metric collection, dashboard management, and DataSource management.
    """
    # Configure logging
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=debug, rich_tracebacks=True)],
    )

    # Update settings with debug flag
    settings = get_settings()
    if debug:
        settings.debug = True


# Register command groups
app.add_typer(config.app, name="config", help="Manage lmn configuration")
app.add_typer(discover.app, name="discover", help="Run Active Discovery on devices")
app.add_typer(collect.app, name="collect", help="Collect metrics from devices")

# LogicMonitor API management commands
app.add_typer(datasource.app, name="datasource", help="Manage DataSources")
app.add_typer(datasource.app, name="ds", help="Manage DataSources (alias)", hidden=True)
app.add_typer(propertysource.app, name="propertysource", help="Manage PropertySources")
app.add_typer(propertysource.app, name="ps", help="Manage PropertySources (alias)", hidden=True)
app.add_typer(eventsource.app, name="eventsource", help="Manage EventSources")
app.add_typer(eventsource.app, name="es", help="Manage EventSources (alias)", hidden=True)
app.add_typer(configsource.app, name="configsource", help="Manage ConfigSources")
app.add_typer(configsource.app, name="cs", help="Manage ConfigSources (alias)", hidden=True)
app.add_typer(topologysource.app, name="topologysource", help="Manage TopologySources")
app.add_typer(topologysource.app, name="ts", help="Manage TopologySources (alias)", hidden=True)
app.add_typer(device.app, name="device", help="Manage devices")
app.add_typer(group.app, name="group", help="Manage device groups")
app.add_typer(alert.app, name="alert", help="Manage alerts")
app.add_typer(alertrule.app, name="alertrule", help="Manage alert rules")
app.add_typer(alertrule.app, name="ar", help="Manage alert rules (alias)", hidden=True)
app.add_typer(chain.app, name="chain", help="Manage escalation chains")
app.add_typer(integration.app, name="integration", help="Manage integrations")
app.add_typer(sdt.app, name="sdt", help="Manage SDT (maintenance windows)")
app.add_typer(collector.app, name="collector", help="View collectors")
app.add_typer(dashboard.app, name="dashboard", help="Manage dashboards")
app.add_typer(website.app, name="website", help="Manage website monitors (synthetic)")
app.add_typer(user.app, name="user", help="View users (read-only)")
app.add_typer(report.app, name="report", help="View reports")
app.add_typer(api.app, name="api", help="Raw API access")

# New API resource commands
app.add_typer(widget.app, name="widget", help="Manage dashboard widgets")
app.add_typer(opsnote.app, name="opsnote", help="Manage operational notes")
app.add_typer(netscan.app, name="netscan", help="Manage network discovery scans")
app.add_typer(batch.app, name="batch", help="View batch jobs")
app.add_typer(recipient.app, name="recipient", help="Manage recipient groups")
app.add_typer(token.app, name="token", help="Manage API tokens")
app.add_typer(accessgroup.app, name="accessgroup", help="Manage access groups (RBAC)")
app.add_typer(audit.app, name="audit", help="View audit logs")
app.add_typer(topology.app, name="topology", help="Manage topology maps")
app.add_typer(service.app, name="service", help="Manage services (Service Insight)")


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold]lmn[/bold] version {__version__}")
    console.print("LogicMonitor Network Tools")


@app.command()
def info() -> None:
    """Show configuration and environment info."""
    settings = get_settings()

    console.print("\n[bold]Configuration:[/bold]")
    console.print(f"  Config directory: {settings.config_dir}")
    console.print(f"  Cache directory: {settings.cache_dir}")
    console.print(f"  Debug mode: {settings.debug}")
    console.print(f"  Log level: {settings.log_level}")

    console.print("\n[bold]LogicMonitor API:[/bold]")
    if settings.has_credentials:
        console.print(f"  Company: {settings.company}")
        console.print(f"  Access ID: {settings.access_id[:8]}..." if settings.access_id else "  Access ID: Not set")
        console.print(f"  API Timeout: {settings.api_timeout}s")
    else:
        console.print("  [yellow]Credentials not configured[/yellow]")
        console.print("  Set LM_COMPANY, LM_ACCESS_ID, and LM_ACCESS_KEY environment variables")


def cli() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    cli()
