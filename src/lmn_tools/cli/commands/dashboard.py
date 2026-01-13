"""
Dashboard management commands.

Provides commands for listing, viewing, and managing LogicMonitor dashboards.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from lmn_tools.cli.utils import build_filter, get_client, load_json_file, unwrap_response
from lmn_tools.services.dashboards import DashboardGroupService, DashboardService

app = typer.Typer(help="Manage dashboards")
console = Console()


def _get_service() -> DashboardService:
    """Get dashboard service."""
    return DashboardService(get_client(console))


def _get_group_service() -> DashboardGroupService:
    """Get dashboard group service."""
    return DashboardGroupService(get_client(console))


@app.command("list")
def list_dashboards(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    group: Annotated[int | None, typer.Option("--group", "-g", help="Filter by group ID")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List dashboards with optional filtering."""
    svc = _get_service()
    filter_str = build_filter(filter, f"groupId:{group}" if group else None)
    dashboards = svc.list(filter=filter_str, max_items=limit)

    if format == "json":
        console.print_json(data=dashboards)
    elif format == "ids":
        for d in dashboards:
            console.print(d["id"])
    else:
        table = Table(title=f"Dashboards ({len(dashboards)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Group ID")
        table.add_column("Owner")
        table.add_column("Sharable")

        for d in dashboards:
            table.add_row(
                str(d["id"]),
                d.get("name", ""),
                str(d.get("groupId", "")),
                d.get("owner", ""),
                str(d.get("sharable", "")),
            )
        console.print(table)


@app.command("get")
def get_dashboard(
    identifier: Annotated[str, typer.Argument(help="Dashboard ID or name")],
    show_widgets: Annotated[bool, typer.Option("--widgets", "-w", help="Show widgets")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get dashboard details."""
    svc = _get_service()

    try:
        dashboard_id = int(identifier)
        dashboard = unwrap_response(svc.get(dashboard_id))
    except ValueError:
        results = svc.list(filter=f'name:"{identifier}"', max_items=1)
        if not results:
            console.print(f"[red]Dashboard not found: {identifier}[/red]")
            raise typer.Exit(1) from None
        dashboard = results[0]
        dashboard_id = dashboard["id"]

    if format == "json":
        if show_widgets:
            dashboard["widgets"] = svc.get_widgets(dashboard_id)
        console.print_json(data=dashboard)
        return

    console.print(f"\n[bold cyan]{dashboard.get('name', 'N/A')}[/bold cyan] (ID: {dashboard_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Group ID", str(dashboard.get("groupId", "N/A")))
    detail_table.add_row("Owner", dashboard.get("owner", "N/A"))
    detail_table.add_row("Sharable", str(dashboard.get("sharable", "N/A")))
    detail_table.add_row("Description", dashboard.get("description", "N/A") or "N/A")

    console.print(detail_table)

    if show_widgets:
        console.print("\n[bold]Widgets:[/bold]")
        widgets = svc.get_widgets(dashboard_id)
        if widgets:
            for w in widgets:
                console.print(f"  - [{w.get('type', 'unknown')}] {w.get('name', 'N/A')}")
        else:
            console.print("  [dim]No widgets[/dim]")


@app.command("widgets")
def list_widgets(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List widgets in a dashboard."""
    svc = _get_service()
    widgets = svc.get_widgets(dashboard_id)

    if format == "json":
        console.print_json(data=widgets)
        return

    if not widgets:
        console.print("[dim]No widgets found[/dim]")
        return

    table = Table(title=f"Widgets in Dashboard {dashboard_id}")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("Position")

    for w in widgets:
        pos = f"row {w.get('row', '?')}, col {w.get('col', '?')}"
        table.add_row(str(w.get("id", "")), w.get("name", ""), w.get("type", ""), pos)
    console.print(table)


@app.command("search")
def search_dashboards(
    query: Annotated[str, typer.Argument(help="Search term")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 25,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """Search dashboards by name."""
    svc = _get_service()
    results = svc.search(query, max_items=limit)

    if format == "json":
        console.print_json(data=results)
    elif format == "ids":
        for d in results:
            console.print(d["id"])
    else:
        if not results:
            console.print(f"[dim]No dashboards matching '{query}'[/dim]")
            return

        table = Table(title=f"Search Results for '{query}' ({len(results)})")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Group ID")

        for d in results[:limit]:
            table.add_row(str(d["id"]), d.get("name", ""), str(d.get("groupId", "")))
        console.print(table)


@app.command("export")
def export_dashboard(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID to export")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file path")] = None,
) -> None:
    """Export a dashboard as JSON (includes widgets)."""
    svc = _get_service()
    dashboard = svc.export_json(dashboard_id)
    json_output = json.dumps(dashboard, indent=2)

    if output:
        Path(output).write_text(json_output)
        console.print(f"[green]Exported to {output}[/green]")
    else:
        console.print(json_output)


@app.command("clone")
def clone_dashboard(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID to clone")],
    name: Annotated[str, typer.Option("--name", "-n", help="Name for the cloned dashboard")],
    group: Annotated[int | None, typer.Option("--group", "-g", help="Group ID for the clone")] = None,
) -> None:
    """Clone a dashboard."""
    svc = _get_service()

    try:
        result = unwrap_response(svc.clone(dashboard_id, name, group_id=group))
        new_id = result.get("id")
        console.print(f"[green]Cloned dashboard {dashboard_id} -> {new_id} as '{name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to clone dashboard: {e}[/red]")
        raise typer.Exit(1) from None


# Dashboard Group commands
@app.command("groups")
def list_groups(
    parent: Annotated[int | None, typer.Option("--parent", "-p", help="Parent group ID")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List dashboard groups."""
    svc = _get_group_service()
    groups = svc.get_children(parent) if parent is not None else svc.list()

    if format == "json":
        console.print_json(data=groups)
    elif format == "ids":
        for g in groups:
            console.print(g["id"])
    else:
        if not groups:
            console.print("[dim]No groups found[/dim]")
            return

        table = Table(title=f"Dashboard Groups ({len(groups)})")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Full Path")
        table.add_column("Parent ID")

        for g in groups:
            table.add_row(
                str(g["id"]), g.get("name", ""), g.get("fullPath", ""), str(g.get("parentId", ""))
            )
        console.print(table)


@app.command("group-tree")
def show_group_tree(
    parent: Annotated[int, typer.Option("--parent", "-p", help="Parent group ID")] = 1,
    depth: Annotated[int, typer.Option("--depth", "-d", help="Maximum depth")] = 5,
) -> None:
    """Show dashboard group hierarchy as a tree."""
    svc = _get_group_service()

    def _add_children(parent_tree: Tree, parent_id: int, current_depth: int) -> None:
        if current_depth <= 0:
            return
        children = svc.get_children(parent_id)
        for child in children:
            name = child.get("name", "Unknown")
            label = f"[cyan]{name}[/cyan] [dim](ID: {child['id']})[/dim]"
            child_tree = parent_tree.add(label)
            _add_children(child_tree, child["id"], current_depth - 1)

    try:
        root_data = unwrap_response(svc.get(parent))
        root_name = root_data.get("name", "Root")
    except Exception:
        root_name = "Root"

    tree = Tree(f"[bold]{root_name}[/bold]")
    _add_children(tree, parent, depth)
    console.print(tree)


# ============================================================================
# Write Operations (CRUD)
# ============================================================================


@app.command("create")
def create_dashboard(
    name: Annotated[str, typer.Argument(help="Dashboard name")],
    group: Annotated[int, typer.Option("--group", "-g", help="Dashboard group ID")] = 1,
    description: Annotated[str | None, typer.Option("--description", "-d", help="Dashboard description")] = None,
    sharable: Annotated[bool, typer.Option("--sharable/--private", help="Make dashboard sharable")] = True,
    template: Annotated[str | None, typer.Option("--template", "-t", help="Template file (JSON)")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new dashboard."""
    svc = _get_service()

    if template:
        dashboard_data = load_json_file(template, console)
        for key in ["id", "owner", "fullPath"]:
            dashboard_data.pop(key, None)
    else:
        dashboard_data = {"widgetTokens": []}

    dashboard_data["name"] = name
    dashboard_data["groupId"] = group
    dashboard_data["sharable"] = sharable
    if description:
        dashboard_data["description"] = description

    try:
        result = unwrap_response(svc.create(dashboard_data))
        dashboard_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created dashboard '{name}' (ID: {dashboard_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create dashboard: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("update")
def update_dashboard(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New name")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="New description")] = None,
    group: Annotated[int | None, typer.Option("--group", "-g", help="New group ID")] = None,
    sharable: Annotated[bool | None, typer.Option("--sharable/--private", help="Toggle sharable")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update a dashboard."""
    svc = _get_service()

    update_data: dict[str, Any] = {}
    if name:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if group is not None:
        update_data["groupId"] = group
    if sharable is not None:
        update_data["sharable"] = sharable

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0) from None

    try:
        result = unwrap_response(svc.update(dashboard_id, update_data))
        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated dashboard {dashboard_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update dashboard: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_dashboard(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a dashboard."""
    svc = _get_service()

    try:
        dashboard = unwrap_response(svc.get(dashboard_id))
        dashboard_name = dashboard.get("name", f"ID:{dashboard_id}")
    except Exception:
        dashboard_name = f"ID:{dashboard_id}"

    if not force:
        confirm = typer.confirm(f"Delete dashboard '{dashboard_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(dashboard_id)
        console.print(f"[green]Deleted dashboard '{dashboard_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete dashboard: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("import")
def import_dashboard(
    file: Annotated[str, typer.Argument(help="JSON file to import")],
    group: Annotated[int | None, typer.Option("--group", "-g", help="Target group ID")] = None,
    name: Annotated[str | None, typer.Option("--name", "-n", help="Override dashboard name")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite if name exists")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Import a dashboard from a JSON file."""
    svc = _get_service()
    dashboard_data = load_json_file(file, console)

    for key in ["id", "owner", "fullPath"]:
        dashboard_data.pop(key, None)

    if name:
        dashboard_data["name"] = name
    if group is not None:
        dashboard_data["groupId"] = group

    dashboard_name = dashboard_data.get("name", "Unknown")

    if not force:
        existing = svc.list(filter=f'name:"{dashboard_name}"', max_items=1)
        if existing:
            console.print(f"[yellow]Dashboard '{dashboard_name}' already exists (ID: {existing[0]['id']})[/yellow]")
            console.print("Use --force to overwrite or --name to rename")
            raise typer.Exit(1) from None

    try:
        result = unwrap_response(svc.create(dashboard_data))
        dashboard_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Imported dashboard '{dashboard_name}' (ID: {dashboard_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to import dashboard: {e}[/red]")
        raise typer.Exit(1) from None


# Dashboard Group write operations

@app.command("create-group")
def create_dashboard_group(
    name: Annotated[str, typer.Argument(help="Group name")],
    parent: Annotated[int, typer.Option("--parent", "-p", help="Parent group ID")] = 1,
    description: Annotated[str | None, typer.Option("--description", "-d", help="Group description")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new dashboard group."""
    svc = _get_group_service()

    group_data: dict[str, Any] = {"name": name, "parentId": parent}
    if description:
        group_data["description"] = description

    try:
        result = unwrap_response(svc.create(group_data))
        group_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created dashboard group '{name}' (ID: {group_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create group: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete-group")
def delete_dashboard_group(
    group_id: Annotated[int, typer.Argument(help="Group ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a dashboard group."""
    svc = _get_group_service()

    try:
        group = unwrap_response(svc.get(group_id))
        group_name = group.get("name", f"ID:{group_id}")
    except Exception:
        group_name = f"ID:{group_id}"

    if not force:
        confirm = typer.confirm(f"Delete dashboard group '{group_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(group_id)
        console.print(f"[green]Deleted dashboard group '{group_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete group: {e}[/red]")
        raise typer.Exit(1) from None
