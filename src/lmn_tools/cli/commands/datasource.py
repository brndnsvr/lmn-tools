"""
DataSource management commands.

Provides commands for listing, viewing, and managing LogicMonitor DataSources.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import (
    build_filter,
    edit_in_editor,
    edit_json_in_editor,
    get_client,
    get_syntax_lexer,
    load_json_file,
    show_diff,
    show_syntax,
    truncate,
    unwrap_response,
)
from lmn_tools.services.modules import LogicModuleService, ModuleType

app = typer.Typer(help="Manage DataSources")
console = Console()


def _get_service() -> LogicModuleService:
    """Get DataSource service."""
    return LogicModuleService(get_client(console), ModuleType.DATASOURCE)


def _get_script_from_ds(ds: dict[str, Any], discovery: bool, script_type: str) -> str:
    """Extract script from DataSource data."""
    config = ds.get("autoDiscoveryConfig") or {} if discovery else ds.get("collectorAttribute") or {}
    return str(config.get(f"{script_type}Script", ""))


def _set_script_in_ds(ds: dict[str, Any], discovery: bool, script_type: str, script: str) -> None:
    """Set script in DataSource data (mutates ds)."""
    key = "autoDiscoveryConfig" if discovery else "collectorAttribute"
    if not ds.get(key):
        ds[key] = {}
    ds[key][f"{script_type}Script"] = script


# ============================================================================
# Read Operations
# ============================================================================


@app.command("list")
def list_datasources(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    group: Annotated[str | None, typer.Option("--group", "-g", help="Filter by group name")] = None,
    method: Annotated[str | None, typer.Option("--method", "-m", help="Filter by collect method")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List DataSources with optional filtering."""
    svc = _get_service()
    filter_str = build_filter(filter, f'group:"{group}"' if group else None, f'collectMethod:"{method}"' if method else None)
    datasources = svc.list(filter=filter_str, max_items=limit)

    if format == "json":
        console.print_json(data=datasources)
    elif format == "ids":
        for ds in datasources:
            console.print(ds["id"])
    else:
        table = Table(title=f"DataSources ({len(datasources)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Display Name")
        table.add_column("Group")
        table.add_column("Method")
        for ds in datasources:
            table.add_row(str(ds["id"]), ds.get("name", ""), ds.get("displayName", ""), ds.get("group", ""), ds.get("collectMethod", ""))
        console.print(table)


@app.command("get")
def get_datasource(
    identifier: Annotated[str, typer.Argument(help="DataSource ID or name")],
    show_datapoints: Annotated[bool, typer.Option("--datapoints", "-d", help="Show datapoints")] = False,
    show_graphs: Annotated[bool, typer.Option("--graphs", "-g", help="Show graphs")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get DataSource details."""
    svc = _get_service()
    try:
        ds_id = int(identifier)
        ds = unwrap_response(svc.get(ds_id))
    except ValueError:
        results = svc.list(filter=f'name:"{identifier}"', max_items=1)
        if not results:
            console.print(f"[red]DataSource not found: {identifier}[/red]")
            raise typer.Exit(1) from None
        ds, ds_id = results[0], results[0]["id"]

    if format == "json":
        console.print_json(data=ds)
        return

    console.print(f"\n[bold cyan]{ds.get('name', 'N/A')}[/bold cyan] (ID: {ds_id})\n")
    detail = Table(show_header=False, box=None)
    detail.add_column("Field", style="dim")
    detail.add_column("Value")
    detail.add_row("Display Name", ds.get("displayName", "N/A"))
    detail.add_row("Group", ds.get("group", "N/A"))
    detail.add_row("Collect Method", ds.get("collectMethod", "N/A"))
    detail.add_row("Collect Interval", f"{ds.get('collectInterval', 'N/A')}s")
    detail.add_row("Multi-instance", str(ds.get("hasMultiInstances", False)))
    detail.add_row("Technology", ds.get("technology", "N/A"))
    detail.add_row("Version", str(ds.get("version", "N/A")))
    detail.add_row("Applies To", truncate(ds.get("appliesTo", ""), 60))
    console.print(detail)

    if show_datapoints:
        console.print("\n[bold]Datapoints:[/bold]")
        for dp in svc.get_datapoints(ds_id) or []:
            console.print(f"  - {dp.get('name', 'N/A')}")
    if show_graphs:
        console.print("\n[bold]Graphs:[/bold]")
        for g in svc.get_graphs(ds_id) or []:
            console.print(f"  - {g.get('name', 'N/A')}")


@app.command("datapoints")
def list_datapoints(
    ds_id: Annotated[int, typer.Argument(help="DataSource ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List datapoints for a DataSource."""
    datapoints = _get_service().get_datapoints(ds_id)
    if format == "json":
        console.print_json(data=datapoints)
        return
    if not datapoints:
        console.print("[dim]No datapoints found[/dim]")
        return
    table = Table(title=f"Datapoints for DataSource {ds_id}")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("Description")
    for dp in datapoints:
        table.add_row(str(dp.get("id", "")), dp.get("name", ""), str(dp.get("type", "")), truncate(dp.get("description", "") or "", 40))
    console.print(table)


@app.command("graphs")
def list_graphs(
    ds_id: Annotated[int, typer.Argument(help="DataSource ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List graphs for a DataSource."""
    graphs = _get_service().get_graphs(ds_id)
    if format == "json":
        console.print_json(data=graphs)
        return
    if not graphs:
        console.print("[dim]No graphs found[/dim]")
        return
    table = Table(title=f"Graphs for DataSource {ds_id}")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Title")
    for g in graphs:
        table.add_row(str(g.get("id", "")), g.get("name", ""), g.get("title", ""))
    console.print(table)


@app.command("ographs")
def list_overview_graphs(
    ds_id: Annotated[int, typer.Argument(help="DataSource ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List overview graphs for a DataSource."""
    ographs = _get_service().get_overview_graphs(ds_id)
    if format == "json":
        console.print_json(data=ographs)
        return
    if not ographs:
        console.print("[dim]No overview graphs found[/dim]")
        return
    table = Table(title=f"Overview Graphs for DataSource {ds_id}")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Title")
    for g in ographs:
        table.add_row(str(g.get("id", "")), g.get("name", ""), g.get("title", ""))
    console.print(table)


@app.command("search")
def search_datasources(
    query: Annotated[str, typer.Argument(help="Search term")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 25,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """Search DataSources by name or display name."""
    svc = _get_service()
    results = svc.list(filter=f'name~"{query}"', max_items=limit)
    display_results = svc.list(filter=f'displayName~"{query}"', max_items=limit)
    seen_ids = {r["id"] for r in results}
    results.extend(r for r in display_results if r["id"] not in seen_ids)

    if format == "json":
        console.print_json(data=results)
    elif format == "ids":
        for ds in results:
            console.print(ds["id"])
    elif not results:
        console.print(f"[dim]No DataSources matching '{query}'[/dim]")
    else:
        table = Table(title=f"Search Results for '{query}' ({len(results)})")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Display Name")
        table.add_column("Group")
        for ds in results[:limit]:
            table.add_row(str(ds["id"]), ds.get("name", ""), ds.get("displayName", ""), ds.get("group", ""))
        console.print(table)


@app.command("export")
def export_datasource(
    ds_id: Annotated[int, typer.Argument(help="DataSource ID to export")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file path")] = None,
) -> None:
    """Export a DataSource as JSON."""
    ds = unwrap_response(_get_service().export_json(ds_id))
    json_output = json.dumps(ds, indent=2)
    if output:
        Path(output).write_text(json_output)
        console.print(f"[green]Exported to {output}[/green]")
    else:
        console.print(json_output)


@app.command("groups")
def list_groups(
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List all DataSource groups."""
    datasources = _get_service().list(fields=["group"], max_items=5000)
    groups: dict[str, int] = {}
    for ds in datasources:
        if group := ds.get("group", ""):
            groups[group] = groups.get(group, 0) + 1

    if format == "json":
        console.print_json(data=[{"group": k, "count": v} for k, v in sorted(groups.items())])
        return
    if not groups:
        console.print("[dim]No groups found[/dim]")
        return
    table = Table(title=f"DataSource Groups ({len(groups)})")
    table.add_column("Group", style="cyan")
    table.add_column("Count", justify="right")
    for group, count in sorted(groups.items()):
        table.add_row(group, str(count))
    console.print(table)


# ============================================================================
# Write Operations (CRUD)
# ============================================================================


@app.command("import")
def import_datasource(
    file: Annotated[str, typer.Argument(help="JSON file path to import")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite if exists")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Import a DataSource from a JSON file."""
    svc = _get_service()
    ds_data = load_json_file(file, console)
    ds_name = ds_data.get("name", "Unknown")

    if not force:
        existing = svc.list(filter=f'name:"{ds_name}"', max_items=1)
        if existing:
            console.print(f"[yellow]DataSource '{ds_name}' already exists (ID: {existing[0]['id']})[/yellow]")
            console.print("Use --force to overwrite")
            raise typer.Exit(1) from None

    for key in ["id", "checksum", "registeredOn", "modifiedOn", "version"]:
        ds_data.pop(key, None)

    try:
        result = unwrap_response(svc.create(ds_data))
        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Imported DataSource '{ds_name}' (ID: {result.get('id')})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to import: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("update")
def update_datasource(
    ds_id: Annotated[int, typer.Argument(help="DataSource ID")],
    group: Annotated[str | None, typer.Option("--group", "-g", help="New group name")] = None,
    display_name: Annotated[str | None, typer.Option("--display-name", "-d", help="New display name")] = None,
    description: Annotated[str | None, typer.Option("--description", help="New description")] = None,
    applies_to: Annotated[str | None, typer.Option("--applies-to", "-a", help="New AppliesTo expression")] = None,
    collect_interval: Annotated[int | None, typer.Option("--interval", help="Collection interval in seconds")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update a DataSource."""
    update_data: dict[str, Any] = {}
    if group is not None:
        update_data["group"] = group
    if display_name:
        update_data["displayName"] = display_name
    if description is not None:
        update_data["description"] = description
    if applies_to is not None:
        update_data["appliesTo"] = applies_to
    if collect_interval is not None:
        update_data["collectInterval"] = collect_interval

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0) from None

    try:
        result = unwrap_response(_get_service().update(ds_id, update_data))
        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated DataSource {ds_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update DataSource: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_datasource(
    ds_id: Annotated[int, typer.Argument(help="DataSource ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a DataSource."""
    svc = _get_service()
    try:
        ds_name = unwrap_response(svc.get(ds_id)).get("name", f"ID:{ds_id}")
    except Exception:
        ds_name = f"ID:{ds_id}"

    if not force and not typer.confirm(f"Delete DataSource '{ds_name}'?"):
        console.print("[dim]Cancelled[/dim]")
        raise typer.Exit(0) from None

    try:
        svc.delete(ds_id)
        console.print(f"[green]Deleted DataSource '{ds_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete DataSource: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("clone")
def clone_datasource(
    ds_id: Annotated[int, typer.Argument(help="DataSource ID to clone")],
    name: Annotated[str, typer.Option("--name", "-n", help="New DataSource name")],
    display_name: Annotated[str | None, typer.Option("--display-name", "-d", help="New display name")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Clone a DataSource with a new name."""
    try:
        result = unwrap_response(_get_service().clone(ds_id, name, display_name))
        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Cloned DataSource {ds_id} → '{name}' (ID: {result.get('id')})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to clone DataSource: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("test")
def test_datasource(
    ds_id: Annotated[int, typer.Argument(help="DataSource ID to test")],
    device_id: Annotated[int, typer.Option("--device", "-d", help="Device ID to test against")],
) -> None:
    """Test a DataSource Active Discovery or Collection script against a device."""
    client = get_client(console)
    try:
        result = unwrap_response(client.post("/debug/collect", json_data={"deviceId": device_id, "dataSourceId": ds_id}))
        if "output" in result:
            console.print("[bold]Script Output:[/bold]")
            console.print(result["output"])
        else:
            console.print_json(data=result)
    except Exception:
        try:
            result = unwrap_response(client.post("/debug/activediscovery", json_data={"deviceId": device_id, "dataSourceId": ds_id}))
            if "output" in result:
                console.print("[bold]Discovery Output:[/bold]")
                console.print(result["output"])
            else:
                console.print_json(data=result)
        except Exception as e:
            console.print(f"[red]Failed to test DataSource: {e}[/red]")
            console.print("[dim]Note: Test requires appropriate permissions and collector access[/dim]")
            raise typer.Exit(1) from None


# ============================================================================
# Script Editing Workflow
# ============================================================================


@app.command("script")
def datasource_script(
    ds_id: Annotated[int, typer.Argument(help="DataSource ID")],
    discovery: Annotated[bool, typer.Option("--discovery", "-d", help="Show/set Active Discovery script")] = False,
    script_type: Annotated[str, typer.Option("--type", "-t", help="Script type: groovy, linux, windows")] = "groovy",
    set_file: Annotated[str | None, typer.Option("--set", "-s", help="File path to read new script from")] = None,
    no_highlight: Annotated[bool, typer.Option("--no-highlight", help="Output raw script without syntax highlighting")] = False,
) -> None:
    """View or update DataSource scripts."""
    svc = _get_service()
    try:
        ds = unwrap_response(svc.export_json(ds_id))
    except Exception as e:
        console.print(f"[red]Failed to get DataSource: {e}[/red]")
        raise typer.Exit(1) from None

    script_location = "Active Discovery" if discovery else "Collection"

    if set_file:
        if not Path(set_file).exists():
            console.print(f"[red]File not found: {set_file}[/red]")
            raise typer.Exit(1) from None
        new_script = Path(set_file).read_text()
        old_script = _get_script_from_ds(ds, discovery, script_type)
        _set_script_in_ds(ds, discovery, script_type, new_script)

        if old_script:
            show_diff(old_script, new_script, f"{script_location} (current)", f"{script_location} (new)", console, title=f"Changes to {script_location} {script_type} script:")

        if not typer.confirm(f"Update {script_location} {script_type} script?"):
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

        try:
            get_client(console).put(f"/setting/datasources/{ds_id}", json_data=ds)
            console.print(f"[green]Updated {script_location} {script_type} script for DataSource {ds_id}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to update script: {e}[/red]")
            raise typer.Exit(1) from None
    else:
        script = _get_script_from_ds(ds, discovery, script_type)
        if not script:
            console.print(f"[dim]No {script_location} {script_type} script defined[/dim]")
            return
        if no_highlight:
            console.print(script)
        else:
            show_syntax(script, get_syntax_lexer(script_type), console, title=f"{script_location} Script ({script_type}) - DataSource {ds_id}")


@app.command("edit")
def edit_datasource(
    ds_id: Annotated[int, typer.Argument(help="DataSource ID")],
    script_only: Annotated[bool, typer.Option("--script-only", "-s", help="Edit only the collection script")] = False,
    discovery: Annotated[bool, typer.Option("--discovery", "-d", help="Edit Active Discovery script")] = False,
    script_type: Annotated[str, typer.Option("--type", "-t", help="Script type: groovy, linux, windows")] = "groovy",
) -> None:
    """Edit a DataSource interactively using $EDITOR."""
    svc = _get_service()
    try:
        ds = unwrap_response(svc.export_json(ds_id))
    except Exception as e:
        console.print(f"[red]Failed to get DataSource: {e}[/red]")
        raise typer.Exit(1) from None

    ds_name = ds.get("name", f"ID:{ds_id}")

    if script_only:
        script_location = "Active Discovery" if discovery else "Collection"
        original_script = _get_script_from_ds(ds, discovery, script_type)
        if not original_script:
            console.print(f"[yellow]No {script_location} {script_type} script exists. Creating new.[/yellow]")
            original_script = ""

        ext_map = {"groovy": ".groovy", "linux": ".sh", "windows": ".ps1"}
        new_script, was_modified = edit_in_editor(original_script, ext_map.get(script_type, ".txt"), console)

        if not was_modified:
            console.print("[dim]No changes made[/dim]")
            return

        show_diff(original_script, new_script, f"{script_location} (original)", f"{script_location} (modified)", console, title=f"Changes to {script_location} {script_type} script:")

        if not typer.confirm("Push these changes?"):
            console.print("[dim]Cancelled[/dim]")
            return

        _set_script_in_ds(ds, discovery, script_type, new_script)
        try:
            get_client(console).put(f"/setting/datasources/{ds_id}", json_data=ds)
            console.print(f"[green]Pushed {script_location} {script_type} script changes to DataSource {ds_id}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to push changes: {e}[/red]")
            raise typer.Exit(1) from None
    else:
        new_ds, was_modified = edit_json_in_editor(ds, console)
        if not was_modified:
            console.print("[dim]No changes made[/dim]")
            return

        show_diff(json.dumps(ds, indent=2), json.dumps(new_ds, indent=2), f"{ds_name} (original)", f"{ds_name} (modified)", console, max_lines=50, title=f"Changes to DataSource '{ds_name}':")

        if not typer.confirm("Push these changes?"):
            console.print("[dim]Cancelled[/dim]")
            return

        try:
            get_client(console).put(f"/setting/datasources/{ds_id}", json_data=new_ds)
            console.print(f"[green]Pushed changes to DataSource '{ds_name}' (ID: {ds_id})[/green]")
        except Exception as e:
            console.print(f"[red]Failed to push changes: {e}[/red]")
            raise typer.Exit(1) from None


@app.command("push")
def push_datasource(
    ds_id: Annotated[int, typer.Argument(help="DataSource ID")],
    file: Annotated[str, typer.Argument(help="JSON file with DataSource configuration")],
    show_diff_opt: Annotated[bool, typer.Option("--diff", "-d", help="Show diff before pushing")] = True,
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Push a modified DataSource configuration from a JSON file."""
    svc = _get_service()
    new_ds = load_json_file(file, console)

    try:
        current_ds = unwrap_response(svc.export_json(ds_id))
    except Exception as e:
        console.print(f"[red]Failed to get current DataSource: {e}[/red]")
        raise typer.Exit(1) from None

    ds_name = current_ds.get("name", f"ID:{ds_id}")

    if show_diff_opt:
        current_json = json.dumps(current_ds, indent=2, sort_keys=True)
        new_json = json.dumps(new_ds, indent=2, sort_keys=True)
        if current_json == new_json:
            console.print("[dim]No differences found[/dim]")
            return
        show_diff(current_json, new_json, f"{ds_name} (current)", f"{ds_name} (from file)", console, title=f"Changes to push for DataSource '{ds_name}':")

    if not force and not typer.confirm(f"Push changes to DataSource '{ds_name}' (ID: {ds_id})?"):
        console.print("[dim]Cancelled[/dim]")
        raise typer.Exit(0) from None

    try:
        get_client(console).put(f"/setting/datasources/{ds_id}", json_data=new_ds)
        console.print(f"[green]Pushed changes to DataSource '{ds_name}' (ID: {ds_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to push changes: {e}[/red]")
        raise typer.Exit(1) from None
