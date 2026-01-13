"""
TopologySource management commands.

Provides commands for listing and viewing LogicMonitor TopologySources.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import get_settings
from lmn_tools.services.modules import LogicModuleService, ModuleType

app = typer.Typer(help="Manage TopologySources")
console = Console()


def _get_client() -> LMClient:
    """Get authenticated API client."""
    settings = get_settings()
    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        raise typer.Exit(1) from None
    return LMClient.from_credentials(settings.credentials)  # type: ignore


def _get_service() -> LogicModuleService:
    """Get TopologySource service."""
    return LogicModuleService(_get_client(), ModuleType.TOPOLOGYSOURCE)


@app.command("list")
def list_topologysources(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    group: Annotated[str | None, typer.Option("--group", "-g", help="Filter by group name")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List TopologySources with optional filtering."""
    svc = _get_service()

    filters = []
    if filter:
        filters.append(filter)
    if group:
        filters.append(f'group:"{group}"')
    filter_str = ",".join(filters) if filters else None

    items = svc.list(filter=filter_str, max_items=limit)

    if format == "json":
        console.print_json(data=items)
    elif format == "ids":
        for item in items:
            console.print(item["id"])
    else:
        table = Table(title=f"TopologySources ({len(items)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Group")
        table.add_column("Technology")

        for item in items:
            table.add_row(
                str(item["id"]),
                item.get("name", ""),
                item.get("group", ""),
                item.get("technology", ""),
            )
        console.print(table)


@app.command("get")
def get_topologysource(
    identifier: Annotated[str, typer.Argument(help="TopologySource ID or name")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get TopologySource details."""
    svc = _get_service()

    try:
        ts_id = int(identifier)
        response = svc.get(ts_id)
        ts = response.get("data", response) if "data" in response else response
    except ValueError:
        results = svc.list(filter=f'name:"{identifier}"', max_items=1)
        if not results:
            console.print(f"[red]TopologySource not found: {identifier}[/red]")
            raise typer.Exit(1) from None
        ts = results[0]
        ts_id = ts["id"]

    if format == "json":
        console.print_json(data=ts)
        return

    console.print(f"\n[bold cyan]{ts.get('name', 'N/A')}[/bold cyan] (ID: {ts_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Group", ts.get("group", "N/A"))
    detail_table.add_row("Technology", ts.get("technology", "N/A"))
    detail_table.add_row("Version", str(ts.get("version", "N/A")))

    applies_to = ts.get("appliesTo", "")
    if len(applies_to) > 60:
        applies_to = applies_to[:60] + "..."
    detail_table.add_row("Applies To", applies_to)

    console.print(detail_table)


@app.command("search")
def search_topologysources(
    query: Annotated[str, typer.Argument(help="Search term")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 25,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """Search TopologySources by name."""
    svc = _get_service()
    results = svc.list(filter=f'name~"{query}"', max_items=limit)

    if format == "json":
        console.print_json(data=results)
    elif format == "ids":
        for item in results:
            console.print(item["id"])
    else:
        if not results:
            console.print(f"[dim]No TopologySources matching '{query}'[/dim]")
            return

        table = Table(title=f"Search Results for '{query}' ({len(results)})")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Group")

        for item in results[:limit]:
            table.add_row(
                str(item["id"]),
                item.get("name", ""),
                item.get("group", ""),
            )
        console.print(table)


@app.command("export")
def export_topologysource(
    ts_id: Annotated[int, typer.Argument(help="TopologySource ID to export")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file path")] = None,
) -> None:
    """Export a TopologySource as JSON."""
    svc = _get_service()
    ts = svc.export_json(ts_id)
    ts_data = ts.get("data", ts) if "data" in ts else ts

    json_output = json.dumps(ts_data, indent=2)

    if output:
        from pathlib import Path
        Path(output).write_text(json_output)
        console.print(f"[green]Exported to {output}[/green]")
    else:
        console.print(json_output)


# ============================================================================
# Write Operations (CRUD)
# ============================================================================


@app.command("import")
def import_topologysource(
    file: Annotated[str, typer.Argument(help="JSON file path to import")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite if exists")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Import a TopologySource from a JSON file."""
    from pathlib import Path

    svc = _get_service()
    file_path = Path(file)

    if not file_path.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1) from None

    try:
        ts_data = json.loads(file_path.read_text())
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1) from None

    # Handle wrapped data
    if "data" in ts_data:
        ts_data = ts_data["data"]

    ts_name = ts_data.get("name", "Unknown")

    # Check if exists
    if not force:
        existing = svc.list(filter=f'name:"{ts_name}"', max_items=1)
        if existing:
            console.print(f"[yellow]TopologySource '{ts_name}' already exists (ID: {existing[0]['id']})[/yellow]")
            console.print("Use --force to overwrite")
            raise typer.Exit(1) from None

    # Remove metadata that would cause conflicts
    for key in ["id", "checksum", "registeredOn", "modifiedOn", "version"]:
        ts_data.pop(key, None)

    try:
        response = svc.create(ts_data)
        result = response.get("data", response) if "data" in response else response
        ts_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Imported TopologySource '{ts_name}' (ID: {ts_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to import: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("update")
def update_topologysource(
    ts_id: Annotated[int, typer.Argument(help="TopologySource ID")],
    group: Annotated[str | None, typer.Option("--group", "-g", help="New group name")] = None,
    technology: Annotated[str | None, typer.Option("--technology", "-t", help="New technology")] = None,
    applies_to: Annotated[str | None, typer.Option("--applies-to", "-a", help="New AppliesTo expression")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update a TopologySource."""
    svc = _get_service()

    update_data: dict[str, Any] = {}

    if group is not None:
        update_data["group"] = group
    if technology is not None:
        update_data["technology"] = technology
    if applies_to is not None:
        update_data["appliesTo"] = applies_to

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0) from None

    try:
        response = svc.update(ts_id, update_data)
        result = response.get("data", response) if "data" in response else response

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated TopologySource {ts_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update TopologySource: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_topologysource(
    ts_id: Annotated[int, typer.Argument(help="TopologySource ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a TopologySource."""
    svc = _get_service()

    # Get topologysource info first
    try:
        response = svc.get(ts_id)
        ts = response.get("data", response) if "data" in response else response
        ts_name = ts.get("name", f"ID:{ts_id}")
    except Exception:
        ts_name = f"ID:{ts_id}"

    if not force:
        confirm = typer.confirm(f"Delete TopologySource '{ts_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(ts_id)
        console.print(f"[green]Deleted TopologySource '{ts_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete TopologySource: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("clone")
def clone_topologysource(
    ts_id: Annotated[int, typer.Argument(help="TopologySource ID to clone")],
    name: Annotated[str, typer.Option("--name", "-n", help="New TopologySource name")],
    display_name: Annotated[str | None, typer.Option("--display-name", "-d", help="New display name")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Clone a TopologySource with a new name."""
    svc = _get_service()

    try:
        response = svc.clone(ts_id, name, display_name)
        result = response.get("data", response) if "data" in response else response
        new_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Cloned TopologySource {ts_id} → '{name}' (ID: {new_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to clone TopologySource: {e}[/red]")
        raise typer.Exit(1) from None
