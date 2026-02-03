"""
Access group management commands.

Provides commands for managing LogicMonitor access groups (RBAC).
"""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import get_client, load_json_file, unwrap_response
from lmn_tools.services.access import AccessGroupService

app = typer.Typer(help="Manage access groups (RBAC)")
console = Console()


def _get_service() -> AccessGroupService:
    """Get access group service."""
    return AccessGroupService(get_client(console))


@app.command("list")
def list_groups(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, ids")
    ] = "table",
) -> None:
    """List access groups."""
    svc = _get_service()
    groups = svc.list(filter=filter, max_items=limit)

    if format == "json":
        console.print_json(data=groups)
    elif format == "ids":
        for g in groups:
            console.print(g.get("id", ""))
    else:
        if not groups:
            console.print("[dim]No access groups found[/dim]")
            return

        table = Table(title=f"Access Groups ({len(groups)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        table.add_column("Device Groups")

        for g in groups:
            device_groups = g.get("deviceGroups", [])
            dg_count = str(len(device_groups)) if device_groups else "0"
            table.add_row(
                str(g.get("id", "")),
                g.get("name", ""),
                (g.get("description", "") or "")[:30],
                dg_count,
            )
        console.print(table)


@app.command("get")
def get_group(
    group_id: Annotated[int, typer.Argument(help="Access group ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get access group details."""
    svc = _get_service()
    response = svc.get(group_id)
    group = unwrap_response(response)

    if format == "json":
        console.print_json(data=group)
        return

    console.print(f"\n[bold cyan]{group.get('name', 'N/A')}[/bold cyan] (ID: {group_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Description", group.get("description", "N/A") or "N/A")

    console.print(detail_table)

    # Device groups
    device_groups = group.get("deviceGroups", [])
    if device_groups:
        console.print("\n[bold]Device Groups:[/bold]")
        for dg in device_groups:
            perm = dg.get("permission", "?")
            console.print(f"  - ID: {dg.get('id', 'N/A')} ({perm})")
    else:
        console.print("\n[dim]No device groups configured[/dim]")

    # Website groups
    website_groups = group.get("websiteGroups", [])
    if website_groups:
        console.print("\n[bold]Website Groups:[/bold]")
        for wg in website_groups:
            perm = wg.get("permission", "?")
            console.print(f"  - ID: {wg.get('id', 'N/A')} ({perm})")

    # Dashboard groups
    dashboard_groups = group.get("dashboardGroups", [])
    if dashboard_groups:
        console.print("\n[bold]Dashboard Groups:[/bold]")
        for dg in dashboard_groups:
            perm = dg.get("permission", "?")
            console.print(f"  - ID: {dg.get('id', 'N/A')} ({perm})")


@app.command("create")
def create_group(
    name: Annotated[str, typer.Option("--name", "-n", help="Group name")],
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Description")
    ] = None,
    config_file: Annotated[str | None, typer.Option("--config", help="JSON config file")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new access group."""
    svc = _get_service()

    group_data: dict[str, Any]
    if config_file:
        group_data = load_json_file(config_file, console)
    else:
        group_data = {"name": name}
        if description:
            group_data["description"] = description

    try:
        result = unwrap_response(svc.create(group_data))
        new_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created access group '{name}' (ID: {new_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create access group: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("update")
def update_group(
    group_id: Annotated[int, typer.Argument(help="Access group ID")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New name")] = None,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="New description")
    ] = None,
    config_file: Annotated[str | None, typer.Option("--config", help="JSON config file")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update an access group."""
    svc = _get_service()

    update_data: dict[str, Any]
    if config_file:
        update_data = load_json_file(config_file, console)
    else:
        update_data = {}
        if name:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0) from None

    try:
        result = unwrap_response(svc.update(group_id, update_data))
        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated access group {group_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update access group: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_group(
    group_id: Annotated[int, typer.Argument(help="Access group ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete an access group."""
    svc = _get_service()

    try:
        group = unwrap_response(svc.get(group_id))
        group_name = group.get("name", f"ID:{group_id}")
    except Exception:
        group_name = f"ID:{group_id}"

    if not force:
        confirm = typer.confirm(f"Delete access group '{group_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(group_id)
        console.print(f"[green]Deleted access group '{group_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete access group: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("add-device-group")
def add_device_group(
    access_group_id: Annotated[int, typer.Argument(help="Access group ID")],
    device_group_id: Annotated[int, typer.Argument(help="Device group ID to add")],
    permission: Annotated[
        str, typer.Option("--permission", "-p", help="Permission level")
    ] = "read",
) -> None:
    """Add a device group to an access group."""
    svc = _get_service()

    if permission not in ("read", "write", "manage"):
        console.print("[red]Permission must be: read, write, or manage[/red]")
        raise typer.Exit(1) from None

    try:
        svc.add_device_group(access_group_id, device_group_id, permission)
        console.print(
            f"[green]Added device group {device_group_id} to access group {access_group_id} "
            f"with {permission} permission[/green]"
        )
    except Exception as e:
        console.print(f"[red]Failed to add device group: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("device-groups")
def list_device_groups(
    access_group_id: Annotated[int, typer.Argument(help="Access group ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List device groups in an access group."""
    svc = _get_service()
    device_groups = svc.get_device_groups(access_group_id)

    if format == "json":
        console.print_json(data=device_groups)
        return

    if not device_groups:
        console.print("[dim]No device groups in this access group[/dim]")
        return

    table = Table(title=f"Device Groups in Access Group {access_group_id}")
    table.add_column("ID", style="dim")
    table.add_column("Permission")

    for dg in device_groups:
        table.add_row(str(dg.get("id", "")), dg.get("permission", ""))

    console.print(table)
