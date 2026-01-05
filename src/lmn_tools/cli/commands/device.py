"""
Device management commands.

Provides commands for listing, viewing, and managing LogicMonitor devices.
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import build_filter, get_client, unwrap_response
from lmn_tools.services.devices import DeviceService

app = typer.Typer(help="Manage devices")
console = Console()


def _get_service() -> DeviceService:
    """Get device service."""
    return DeviceService(get_client(console))


@app.command("list")
def list_devices(
    filter: Annotated[Optional[str], typer.Option("--filter", "-f", help="LM filter string")] = None,
    group: Annotated[Optional[int], typer.Option("--group", "-g", help="Filter by group ID")] = None,
    collector: Annotated[Optional[int], typer.Option("--collector", "-c", help="Filter by collector ID")] = None,
    status: Annotated[Optional[str], typer.Option("--status", "-s", help="Filter by status: alive, dead")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List devices with optional filtering."""
    svc = _get_service()

    status_map = {"alive": "normal", "dead": "dead"}
    filter_str = build_filter(
        filter,
        f"hostGroupIds:{group}" if group else None,
        f"currentCollectorId:{collector}" if collector else None,
        f"hostStatus:{status_map.get(status, status)}" if status else None,
    )
    devices = svc.list(filter=filter_str, max_items=limit)

    if format == "json":
        console.print_json(data=devices)
    elif format == "ids":
        for d in devices:
            console.print(d["id"])
    else:
        table = Table(title=f"Devices ({len(devices)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Hostname", style="cyan")
        table.add_column("Display Name")
        table.add_column("Status")
        table.add_column("Collector")

        for d in devices:
            status_str = d.get("hostStatus", "")
            status_style = "green" if status_str == "normal" else "red"
            table.add_row(
                str(d["id"]),
                d.get("name", ""),
                d.get("displayName", ""),
                f"[{status_style}]{status_str}[/{status_style}]",
                str(d.get("currentCollectorId", "")),
            )
        console.print(table)


@app.command("get")
def get_device(
    identifier: Annotated[str, typer.Argument(help="Device ID or hostname")],
    show_properties: Annotated[bool, typer.Option("--properties", "-p", help="Show properties")] = False,
    show_datasources: Annotated[bool, typer.Option("--datasources", "-d", help="Show datasources")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get device details."""
    svc = _get_service()

    try:
        device_id = int(identifier)
        device = unwrap_response(svc.get(device_id))
    except ValueError:
        device = svc.find_by_hostname(identifier)
        if not device:
            console.print(f"[red]Device not found: {identifier}[/red]")
            raise typer.Exit(1)
        device_id = device["id"]

    if format == "json":
        console.print_json(data=device)
        return

    console.print(f"\n[bold cyan]{device.get('displayName', 'N/A')}[/bold cyan] (ID: {device_id})")
    console.print()

    status = device.get("hostStatus", "")
    status_style = "green" if status == "normal" else "red"

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Name (IP)", device.get("name", "N/A"))
    detail_table.add_row("Status", f"[{status_style}]{status}[/{status_style}]")
    detail_table.add_row("Collector ID", str(device.get("currentCollectorId", "N/A")))
    detail_table.add_row("Device Type", str(device.get("deviceType", "N/A")))
    detail_table.add_row("Link", device.get("link", "N/A"))
    detail_table.add_row("Created On", str(device.get("createdOn", "N/A")))

    console.print(detail_table)

    if show_properties:
        console.print("\n[bold]Custom Properties:[/bold]")
        props = svc.get_properties(device_id)
        if props:
            prop_table = Table(show_header=True, box=None)
            prop_table.add_column("Name", style="dim")
            prop_table.add_column("Value")
            for p in props:
                if p.get("type") == "custom":
                    prop_table.add_row(p.get("name", ""), p.get("value", ""))
            console.print(prop_table)
        else:
            console.print("  [dim]No custom properties[/dim]")

    if show_datasources:
        console.print("\n[bold]DataSources:[/bold]")
        datasources = svc.get_datasources(device_id)
        if datasources:
            for ds in datasources[:20]:
                console.print(f"  - {ds.get('dataSourceDisplayName', ds.get('dataSourceName', 'N/A'))}")
            if len(datasources) > 20:
                console.print(f"  [dim]... and {len(datasources) - 20} more[/dim]")
        else:
            console.print("  [dim]No datasources applied[/dim]")


@app.command("search")
def search_devices(
    query: Annotated[str, typer.Argument(help="Search term")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 25,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """Search devices by hostname or display name."""
    svc = _get_service()
    results = svc.list(filter=f"displayName~*{query}*", max_items=limit)

    if format == "json":
        console.print_json(data=results)
    elif format == "ids":
        for d in results:
            console.print(d["id"])
    else:
        if not results:
            console.print(f"[dim]No devices matching '{query}'[/dim]")
            return

        table = Table(title=f"Search Results for '{query}' ({len(results)})")
        table.add_column("ID", style="dim")
        table.add_column("Display Name", style="cyan")
        table.add_column("Name (IP)")
        table.add_column("Status")

        for d in results:
            status = d.get("hostStatus", "")
            status_style = "green" if status == "normal" else "red"
            table.add_row(
                str(d["id"]),
                d.get("displayName", ""),
                d.get("name", ""),
                f"[{status_style}]{status}[/{status_style}]",
            )
        console.print(table)


@app.command("datasources")
def list_device_datasources(
    device_id: Annotated[int, typer.Argument(help="Device ID")],
    filter: Annotated[Optional[str], typer.Option("--filter", "-f", help="Filter by datasource name")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List DataSources applied to a device."""
    svc = _get_service()
    datasources = svc.get_datasources(device_id, datasource_name=filter)

    if format == "json":
        console.print_json(data=datasources)
        return

    if not datasources:
        console.print("[dim]No datasources found[/dim]")
        return

    table = Table(title=f"DataSources for Device {device_id} ({len(datasources)})")
    table.add_column("DS ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Display Name")
    table.add_column("Instances")

    for ds in datasources:
        table.add_row(
            str(ds.get("id", "")),
            ds.get("dataSourceName", ""),
            ds.get("dataSourceDisplayName", ""),
            str(ds.get("instanceNumber", 0)),
        )
    console.print(table)


@app.command("properties")
def list_device_properties(
    device_id: Annotated[int, typer.Argument(help="Device ID")],
    type: Annotated[Optional[str], typer.Option("--type", "-t", help="Property type: custom, system, auto")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List device properties."""
    svc = _get_service()
    properties = svc.get_properties(device_id)

    if type:
        properties = [p for p in properties if p.get("type") == type]

    if format == "json":
        console.print_json(data=properties)
        return

    if not properties:
        console.print("[dim]No properties found[/dim]")
        return

    table = Table(title=f"Properties for Device {device_id}")
    table.add_column("Name", style="cyan")
    table.add_column("Value")
    table.add_column("Type", style="dim")

    for p in properties:
        value = p.get("value", "")
        if len(value) > 50:
            value = value[:50] + "..."
        table.add_row(p.get("name", ""), value, p.get("type", ""))
    console.print(table)


@app.command("dead")
def list_dead_devices(
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List devices with dead status."""
    svc = _get_service()
    devices = svc.list_dead()

    if format == "json":
        console.print_json(data=devices)
    elif format == "ids":
        for d in devices:
            console.print(d["id"])
    else:
        if not devices:
            console.print("[green]No dead devices found[/green]")
            return

        table = Table(title=f"Dead Devices ({len(devices)})")
        table.add_column("ID", style="dim")
        table.add_column("Display Name", style="cyan")
        table.add_column("Name (IP)")
        table.add_column("Collector")

        for d in devices:
            table.add_row(
                str(d["id"]),
                d.get("displayName", ""),
                d.get("name", ""),
                str(d.get("currentCollectorId", "")),
            )
        console.print(table)


# ============================================================================
# Write Operations (CRUD)
# ============================================================================


@app.command("create")
def create_device(
    name: Annotated[str, typer.Argument(help="Device IP or hostname")],
    display_name: Annotated[str, typer.Option("--display-name", "-d", help="Display name")],
    group: Annotated[int, typer.Option("--group", "-g", help="Host group ID")] = 1,
    collector: Annotated[Optional[int], typer.Option("--collector", "-c", help="Preferred collector ID")] = None,
    description: Annotated[Optional[str], typer.Option("--description", help="Device description")] = None,
    properties: Annotated[Optional[str], typer.Option("--properties", "-p", help="Custom properties as JSON")] = None,
    disable_alerting: Annotated[bool, typer.Option("--disable-alerting", help="Disable alerting on creation")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new device."""
    svc = _get_service()

    device_data: dict = {
        "name": name,
        "displayName": display_name,
        "hostGroupIds": str(group),
        "disableAlerting": disable_alerting,
    }

    if collector:
        device_data["preferredCollectorId"] = collector
    if description:
        device_data["description"] = description

    if properties:
        try:
            props = json.loads(properties)
            device_data["customProperties"] = [{"name": k, "value": v} for k, v in props.items()]
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON for properties: {e}[/red]")
            raise typer.Exit(1)

    try:
        result = unwrap_response(svc.create(device_data))
        device_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created device '{display_name}' with ID: {device_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create device: {e}[/red]")
        raise typer.Exit(1)


@app.command("update")
def update_device(
    device_id: Annotated[int, typer.Argument(help="Device ID")],
    display_name: Annotated[Optional[str], typer.Option("--display-name", "-d", help="New display name")] = None,
    description: Annotated[Optional[str], typer.Option("--description", help="New description")] = None,
    group: Annotated[Optional[int], typer.Option("--group", "-g", help="New host group ID")] = None,
    collector: Annotated[Optional[int], typer.Option("--collector", "-c", help="New preferred collector ID")] = None,
    disable_alerting: Annotated[Optional[bool], typer.Option("--disable-alerting/--enable-alerting", help="Toggle alerting")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update a device's properties."""
    svc = _get_service()

    update_data: dict = {}
    if display_name:
        update_data["displayName"] = display_name
    if description is not None:
        update_data["description"] = description
    if group:
        update_data["hostGroupIds"] = str(group)
    if collector:
        update_data["preferredCollectorId"] = collector
    if disable_alerting is not None:
        update_data["disableAlerting"] = disable_alerting

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0)

    try:
        result = unwrap_response(svc.update(device_id, update_data))
        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated device {device_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update device: {e}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_device(
    device_id: Annotated[int, typer.Argument(help="Device ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
    delete_hard: Annotated[bool, typer.Option("--hard", help="Hard delete (immediate, not 30-day retention)")] = False,
) -> None:
    """Delete a device."""
    svc = _get_service()

    try:
        device = unwrap_response(svc.get(device_id))
        display_name = device.get("displayName", f"ID:{device_id}")
    except Exception:
        display_name = f"ID:{device_id}"

    if not force:
        delete_type = "HARD delete" if delete_hard else "delete"
        confirm = typer.confirm(f"{delete_type} device '{display_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    try:
        if delete_hard:
            svc.client.delete(f"{svc.base_path}/{device_id}?deleteHard=true")
        else:
            svc.delete(device_id)
        console.print(f"[green]Deleted device '{display_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete device: {e}[/red]")
        raise typer.Exit(1)


@app.command("set-property")
def set_device_property(
    device_id: Annotated[int, typer.Argument(help="Device ID")],
    name: Annotated[str, typer.Argument(help="Property name")],
    value: Annotated[str, typer.Argument(help="Property value")],
) -> None:
    """Set a custom property on a device."""
    svc = _get_service()

    try:
        svc.set_property(device_id, name, value)
        console.print(f"[green]Set property '{name}' = '{value}' on device {device_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to set property: {e}[/red]")
        raise typer.Exit(1)


@app.command("delete-property")
def delete_device_property(
    device_id: Annotated[int, typer.Argument(help="Device ID")],
    name: Annotated[str, typer.Argument(help="Property name")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a custom property from a device."""
    svc = _get_service()

    if not force:
        confirm = typer.confirm(f"Delete property '{name}' from device {device_id}?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    try:
        svc.client.delete(f"{svc.base_path}/{device_id}/properties/{name}")
        console.print(f"[green]Deleted property '{name}' from device {device_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete property: {e}[/red]")
        raise typer.Exit(1)
