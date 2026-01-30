"""
Service Insight management commands.

Provides commands for managing LogicMonitor services (Service Insight).
"""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import get_client, load_json_file, unwrap_response
from lmn_tools.services.serviceinsight import ServiceGroupService, ServiceService

app = typer.Typer(help="Manage services (Service Insight)")
console = Console()


def _get_service() -> ServiceService:
    """Get service service."""
    return ServiceService(get_client(console))


def _get_group_service() -> ServiceGroupService:
    """Get service group service."""
    return ServiceGroupService(get_client(console))


def _status_style(status: str | int | None) -> str:
    """Get Rich style for status."""
    if status is None:
        return "dim"
    status_str = str(status).lower()
    if status_str in ("normal", "0"):
        return "green"
    elif status_str in ("warning", "1"):
        return "yellow"
    elif status_str in ("error", "2"):
        return "red"
    elif status_str in ("critical", "3"):
        return "red bold"
    return "white"


@app.command("list")
def list_services(
    group: Annotated[int | None, typer.Option("--group", "-g", help="Filter by group ID")] = None,
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List services."""
    svc = _get_service()

    if group:
        services = svc.list_by_group(group, max_items=limit)
    else:
        services = svc.list(filter=filter, max_items=limit)

    if format == "json":
        console.print_json(data=services)
    elif format == "ids":
        for s in services:
            console.print(s.get("id", ""))
    else:
        if not services:
            console.print("[dim]No services found[/dim]")
            return

        table = Table(title=f"Services ({len(services)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Status")
        table.add_column("Group ID")
        table.add_column("Description")

        for s in services:
            status = s.get("alertStatus", s.get("status", ""))
            status_styled = f"[{_status_style(status)}]{status}[/{_status_style(status)}]"
            table.add_row(
                str(s.get("id", "")),
                s.get("name", ""),
                status_styled,
                str(s.get("groupId", "")),
                (s.get("description", "") or "")[:30],
            )
        console.print(table)


@app.command("get")
def get_service_cmd(
    service_id: Annotated[int, typer.Argument(help="Service ID")],
    show_members: Annotated[bool, typer.Option("--members", "-m", help="Show members")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get service details."""
    svc = _get_service()
    response = svc.get(service_id)
    service = unwrap_response(response)

    if format == "json":
        console.print_json(data=service)
        return

    console.print(f"\n[bold cyan]{service.get('name', 'N/A')}[/bold cyan] (ID: {service_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    status = service.get("alertStatus", service.get("status", ""))
    status_styled = f"[{_status_style(status)}]{status}[/{_status_style(status)}]"

    detail_table.add_row("Status", status_styled)
    detail_table.add_row("Group ID", str(service.get("groupId", "N/A")))
    detail_table.add_row("Description", service.get("description", "N/A") or "N/A")
    detail_table.add_row("SDT Status", service.get("sdtStatus", "N/A"))

    console.print(detail_table)

    if show_members:
        members = service.get("members", [])
        if members:
            console.print("\n[bold]Members:[/bold]")
            for m in members:
                mtype = m.get("type", "?")
                mid = m.get("id", "?")
                console.print(f"  - [{mtype}] ID: {mid}")
        else:
            console.print("\n[dim]No members configured[/dim]")


@app.command("create")
def create_service(
    name: Annotated[str, typer.Option("--name", "-n", help="Service name")],
    group: Annotated[int, typer.Option("--group", "-g", help="Service group ID")] = 1,
    devices: Annotated[str | None, typer.Option("--devices", "-d", help="Comma-separated device IDs")] = None,
    description: Annotated[str | None, typer.Option("--description", help="Description")] = None,
    config_file: Annotated[str | None, typer.Option("--config", help="JSON config file")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new service."""
    svc = _get_service()

    service_data: dict[str, Any]
    if config_file:
        service_data = load_json_file(config_file, console)
    else:
        service_data = {
            "name": name,
            "groupId": group,
        }
        if description:
            service_data["description"] = description
        if devices:
            device_ids = [int(d.strip()) for d in devices.split(",")]
            service_data["members"] = [{"type": "device", "id": did} for did in device_ids]

    try:
        result = unwrap_response(svc.create(service_data))
        new_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created service '{name}' (ID: {new_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create service: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("update")
def update_service(
    service_id: Annotated[int, typer.Argument(help="Service ID")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New name")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="New description")] = None,
    group: Annotated[int | None, typer.Option("--group", "-g", help="New group ID")] = None,
    config_file: Annotated[str | None, typer.Option("--config", help="JSON config file")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update a service."""
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
        if group is not None:
            update_data["groupId"] = group

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0) from None

    try:
        result = unwrap_response(svc.update(service_id, update_data))
        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated service {service_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update service: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_service(
    service_id: Annotated[int, typer.Argument(help="Service ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a service."""
    svc = _get_service()

    try:
        service = unwrap_response(svc.get(service_id))
        service_name = service.get("name", f"ID:{service_id}")
    except Exception:
        service_name = f"ID:{service_id}"

    if not force:
        confirm = typer.confirm(f"Delete service '{service_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(service_id)
        console.print(f"[green]Deleted service '{service_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete service: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("status")
def service_status(
    service_id: Annotated[int, typer.Argument(help="Service ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get service status."""
    svc = _get_service()
    status = svc.get_status(service_id)

    if format == "json":
        console.print_json(data=status)
        return

    alert_status = status.get("alertStatus", status.get("status", ""))
    status_styled = f"[{_status_style(alert_status)}]{alert_status}[/{_status_style(alert_status)}]"

    console.print(f"\n[bold]Service Status: {status.get('name', service_id)}[/bold]")
    console.print()
    console.print(f"Alert Status: {status_styled}")
    console.print(f"SDT Status: {status.get('sdtStatus', 'N/A')}")
    console.print(f"Alert Disable Status: {status.get('alertDisableStatus', 'N/A')}")


@app.command("members")
def list_members(
    service_id: Annotated[int, typer.Argument(help="Service ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List service members."""
    svc = _get_service()
    members = svc.get_members(service_id)

    if format == "json":
        console.print_json(data=members)
        return

    if not members:
        console.print("[dim]No members in this service[/dim]")
        return

    table = Table(title=f"Members of Service {service_id}")
    table.add_column("Type")
    table.add_column("ID")

    for m in members:
        table.add_row(m.get("type", ""), str(m.get("id", "")))

    console.print(table)


@app.command("add-device")
def add_device(
    service_id: Annotated[int, typer.Argument(help="Service ID")],
    device_id: Annotated[int, typer.Argument(help="Device ID to add")],
) -> None:
    """Add a device to a service."""
    svc = _get_service()

    try:
        svc.add_device(service_id, device_id)
        console.print(f"[green]Added device {device_id} to service {service_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to add device: {e}[/red]")
        raise typer.Exit(1) from None


# Service Group commands
@app.command("groups")
def list_groups(
    parent: Annotated[int | None, typer.Option("--parent", "-p", help="Parent group ID")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List service groups."""
    svc = _get_group_service()
    groups = svc.get_children(parent) if parent is not None else svc.list()

    if format == "json":
        console.print_json(data=groups)
    elif format == "ids":
        for g in groups:
            console.print(g.get("id", ""))
    else:
        if not groups:
            console.print("[dim]No groups found[/dim]")
            return

        table = Table(title=f"Service Groups ({len(groups)})")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Parent ID")

        for g in groups:
            table.add_row(
                str(g.get("id", "")),
                g.get("name", ""),
                str(g.get("parentId", "")),
            )
        console.print(table)
