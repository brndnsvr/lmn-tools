"""
Topology map management commands.

Provides commands for managing LogicMonitor topology/resource maps.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import get_client, load_json_file, unwrap_response
from lmn_tools.services.topology import TopologyService

app = typer.Typer(help="Manage topology maps")
console = Console()


def _get_service() -> TopologyService:
    """Get topology service."""
    return TopologyService(get_client(console))


@app.command("list")
def list_maps(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List topology maps."""
    svc = _get_service()
    maps = svc.list(filter=filter, max_items=limit)

    if format == "json":
        console.print_json(data=maps)
    elif format == "ids":
        for m in maps:
            console.print(m.get("id", ""))
    else:
        if not maps:
            console.print("[dim]No topology maps found[/dim]")
            return

        table = Table(title=f"Topology Maps ({len(maps)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Description")

        for m in maps:
            table.add_row(
                str(m.get("id", "")),
                m.get("name", ""),
                m.get("type", ""),
                (m.get("description", "") or "")[:40],
            )
        console.print(table)


@app.command("get")
def get_map(
    map_id: Annotated[int, typer.Argument(help="Topology map ID")],
    show_data: Annotated[bool, typer.Option("--data", "-d", help="Include map data")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get topology map details."""
    svc = _get_service()
    response = svc.get(map_id)
    topo_map = unwrap_response(response)

    if show_data:
        map_data = svc.get_map_data(map_id)
        topo_map["mapData"] = unwrap_response(map_data)

    if format == "json":
        console.print_json(data=topo_map)
        return

    console.print(f"\n[bold cyan]{topo_map.get('name', 'N/A')}[/bold cyan] (ID: {map_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Type", topo_map.get("type", "N/A"))
    detail_table.add_row("Description", topo_map.get("description", "N/A") or "N/A")

    console.print(detail_table)

    if show_data and "mapData" in topo_map:
        map_data = topo_map["mapData"]
        vertices = map_data.get("vertices", [])
        edges = map_data.get("edges", [])
        console.print("\n[bold]Map Data:[/bold]")
        console.print(f"  Vertices: {len(vertices)}")
        console.print(f"  Edges: {len(edges)}")


@app.command("create")
def create_map(
    name: Annotated[str, typer.Option("--name", "-n", help="Map name")],
    devices: Annotated[str | None, typer.Option("--devices", "-d", help="Comma-separated device IDs")] = None,
    description: Annotated[str | None, typer.Option("--description", help="Description")] = None,
    config_file: Annotated[str | None, typer.Option("--config", help="JSON config file")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new topology map."""
    svc = _get_service()

    map_data: dict[str, Any]
    if config_file:
        map_data = load_json_file(config_file, console)
    else:
        map_data = {"name": name, "type": "manual"}
        if description:
            map_data["description"] = description
        if devices:
            device_ids = [int(d.strip()) for d in devices.split(",")]
            map_data["vertices"] = [{"type": "device", "id": did} for did in device_ids]

    try:
        result = unwrap_response(svc.create(map_data))
        new_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created topology map '{name}' (ID: {new_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create topology map: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("update")
def update_map(
    map_id: Annotated[int, typer.Argument(help="Topology map ID")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New name")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="New description")] = None,
    config_file: Annotated[str | None, typer.Option("--config", help="JSON config file")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update a topology map."""
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
        result = unwrap_response(svc.update(map_id, update_data))
        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated topology map {map_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update topology map: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_map(
    map_id: Annotated[int, typer.Argument(help="Topology map ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a topology map."""
    svc = _get_service()

    try:
        topo_map = unwrap_response(svc.get(map_id))
        map_name = topo_map.get("name", f"ID:{map_id}")
    except Exception:
        map_name = f"ID:{map_id}"

    if not force:
        confirm = typer.confirm(f"Delete topology map '{map_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(map_id)
        console.print(f"[green]Deleted topology map '{map_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete topology map: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("export")
def export_map(
    map_id: Annotated[int, typer.Argument(help="Topology map ID to export")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file path")] = None,
    format: Annotated[str, typer.Option("--format", help="Export format: json")] = "json",
) -> None:
    """Export a topology map as JSON."""
    svc = _get_service()
    export_data = svc.export_map(map_id)
    json_output = json.dumps(export_data, indent=2)

    if output:
        Path(output).write_text(json_output)
        console.print(f"[green]Exported topology map to {output}[/green]")
    else:
        console.print(json_output)


@app.command("data")
def show_map_data(
    map_id: Annotated[int, typer.Argument(help="Topology map ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Show topology map data (vertices and edges)."""
    svc = _get_service()
    response = svc.get_map_data(map_id)
    map_data = unwrap_response(response)

    if format == "json":
        console.print_json(data=map_data)
        return

    vertices = map_data.get("vertices", [])
    edges = map_data.get("edges", [])

    console.print(f"\n[bold]Topology Map {map_id} Data[/bold]")
    console.print()

    if vertices:
        console.print(f"[bold]Vertices ({len(vertices)}):[/bold]")
        vertex_table = Table()
        vertex_table.add_column("Type")
        vertex_table.add_column("ID")
        vertex_table.add_column("Name")

        for v in vertices[:20]:
            vertex_table.add_row(
                v.get("type", ""),
                str(v.get("id", "")),
                v.get("name", ""),
            )
        console.print(vertex_table)
        if len(vertices) > 20:
            console.print(f"[dim]... and {len(vertices) - 20} more[/dim]")
    else:
        console.print("[dim]No vertices[/dim]")

    if edges:
        console.print(f"\n[bold]Edges ({len(edges)}):[/bold]")
        edge_table = Table()
        edge_table.add_column("From")
        edge_table.add_column("To")
        edge_table.add_column("Type")

        for e in edges[:20]:
            edge_table.add_row(
                str(e.get("from", "")),
                str(e.get("to", "")),
                e.get("type", ""),
            )
        console.print(edge_table)
        if len(edges) > 20:
            console.print(f"[dim]... and {len(edges) - 20} more[/dim]")
    else:
        console.print("\n[dim]No edges[/dim]")


@app.command("add-device")
def add_device(
    map_id: Annotated[int, typer.Argument(help="Topology map ID")],
    device_id: Annotated[int, typer.Argument(help="Device ID to add")],
) -> None:
    """Add a device to a topology map."""
    svc = _get_service()

    try:
        svc.add_device(map_id, device_id)
        console.print(f"[green]Added device {device_id} to topology map {map_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to add device: {e}[/red]")
        raise typer.Exit(1) from None
