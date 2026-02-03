"""
Netscan management commands.

Provides commands for managing LogicMonitor network discovery scans.
"""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import format_timestamp, get_client, load_json_file, unwrap_response
from lmn_tools.services.discovery import NetscanService

app = typer.Typer(help="Manage network discovery scans")
console = Console()


def _get_service() -> NetscanService:
    """Get Netscan service."""
    return NetscanService(get_client(console))


@app.command("list")
def list_netscans(
    collector: Annotated[
        int | None, typer.Option("--collector", "-c", help="Filter by collector ID")
    ] = None,
    group: Annotated[
        int | None, typer.Option("--group", "-g", help="Filter by target group ID")
    ] = None,
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, ids")
    ] = "table",
) -> None:
    """List Netscans with optional filtering."""
    svc = _get_service()

    if collector:
        scans = svc.list_by_collector(collector, max_items=limit)
    elif group:
        scans = svc.list_by_group(group, max_items=limit)
    else:
        scans = svc.list(filter=filter, max_items=limit)

    if format == "json":
        console.print_json(data=scans)
    elif format == "ids":
        for s in scans:
            console.print(s.get("id", ""))
    else:
        if not scans:
            console.print("[dim]No Netscans found[/dim]")
            return

        table = Table(title=f"Netscans ({len(scans)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Method")
        table.add_column("Collector")
        table.add_column("Target Group")
        table.add_column("Disabled")

        for s in scans:
            collector_info = s.get("collector", {})
            collector_name = collector_info.get("description", str(collector_info.get("id", "")))
            group_info = s.get("group", {})
            group_name = group_info.get("name", str(group_info.get("id", "")))
            disabled = "[red]Yes[/red]" if s.get("disabled") else "[green]No[/green]"

            table.add_row(
                str(s.get("id", "")),
                s.get("name", ""),
                s.get("method", ""),
                collector_name,
                group_name,
                disabled,
            )
        console.print(table)


@app.command("get")
def get_netscan(
    netscan_id: Annotated[int, typer.Argument(help="Netscan ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get Netscan details."""
    svc = _get_service()
    response = svc.get(netscan_id)
    scan = unwrap_response(response)

    if format == "json":
        console.print_json(data=scan)
        return

    console.print(f"\n[bold cyan]{scan.get('name', 'N/A')}[/bold cyan] (ID: {netscan_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Method", scan.get("method", "N/A"))
    detail_table.add_row("Description", scan.get("description", "N/A") or "N/A")

    collector_info = scan.get("collector", {})
    detail_table.add_row(
        "Collector", collector_info.get("description", str(collector_info.get("id", "N/A")))
    )

    group_info = scan.get("group", {})
    detail_table.add_row("Target Group", group_info.get("name", str(group_info.get("id", "N/A"))))

    detail_table.add_row("Subnet", scan.get("subnet", "N/A") or "N/A")
    detail_table.add_row("Disabled", "Yes" if scan.get("disabled") else "No")
    detail_table.add_row("Last Executed", format_timestamp(scan.get("lastExecutedOn")))
    detail_table.add_row("Next Start", format_timestamp(scan.get("nextStart")))

    console.print(detail_table)


@app.command("create")
def create_netscan(
    name: Annotated[str, typer.Option("--name", "-n", help="Scan name")],
    collector: Annotated[int, typer.Option("--collector", "-c", help="Collector ID")],
    group: Annotated[int, typer.Option("--group", "-g", help="Target device group ID")],
    subnet: Annotated[str, typer.Option("--subnet", "-s", help="IP range to scan (CIDR)")],
    method: Annotated[str, typer.Option("--method", "-m", help="Scan method")] = "nmap",
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Description")
    ] = None,
    config_file: Annotated[str | None, typer.Option("--config", help="JSON config file")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new Netscan."""
    svc = _get_service()

    scan_data: dict[str, Any]
    if config_file:
        scan_data = load_json_file(config_file, console)
    else:
        scan_data = {
            "name": name,
            "method": method,
            "collector": collector,
            "group": {"id": group},
            "subnet": subnet,
        }
        if description:
            scan_data["description"] = description

    try:
        result = unwrap_response(svc.create(scan_data))
        new_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created Netscan '{name}' (ID: {new_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create Netscan: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("run")
def run_netscan(
    netscan_id: Annotated[int, typer.Argument(help="Netscan ID to execute")],
) -> None:
    """Execute a Netscan immediately."""
    svc = _get_service()

    try:
        svc.run(netscan_id)
        console.print(f"[green]Netscan {netscan_id} execution started[/green]")
    except Exception as e:
        console.print(f"[red]Failed to run Netscan: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("status")
def netscan_status(
    netscan_id: Annotated[int, typer.Argument(help="Netscan ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get Netscan execution status."""
    svc = _get_service()
    status = svc.get_execution_status(netscan_id)

    if format == "json":
        console.print_json(data=status)
        return

    console.print(f"\n[bold]Netscan Status: {status.get('name', netscan_id)}[/bold]")
    console.print()

    table = Table(show_header=False, box=None)
    table.add_column("Field", style="dim")
    table.add_column("Value")

    table.add_row("Last Executed", format_timestamp(status.get("lastExecutedOn")))
    table.add_row("Next Start", format_timestamp(status.get("nextStart")))

    console.print(table)


@app.command("enable")
def enable_netscan(
    netscan_id: Annotated[int, typer.Argument(help="Netscan ID")],
) -> None:
    """Enable a Netscan."""
    svc = _get_service()

    try:
        svc.enable(netscan_id)
        console.print(f"[green]Enabled Netscan {netscan_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to enable Netscan: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("disable")
def disable_netscan(
    netscan_id: Annotated[int, typer.Argument(help="Netscan ID")],
) -> None:
    """Disable a Netscan."""
    svc = _get_service()

    try:
        svc.disable(netscan_id)
        console.print(f"[yellow]Disabled Netscan {netscan_id}[/yellow]")
    except Exception as e:
        console.print(f"[red]Failed to disable Netscan: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_netscan(
    netscan_id: Annotated[int, typer.Argument(help="Netscan ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a Netscan."""
    svc = _get_service()

    try:
        scan = unwrap_response(svc.get(netscan_id))
        scan_name = scan.get("name", f"ID:{netscan_id}")
    except Exception:
        scan_name = f"ID:{netscan_id}"

    if not force:
        confirm = typer.confirm(f"Delete Netscan '{scan_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(netscan_id)
        console.print(f"[green]Deleted Netscan '{scan_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete Netscan: {e}[/red]")
        raise typer.Exit(1) from None
