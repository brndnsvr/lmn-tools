"""
EventSource management commands.

Provides commands for listing and viewing LogicMonitor EventSources.
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

app = typer.Typer(help="Manage EventSources")
console = Console()


def _get_client() -> LMClient:
    """Get authenticated API client."""
    settings = get_settings()
    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        raise typer.Exit(1) from None
    return LMClient.from_credentials(settings.credentials)  # type: ignore


def _get_service() -> LogicModuleService:
    """Get EventSource service."""
    return LogicModuleService(_get_client(), ModuleType.EVENTSOURCE)


@app.command("list")
def list_eventsources(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    group: Annotated[str | None, typer.Option("--group", "-g", help="Filter by group name")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List EventSources with optional filtering."""
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
        table = Table(title=f"EventSources ({len(items)})")
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
def get_eventsource(
    identifier: Annotated[str, typer.Argument(help="EventSource ID or name")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get EventSource details."""
    svc = _get_service()

    try:
        es_id = int(identifier)
        response = svc.get(es_id)
        es = response.get("data", response) if "data" in response else response
    except ValueError:
        results = svc.list(filter=f'name:"{identifier}"', max_items=1)
        if not results:
            console.print(f"[red]EventSource not found: {identifier}[/red]")
            raise typer.Exit(1) from None
        es = results[0]
        es_id = es["id"]

    if format == "json":
        console.print_json(data=es)
        return

    console.print(f"\n[bold cyan]{es.get('name', 'N/A')}[/bold cyan] (ID: {es_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Group", es.get("group", "N/A"))
    detail_table.add_row("Technology", es.get("technology", "N/A"))
    detail_table.add_row("Version", str(es.get("version", "N/A")))

    applies_to = es.get("appliesTo", "")
    if len(applies_to) > 60:
        applies_to = applies_to[:60] + "..."
    detail_table.add_row("Applies To", applies_to)

    console.print(detail_table)


@app.command("search")
def search_eventsources(
    query: Annotated[str, typer.Argument(help="Search term")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 25,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """Search EventSources by name."""
    svc = _get_service()
    results = svc.list(filter=f'name~"{query}"', max_items=limit)

    if format == "json":
        console.print_json(data=results)
    elif format == "ids":
        for item in results:
            console.print(item["id"])
    else:
        if not results:
            console.print(f"[dim]No EventSources matching '{query}'[/dim]")
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
def export_eventsource(
    es_id: Annotated[int, typer.Argument(help="EventSource ID to export")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file path")] = None,
) -> None:
    """Export an EventSource as JSON."""
    svc = _get_service()
    es = svc.export_json(es_id)
    es_data = es.get("data", es) if "data" in es else es

    json_output = json.dumps(es_data, indent=2)

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
def import_eventsource(
    file: Annotated[str, typer.Argument(help="JSON file path to import")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite if exists")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Import an EventSource from a JSON file."""
    from pathlib import Path

    svc = _get_service()
    file_path = Path(file)

    if not file_path.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1) from None

    try:
        es_data = json.loads(file_path.read_text())
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1) from None

    # Handle wrapped data
    if "data" in es_data:
        es_data = es_data["data"]

    es_name = es_data.get("name", "Unknown")

    # Check if exists
    if not force:
        existing = svc.list(filter=f'name:"{es_name}"', max_items=1)
        if existing:
            console.print(f"[yellow]EventSource '{es_name}' already exists (ID: {existing[0]['id']})[/yellow]")
            console.print("Use --force to overwrite")
            raise typer.Exit(1) from None

    # Remove metadata that would cause conflicts
    for key in ["id", "checksum", "registeredOn", "modifiedOn", "version"]:
        es_data.pop(key, None)

    try:
        response = svc.create(es_data)
        result = response.get("data", response) if "data" in response else response
        es_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Imported EventSource '{es_name}' (ID: {es_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to import: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("update")
def update_eventsource(
    es_id: Annotated[int, typer.Argument(help="EventSource ID")],
    group: Annotated[str | None, typer.Option("--group", "-g", help="New group name")] = None,
    technology: Annotated[str | None, typer.Option("--technology", "-t", help="New technology")] = None,
    applies_to: Annotated[str | None, typer.Option("--applies-to", "-a", help="New AppliesTo expression")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update an EventSource."""
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
        response = svc.update(es_id, update_data)
        result = response.get("data", response) if "data" in response else response

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated EventSource {es_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update EventSource: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_eventsource(
    es_id: Annotated[int, typer.Argument(help="EventSource ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete an EventSource."""
    svc = _get_service()

    # Get eventsource info first
    try:
        response = svc.get(es_id)
        es = response.get("data", response) if "data" in response else response
        es_name = es.get("name", f"ID:{es_id}")
    except Exception:
        es_name = f"ID:{es_id}"

    if not force:
        confirm = typer.confirm(f"Delete EventSource '{es_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(es_id)
        console.print(f"[green]Deleted EventSource '{es_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete EventSource: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("clone")
def clone_eventsource(
    es_id: Annotated[int, typer.Argument(help="EventSource ID to clone")],
    name: Annotated[str, typer.Option("--name", "-n", help="New EventSource name")],
    display_name: Annotated[str | None, typer.Option("--display-name", "-d", help="New display name")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Clone an EventSource with a new name."""
    svc = _get_service()

    try:
        response = svc.clone(es_id, name, display_name)
        result = response.get("data", response) if "data" in response else response
        new_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Cloned EventSource {es_id} → '{name}' (ID: {new_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to clone EventSource: {e}[/red]")
        raise typer.Exit(1) from None
