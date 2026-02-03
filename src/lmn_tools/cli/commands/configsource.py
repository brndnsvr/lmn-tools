"""
ConfigSource management commands.

Provides commands for listing and viewing LogicMonitor ConfigSources.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import get_client
from lmn_tools.services.modules import LogicModuleService, ModuleType

app = typer.Typer(help="Manage ConfigSources")
console = Console()


def _get_service() -> LogicModuleService:
    """Get ConfigSource service."""
    return LogicModuleService(get_client(console), ModuleType.CONFIGSOURCE)


@app.command("list")
def list_configsources(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    group: Annotated[str | None, typer.Option("--group", "-g", help="Filter by group name")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, ids")
    ] = "table",
) -> None:
    """List ConfigSources with optional filtering."""
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
        table = Table(title=f"ConfigSources ({len(items)})")
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
def get_configsource(
    identifier: Annotated[str, typer.Argument(help="ConfigSource ID or name")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get ConfigSource details."""
    svc = _get_service()

    try:
        cs_id = int(identifier)
        response = svc.get(cs_id)
        cs = response.get("data", response) if "data" in response else response
    except ValueError:
        results = svc.list(filter=f'name:"{identifier}"', max_items=1)
        if not results:
            console.print(f"[red]ConfigSource not found: {identifier}[/red]")
            raise typer.Exit(1) from None
        cs = results[0]
        cs_id = cs["id"]

    if format == "json":
        console.print_json(data=cs)
        return

    console.print(f"\n[bold cyan]{cs.get('name', 'N/A')}[/bold cyan] (ID: {cs_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Group", cs.get("group", "N/A"))
    detail_table.add_row("Technology", cs.get("technology", "N/A"))
    detail_table.add_row("Version", str(cs.get("version", "N/A")))

    applies_to = cs.get("appliesTo", "")
    if len(applies_to) > 60:
        applies_to = applies_to[:60] + "..."
    detail_table.add_row("Applies To", applies_to)

    console.print(detail_table)


@app.command("search")
def search_configsources(
    query: Annotated[str, typer.Argument(help="Search term")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 25,
    format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, ids")
    ] = "table",
) -> None:
    """Search ConfigSources by name."""
    svc = _get_service()
    results = svc.list(filter=f'name~"{query}"', max_items=limit)

    if format == "json":
        console.print_json(data=results)
    elif format == "ids":
        for item in results:
            console.print(item["id"])
    else:
        if not results:
            console.print(f"[dim]No ConfigSources matching '{query}'[/dim]")
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
def export_configsource(
    cs_id: Annotated[int, typer.Argument(help="ConfigSource ID to export")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file path")] = None,
) -> None:
    """Export a ConfigSource as JSON."""
    svc = _get_service()
    cs = svc.export_json(cs_id)
    cs_data = cs.get("data", cs) if "data" in cs else cs

    json_output = json.dumps(cs_data, indent=2)

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
def import_configsource(
    file: Annotated[str, typer.Argument(help="JSON file path to import")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite if exists")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Import a ConfigSource from a JSON file."""
    from pathlib import Path

    svc = _get_service()
    file_path = Path(file)

    if not file_path.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1) from None

    try:
        cs_data = json.loads(file_path.read_text())
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1) from None

    # Handle wrapped data
    if "data" in cs_data:
        cs_data = cs_data["data"]

    cs_name = cs_data.get("name", "Unknown")

    # Check if exists
    if not force:
        existing = svc.list(filter=f'name:"{cs_name}"', max_items=1)
        if existing:
            console.print(
                f"[yellow]ConfigSource '{cs_name}' already exists (ID: {existing[0]['id']})[/yellow]"
            )
            console.print("Use --force to overwrite")
            raise typer.Exit(1) from None

    # Remove metadata that would cause conflicts
    for key in ["id", "checksum", "registeredOn", "modifiedOn", "version"]:
        cs_data.pop(key, None)

    try:
        response = svc.create(cs_data)
        result = response.get("data", response) if "data" in response else response
        cs_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Imported ConfigSource '{cs_name}' (ID: {cs_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to import: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("update")
def update_configsource(
    cs_id: Annotated[int, typer.Argument(help="ConfigSource ID")],
    group: Annotated[str | None, typer.Option("--group", "-g", help="New group name")] = None,
    technology: Annotated[
        str | None, typer.Option("--technology", "-t", help="New technology")
    ] = None,
    applies_to: Annotated[
        str | None, typer.Option("--applies-to", "-a", help="New AppliesTo expression")
    ] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update a ConfigSource."""
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
        response = svc.update(cs_id, update_data)
        result = response.get("data", response) if "data" in response else response

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated ConfigSource {cs_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update ConfigSource: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_configsource(
    cs_id: Annotated[int, typer.Argument(help="ConfigSource ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a ConfigSource."""
    svc = _get_service()

    # Get configsource info first
    try:
        response = svc.get(cs_id)
        cs = response.get("data", response) if "data" in response else response
        cs_name = cs.get("name", f"ID:{cs_id}")
    except Exception:
        cs_name = f"ID:{cs_id}"

    if not force:
        confirm = typer.confirm(f"Delete ConfigSource '{cs_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(cs_id)
        console.print(f"[green]Deleted ConfigSource '{cs_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete ConfigSource: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("clone")
def clone_configsource(
    cs_id: Annotated[int, typer.Argument(help="ConfigSource ID to clone")],
    name: Annotated[str, typer.Option("--name", "-n", help="New ConfigSource name")],
    display_name: Annotated[
        str | None, typer.Option("--display-name", "-d", help="New display name")
    ] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Clone a ConfigSource with a new name."""
    svc = _get_service()

    try:
        response = svc.clone(cs_id, name, display_name)
        result = response.get("data", response) if "data" in response else response
        new_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Cloned ConfigSource {cs_id} → '{name}' (ID: {new_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to clone ConfigSource: {e}[/red]")
        raise typer.Exit(1) from None
