"""
PropertySource management commands.

Provides commands for listing and viewing LogicMonitor PropertySources.
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import get_settings
from lmn_tools.services.modules import LogicModuleService, ModuleType

app = typer.Typer(help="Manage PropertySources")
console = Console()


def _get_client() -> LMClient:
    """Get authenticated API client."""
    settings = get_settings()
    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        raise typer.Exit(1)
    return LMClient.from_credentials(settings.credentials)  # type: ignore


def _get_service() -> LogicModuleService:
    """Get PropertySource service."""
    return LogicModuleService(_get_client(), ModuleType.PROPERTYSOURCE)


@app.command("list")
def list_propertysources(
    filter: Annotated[Optional[str], typer.Option("--filter", "-f", help="LM filter string")] = None,
    group: Annotated[Optional[str], typer.Option("--group", "-g", help="Filter by group name")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List PropertySources with optional filtering."""
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
        table = Table(title=f"PropertySources ({len(items)})")
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
def get_propertysource(
    identifier: Annotated[str, typer.Argument(help="PropertySource ID or name")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get PropertySource details."""
    svc = _get_service()

    try:
        ps_id = int(identifier)
        response = svc.get(ps_id)
        ps = response.get("data", response) if "data" in response else response
    except ValueError:
        results = svc.list(filter=f'name:"{identifier}"', max_items=1)
        if not results:
            console.print(f"[red]PropertySource not found: {identifier}[/red]")
            raise typer.Exit(1)
        ps = results[0]
        ps_id = ps["id"]

    if format == "json":
        console.print_json(data=ps)
        return

    console.print(f"\n[bold cyan]{ps.get('name', 'N/A')}[/bold cyan] (ID: {ps_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Group", ps.get("group", "N/A"))
    detail_table.add_row("Technology", ps.get("technology", "N/A"))
    detail_table.add_row("Version", str(ps.get("version", "N/A")))

    applies_to = ps.get("appliesTo", "")
    if len(applies_to) > 60:
        applies_to = applies_to[:60] + "..."
    detail_table.add_row("Applies To", applies_to)

    console.print(detail_table)


@app.command("search")
def search_propertysources(
    query: Annotated[str, typer.Argument(help="Search term")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 25,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """Search PropertySources by name."""
    svc = _get_service()
    results = svc.list(filter=f'name~"{query}"', max_items=limit)

    if format == "json":
        console.print_json(data=results)
    elif format == "ids":
        for item in results:
            console.print(item["id"])
    else:
        if not results:
            console.print(f"[dim]No PropertySources matching '{query}'[/dim]")
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
def export_propertysource(
    ps_id: Annotated[int, typer.Argument(help="PropertySource ID to export")],
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output file path")] = None,
) -> None:
    """Export a PropertySource as JSON."""
    svc = _get_service()
    ps = svc.export_json(ps_id)
    ps_data = ps.get("data", ps) if "data" in ps else ps

    json_output = json.dumps(ps_data, indent=2)

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
def import_propertysource(
    file: Annotated[str, typer.Argument(help="JSON file path to import")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite if exists")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Import a PropertySource from a JSON file."""
    from pathlib import Path

    svc = _get_service()
    file_path = Path(file)

    if not file_path.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    try:
        ps_data = json.loads(file_path.read_text())
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1)

    # Handle wrapped data
    if "data" in ps_data:
        ps_data = ps_data["data"]

    ps_name = ps_data.get("name", "Unknown")

    # Check if exists
    if not force:
        existing = svc.list(filter=f'name:"{ps_name}"', max_items=1)
        if existing:
            console.print(f"[yellow]PropertySource '{ps_name}' already exists (ID: {existing[0]['id']})[/yellow]")
            console.print("Use --force to overwrite")
            raise typer.Exit(1)

    # Remove metadata that would cause conflicts
    for key in ["id", "checksum", "registeredOn", "modifiedOn", "version"]:
        ps_data.pop(key, None)

    try:
        response = svc.create(ps_data)
        result = response.get("data", response) if "data" in response else response
        ps_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Imported PropertySource '{ps_name}' (ID: {ps_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to import: {e}[/red]")
        raise typer.Exit(1)


@app.command("update")
def update_propertysource(
    ps_id: Annotated[int, typer.Argument(help="PropertySource ID")],
    group: Annotated[Optional[str], typer.Option("--group", "-g", help="New group name")] = None,
    technology: Annotated[Optional[str], typer.Option("--technology", "-t", help="New technology")] = None,
    applies_to: Annotated[Optional[str], typer.Option("--applies-to", "-a", help="New AppliesTo expression")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update a PropertySource."""
    svc = _get_service()

    update_data: dict = {}

    if group is not None:
        update_data["group"] = group
    if technology is not None:
        update_data["technology"] = technology
    if applies_to is not None:
        update_data["appliesTo"] = applies_to

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0)

    try:
        response = svc.update(ps_id, update_data)
        result = response.get("data", response) if "data" in response else response

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated PropertySource {ps_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update PropertySource: {e}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_propertysource(
    ps_id: Annotated[int, typer.Argument(help="PropertySource ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a PropertySource."""
    svc = _get_service()

    # Get propertysource info first
    try:
        response = svc.get(ps_id)
        ps = response.get("data", response) if "data" in response else response
        ps_name = ps.get("name", f"ID:{ps_id}")
    except Exception:
        ps_name = f"ID:{ps_id}"

    if not force:
        confirm = typer.confirm(f"Delete PropertySource '{ps_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    try:
        svc.delete(ps_id)
        console.print(f"[green]Deleted PropertySource '{ps_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete PropertySource: {e}[/red]")
        raise typer.Exit(1)


@app.command("clone")
def clone_propertysource(
    ps_id: Annotated[int, typer.Argument(help="PropertySource ID to clone")],
    name: Annotated[str, typer.Option("--name", "-n", help="New PropertySource name")],
    display_name: Annotated[Optional[str], typer.Option("--display-name", "-d", help="New display name")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Clone a PropertySource with a new name."""
    svc = _get_service()

    try:
        response = svc.clone(ps_id, name, display_name)
        result = response.get("data", response) if "data" in response else response
        new_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Cloned PropertySource {ps_id} → '{name}' (ID: {new_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to clone PropertySource: {e}[/red]")
        raise typer.Exit(1)
