"""
Device group management commands.

Provides commands for listing and viewing LogicMonitor device groups.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import get_settings
from lmn_tools.services.devices import DeviceGroupService

app = typer.Typer(help="Manage device groups")
console = Console()


def _get_client() -> LMClient:
    """Get authenticated API client."""
    settings = get_settings()
    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        raise typer.Exit(1) from None
    return LMClient.from_credentials(settings.credentials)  # type: ignore


def _get_service() -> DeviceGroupService:
    """Get device group service."""
    return DeviceGroupService(_get_client())


@app.command("list")
def list_groups(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    parent: Annotated[
        int | None, typer.Option("--parent", "-p", help="Filter by parent group ID")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 100,
    format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, ids")
    ] = "table",
) -> None:
    """List device groups."""
    svc = _get_service()

    filters = []
    if filter:
        filters.append(filter)
    if parent is not None:
        filters.append(f"parentId:{parent}")
    filter_str = ",".join(filters) if filters else None

    groups = svc.list(filter=filter_str, max_items=limit)

    if format == "json":
        console.print_json(data=groups)
    elif format == "ids":
        for g in groups:
            console.print(g["id"])
    else:
        table = Table(title=f"Device Groups ({len(groups)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Full Path")
        table.add_column("Devices", justify="right")

        for g in groups:
            table.add_row(
                str(g["id"]),
                g.get("name", ""),
                g.get("fullPath", ""),
                str(g.get("numOfDirectDevices", 0)),
            )
        console.print(table)


@app.command("get")
def get_group(
    identifier: Annotated[str, typer.Argument(help="Group ID or path")],
    show_properties: Annotated[
        bool, typer.Option("--properties", "-p", help="Show properties")
    ] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get device group details."""
    svc = _get_service()

    # Try as ID first, then search by path
    try:
        group_id = int(identifier)
        response = svc.get(group_id)
        group = response.get("data", response) if "data" in response else response
    except ValueError:
        group = svc.get_by_path(identifier)
        if not group:
            console.print(f"[red]Group not found: {identifier}[/red]")
            raise typer.Exit(1) from None
        group_id = group["id"]

    if format == "json":
        console.print_json(data=group)
        return

    console.print(f"\n[bold cyan]{group.get('name', 'N/A')}[/bold cyan] (ID: {group_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Full Path", group.get("fullPath", "N/A"))
    detail_table.add_row("Parent ID", str(group.get("parentId", "N/A")))
    detail_table.add_row("Direct Devices", str(group.get("numOfDirectDevices", 0)))
    detail_table.add_row("All Devices", str(group.get("numOfHosts", 0)))
    detail_table.add_row("Subgroups", str(group.get("numOfDirectSubGroups", 0)))

    console.print(detail_table)

    if show_properties:
        console.print("\n[bold]Properties:[/bold]")
        props = svc.get_properties(group_id)
        if props:
            prop_table = Table(show_header=True, box=None)
            prop_table.add_column("Name", style="dim")
            prop_table.add_column("Value")
            for p in props:
                value = p.get("value", "")
                if len(value) > 50:
                    value = value[:50] + "..."
                prop_table.add_row(p.get("name", ""), value)
            console.print(prop_table)
        else:
            console.print("  [dim]No properties[/dim]")


@app.command("devices")
def list_group_devices(
    group_id: Annotated[int, typer.Argument(help="Group ID")],
    format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, ids")
    ] = "table",
) -> None:
    """List devices in a group."""
    svc = _get_service()
    devices = svc.get_devices(group_id)

    if format == "json":
        console.print_json(data=devices)
    elif format == "ids":
        for d in devices:
            console.print(d["id"])
    else:
        if not devices:
            console.print("[dim]No devices in this group[/dim]")
            return

        table = Table(title=f"Devices in Group {group_id} ({len(devices)})")
        table.add_column("ID", style="dim")
        table.add_column("Display Name", style="cyan")
        table.add_column("Status")

        for d in devices:
            status = d.get("hostStatus", "")
            status_style = "green" if status == "normal" else "red"
            table.add_row(
                str(d["id"]),
                d.get("displayName", ""),
                f"[{status_style}]{status}[/{status_style}]",
            )
        console.print(table)


@app.command("tree")
def show_tree(
    parent: Annotated[int, typer.Option("--parent", "-p", help="Parent group ID")] = 1,
    depth: Annotated[int, typer.Option("--depth", "-d", help="Maximum depth")] = 5,
) -> None:
    """Show group hierarchy as a tree."""
    svc = _get_service()

    def _add_children(parent_tree: Tree, parent_id: int, current_depth: int) -> None:
        if current_depth <= 0:
            return
        children = svc.get_children(parent_id)
        for child in children:
            name = child.get("name", "Unknown")
            device_count = child.get("numOfDirectDevices", 0)
            label = f"[cyan]{name}[/cyan] [dim]({device_count} devices)[/dim]"
            child_tree = parent_tree.add(label)
            _add_children(child_tree, child["id"], current_depth - 1)

    # Get the root group name
    try:
        root = svc.get(parent)
        root_data = root.get("data", root) if "data" in root else root
        root_name = root_data.get("name", "Root")
    except Exception:
        root_name = "Root"

    tree = Tree(f"[bold]{root_name}[/bold]")
    _add_children(tree, parent, depth)
    console.print(tree)


@app.command("children")
def list_children(
    parent_id: Annotated[int, typer.Argument(help="Parent group ID")] = 1,
    format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, ids")
    ] = "table",
) -> None:
    """List child groups of a parent."""
    svc = _get_service()
    children = svc.get_children(parent_id)

    if format == "json":
        console.print_json(data=children)
    elif format == "ids":
        for c in children:
            console.print(c["id"])
    else:
        if not children:
            console.print("[dim]No child groups[/dim]")
            return

        table = Table(title=f"Children of Group {parent_id} ({len(children)})")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Devices", justify="right")
        table.add_column("Subgroups", justify="right")

        for c in children:
            table.add_row(
                str(c["id"]),
                c.get("name", ""),
                str(c.get("numOfDirectDevices", 0)),
                str(c.get("numOfDirectSubGroups", 0)),
            )
        console.print(table)


# ============================================================================
# Write Operations (CRUD)
# ============================================================================


@app.command("create")
def create_group(
    name: Annotated[str, typer.Argument(help="Group name")],
    parent: Annotated[int, typer.Option("--parent", "-p", help="Parent group ID")] = 1,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Group description")
    ] = None,
    applies_to: Annotated[
        str | None,
        typer.Option("--applies-to", "-a", help="AppliesTo expression for dynamic group"),
    ] = None,
    properties: Annotated[
        str | None, typer.Option("--properties", help="Custom properties as JSON")
    ] = None,
    disable_alerting: Annotated[
        bool, typer.Option("--disable-alerting", help="Disable alerting for group")
    ] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new device group."""
    svc = _get_service()

    group_data: dict[str, Any] = {
        "name": name,
        "parentId": parent,
        "disableAlerting": disable_alerting,
    }

    if description:
        group_data["description"] = description

    if applies_to:
        group_data["appliesTo"] = applies_to

    if properties:
        try:
            props = json.loads(properties)
            group_data["customProperties"] = [{"name": k, "value": v} for k, v in props.items()]
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON for properties: {e}[/red]")
            raise typer.Exit(1) from None

    try:
        response = svc.create(group_data)
        result = response.get("data", response) if "data" in response else response
        group_id = result.get("id")
        full_path = result.get("fullPath", "")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created group '{name}' (ID: {group_id})[/green]")
            console.print(f"[dim]Path: {full_path}[/dim]")
    except Exception as e:
        console.print(f"[red]Failed to create group: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("update")
def update_group(
    group_id: Annotated[int, typer.Argument(help="Group ID")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New group name")] = None,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="New description")
    ] = None,
    parent: Annotated[
        int | None, typer.Option("--parent", "-p", help="New parent group ID (moves group)")
    ] = None,
    applies_to: Annotated[
        str | None, typer.Option("--applies-to", "-a", help="New AppliesTo expression")
    ] = None,
    disable_alerting: Annotated[
        bool | None, typer.Option("--disable-alerting/--enable-alerting", help="Toggle alerting")
    ] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update a device group."""
    svc = _get_service()

    update_data: dict[str, Any] = {}

    if name:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if parent is not None:
        update_data["parentId"] = parent
    if applies_to is not None:
        update_data["appliesTo"] = applies_to
    if disable_alerting is not None:
        update_data["disableAlerting"] = disable_alerting

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0) from None

    try:
        response = svc.update(group_id, update_data)
        result = response.get("data", response) if "data" in response else response

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated group {group_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update group: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_group(
    group_id: Annotated[int, typer.Argument(help="Group ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
    delete_devices: Annotated[
        bool, typer.Option("--delete-devices", help="Also delete devices in group")
    ] = False,
    delete_hard: Annotated[bool, typer.Option("--hard", help="Hard delete (immediate)")] = False,
) -> None:
    """Delete a device group."""
    svc = _get_service()

    # Get group info first
    try:
        response = svc.get(group_id)
        group = response.get("data", response) if "data" in response else response
        group_name = group.get("name", f"ID:{group_id}")
        device_count = group.get("numOfDirectDevices", 0)
    except Exception:
        group_name = f"ID:{group_id}"
        device_count = 0

    if not force:
        msg = f"Delete group '{group_name}'?"
        if device_count > 0:
            msg = f"Delete group '{group_name}' ({device_count} devices)?"
        confirm = typer.confirm(msg)
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        params = []
        if delete_devices:
            params.append("deleteDevices=true")
        if delete_hard:
            params.append("deleteHard=true")

        path = f"{svc.base_path}/{group_id}"
        if params:
            path += "?" + "&".join(params)

        svc.client.delete(path)
        console.print(f"[green]Deleted group '{group_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete group: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("set-property")
def set_group_property(
    group_id: Annotated[int, typer.Argument(help="Group ID")],
    name: Annotated[str, typer.Argument(help="Property name")],
    value: Annotated[str, typer.Argument(help="Property value")],
) -> None:
    """Set a custom property on a group."""
    svc = _get_service()

    try:
        svc.client.post(
            f"{svc.base_path}/{group_id}/properties",
            json_data={"name": name, "value": value},
        )
        console.print(f"[green]Set property '{name}' = '{value}' on group {group_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to set property: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete-property")
def delete_group_property(
    group_id: Annotated[int, typer.Argument(help="Group ID")],
    name: Annotated[str, typer.Argument(help="Property name")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a custom property from a group."""
    svc = _get_service()

    if not force:
        confirm = typer.confirm(f"Delete property '{name}' from group {group_id}?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.client.delete(f"{svc.base_path}/{group_id}/properties/{name}")
        console.print(f"[green]Deleted property '{name}' from group {group_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete property: {e}[/red]")
        raise typer.Exit(1) from None
