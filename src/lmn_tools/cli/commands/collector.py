"""
Collector management commands.

Provides commands for viewing LogicMonitor collectors.
"""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import get_client
from lmn_tools.services.collectors import (
    CollectorService,
    CollectorStatus,
    collector_service,
)

app = typer.Typer(help="Manage collectors")
console = Console()


def _get_service() -> CollectorService:
    """Get collector service."""
    return collector_service(get_client(console))


def _status_name(status: str | int) -> str:
    """Convert collector status to display name."""
    if isinstance(status, int):
        try:
            return CollectorStatus(status).name.lower()
        except ValueError:
            return str(status)
    return str(status) if status else "unknown"


@app.command("list")
def list_collectors(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    status: Annotated[str | None, typer.Option("--status", "-s", help="Filter by status")] = None,
    format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, ids")
    ] = "table",
) -> None:
    """List collectors."""
    svc = _get_service()

    filters = []
    if filter:
        filters.append(filter)
    if status:
        filters.append(f"status:{status}")
    filter_str = ",".join(filters) if filters else None

    collectors = svc.list(filter=filter_str)

    if format == "json":
        console.print_json(data=collectors)
    elif format == "ids":
        for c in collectors:
            console.print(c["id"])
    else:
        table = Table(title=f"Collectors ({len(collectors)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Hostname", style="cyan")
        table.add_column("Description")
        table.add_column("Status")
        table.add_column("Version")
        table.add_column("Platform")

        for c in collectors:
            status = _status_name(c.get("status", ""))
            status_style = "green" if status == "ok" else "red"
            table.add_row(
                str(c["id"]),
                c.get("hostname", ""),
                c.get("description", ""),
                f"[{status_style}]{status}[/{status_style}]",
                c.get("build", ""),
                c.get("platform", ""),
            )
        console.print(table)


@app.command("get")
def get_collector(
    collector_id: Annotated[int, typer.Argument(help="Collector ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get collector details."""
    svc = _get_service()
    response = svc.get(collector_id)
    collector = response.get("data", response) if "data" in response else response

    if format == "json":
        console.print_json(data=collector)
        return

    console.print(
        f"\n[bold cyan]{collector.get('hostname', 'N/A')}[/bold cyan] (ID: {collector_id})"
    )
    console.print()

    status = _status_name(collector.get("status", ""))
    status_style = "green" if status == "ok" else "red"

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Description", collector.get("description", "N/A"))
    detail_table.add_row("Status", f"[{status_style}]{status}[/{status_style}]")
    detail_table.add_row("Build", collector.get("build", "N/A"))
    detail_table.add_row("Platform", collector.get("platform", "N/A"))
    detail_table.add_row("Up Time", str(collector.get("upTime", "N/A")))
    detail_table.add_row("Number of Hosts", str(collector.get("numberOfHosts", 0)))
    detail_table.add_row(
        "Automatic Upgrade",
        str((collector.get("automaticUpgradeInfo") or {}).get("enabled", False)),
    )

    console.print(detail_table)


@app.command("status")
def collector_status(
    down_only: Annotated[
        bool, typer.Option("--down-only", "-d", help="Show only down collectors")
    ] = False,
) -> None:
    """Show collector status summary."""
    svc = _get_service()
    collectors = svc.list()

    # Count by status
    status_counts: dict[str, int] = {}
    down_collectors: list[dict[str, Any]] = []

    for c in collectors:
        status = _status_name(c.get("status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
        if status != "ok":
            down_collectors.append(c)

    if down_only:
        if not down_collectors:
            console.print("[green]All collectors are healthy[/green]")
            return

        table = Table(title=f"[red]Down Collectors ({len(down_collectors)})[/red]")
        table.add_column("ID", style="dim")
        table.add_column("Hostname", style="cyan")
        table.add_column("Status", style="red")

        for c in down_collectors:
            table.add_row(
                str(c["id"]),
                c.get("hostname", ""),
                _status_name(c.get("status", "")),
            )
        console.print(table)
    else:
        console.print("\n[bold]Collector Status Summary[/bold]")

        summary_table = Table(show_header=False, box=None)
        summary_table.add_column("Status", style="dim")
        summary_table.add_column("Count", justify="right")

        ok_count = status_counts.get("ok", 0)
        summary_table.add_row("[green]OK[/green]", f"[green]{ok_count}[/green]")

        for status, count in sorted(status_counts.items()):
            if status != "ok":
                summary_table.add_row(f"[red]{status}[/red]", f"[red]{count}[/red]")

        summary_table.add_row("[bold]Total[/bold]", f"[bold]{len(collectors)}[/bold]")
        console.print(summary_table)


@app.command("update")
def update_collector(
    collector_id: Annotated[int, typer.Argument(help="Collector ID")],
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="New description")
    ] = None,
    auto_upgrade: Annotated[
        bool | None, typer.Option("--auto-upgrade", help="Enable/disable auto-upgrade")
    ] = None,
) -> None:
    """Update collector configuration."""
    svc = _get_service()

    data: dict[str, Any] = {}
    if description is not None:
        data["description"] = description
    if auto_upgrade is not None:
        data["automaticUpgradeInfo"] = {"enabled": auto_upgrade}

    if not data:
        console.print("[yellow]No changes specified[/yellow]")
        raise typer.Exit(1)

    try:
        result = svc.update(collector_id, data)
        console.print(f"[green]Updated collector {collector_id}[/green]")
        console.print_json(data=result)
    except Exception as e:
        console.print(f"[red]Failed: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("download")
def download_installer(
    platform: Annotated[str, typer.Argument(help="Platform: linux64, win64, etc.")],
    version: Annotated[
        str | None, typer.Option("--version", "-v", help="Specific version (default: latest)")
    ] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get collector installer download URL."""
    svc = _get_service()

    try:
        result = svc.get_installer_url(platform, version)

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"\n[bold]Installer: {platform}[/bold]")
            console.print(f"Version: {result.get('version', 'N/A')}")
            console.print(f"URL: {result.get('link', 'N/A')}")
            console.print("\n[dim]URL expires in 2 hours[/dim]")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("upgrade")
def upgrade_collector(
    collector_id: Annotated[int, typer.Argument(help="Collector ID")],
    version: Annotated[str, typer.Argument(help="Target version (e.g., 31.004)")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Upgrade collector to specific version."""
    svc = _get_service()

    try:
        collector = svc.get(collector_id)
        current_version = collector.get("build", "unknown")

        if not force:
            console.print(f"Current: {current_version}")
            console.print(f"Target: {version}")
            confirm = typer.confirm("Proceed?")
            if not confirm:
                raise typer.Abort()

        result = svc.escalate_to_version(collector_id, version)
        console.print(f"[green]Initiated upgrade to {version}[/green]")
        console.print_json(data=result)
    except typer.Abort:
        console.print("[yellow]Upgrade cancelled[/yellow]")
        raise typer.Exit(0) from None
    except Exception as e:
        console.print(f"[red]Failed: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_collector(
    collector_id: Annotated[int, typer.Argument(help="Collector ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a collector."""
    svc = _get_service()

    try:
        collector = svc.get(collector_id)
        hostname = collector.get("hostname", f"ID {collector_id}")

        if not force:
            console.print(f"[yellow]Warning: Delete '{hostname}'?[/yellow]")
            typer.confirm("Confirm", abort=True)

        svc.delete(collector_id)
        console.print(f"[green]Deleted {hostname}[/green]")
    except typer.Abort:
        console.print("[yellow]Deletion cancelled[/yellow]")
        raise typer.Exit(0) from None
    except Exception as e:
        console.print(f"[red]Failed: {e}[/red]")
        raise typer.Exit(1) from None
