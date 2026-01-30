"""
Widget management commands.

Provides commands for managing LogicMonitor dashboard widgets.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import get_client, load_json_file, unwrap_response
from lmn_tools.services.dashboards import WidgetService

app = typer.Typer(help="Manage dashboard widgets")
console = Console()


def _get_service() -> WidgetService:
    """Get widget service."""
    return WidgetService(get_client(console))


@app.command("list")
def list_widgets(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List widgets in a dashboard."""
    svc = _get_service()
    widgets = svc.list_by_dashboard(dashboard_id)

    if format == "json":
        console.print_json(data=widgets)
    elif format == "ids":
        for w in widgets:
            console.print(w.get("id", ""))
    else:
        if not widgets:
            console.print("[dim]No widgets found[/dim]")
            return

        table = Table(title=f"Widgets in Dashboard {dashboard_id} ({len(widgets)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Position")
        table.add_column("Size")

        for w in widgets:
            pos = f"row {w.get('row', '?')}, col {w.get('col', '?')}"
            size = f"{w.get('width', '?')}x{w.get('height', '?')}"
            table.add_row(
                str(w.get("id", "")),
                w.get("name", ""),
                w.get("type", ""),
                pos,
                size,
            )
        console.print(table)


@app.command("get")
def get_widget(
    widget_id: Annotated[int, typer.Argument(help="Widget ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get widget details."""
    svc = _get_service()
    response = svc.get(widget_id)
    widget = unwrap_response(response)

    if format == "json":
        console.print_json(data=widget)
        return

    console.print(f"\n[bold cyan]{widget.get('name', 'N/A')}[/bold cyan] (ID: {widget_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Type", widget.get("type", "N/A"))
    detail_table.add_row("Dashboard ID", str(widget.get("dashboardId", "N/A")))
    detail_table.add_row("Position", f"row {widget.get('row', 'N/A')}, col {widget.get('col', 'N/A')}")
    detail_table.add_row("Size", f"{widget.get('width', 'N/A')}x{widget.get('height', 'N/A')}")
    detail_table.add_row("Description", widget.get("description", "N/A") or "N/A")

    console.print(detail_table)


@app.command("create")
def create_widget(
    dashboard_id: Annotated[int, typer.Argument(help="Dashboard ID")],
    name: Annotated[str, typer.Option("--name", "-n", help="Widget name")],
    widget_type: Annotated[str, typer.Option("--type", "-t", help="Widget type (e.g., text, bigNumber, gauge)")],
    row: Annotated[int, typer.Option("--row", "-r", help="Row position")] = 1,
    col: Annotated[int, typer.Option("--col", "-c", help="Column position")] = 1,
    width: Annotated[int, typer.Option("--width", "-w", help="Widget width")] = 4,
    height: Annotated[int, typer.Option("--height", help="Widget height")] = 4,
    config_file: Annotated[str | None, typer.Option("--config", help="JSON config file")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new widget on a dashboard."""
    svc = _get_service()

    widget_data: dict[str, Any]
    if config_file:
        widget_data = load_json_file(config_file, console)
    else:
        widget_data = {}

    widget_data["name"] = name
    widget_data["type"] = widget_type
    widget_data["row"] = row
    widget_data["col"] = col
    widget_data["width"] = width
    widget_data["height"] = height

    try:
        result = unwrap_response(svc.create_for_dashboard(dashboard_id, widget_data))
        new_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created widget '{name}' (ID: {new_id}) on dashboard {dashboard_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create widget: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("update")
def update_widget(
    widget_id: Annotated[int, typer.Argument(help="Widget ID")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New name")] = None,
    row: Annotated[int | None, typer.Option("--row", "-r", help="New row position")] = None,
    col: Annotated[int | None, typer.Option("--col", "-c", help="New column position")] = None,
    width: Annotated[int | None, typer.Option("--width", "-w", help="New width")] = None,
    height: Annotated[int | None, typer.Option("--height", help="New height")] = None,
    config_file: Annotated[str | None, typer.Option("--config", help="JSON config file")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update a widget."""
    svc = _get_service()

    update_data: dict[str, Any]
    if config_file:
        update_data = load_json_file(config_file, console)
    else:
        update_data = {}

    if name:
        update_data["name"] = name
    if row is not None:
        update_data["row"] = row
    if col is not None:
        update_data["col"] = col
    if width is not None:
        update_data["width"] = width
    if height is not None:
        update_data["height"] = height

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0) from None

    try:
        result = unwrap_response(svc.update(widget_id, update_data))
        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated widget {widget_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update widget: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_widget(
    widget_id: Annotated[int, typer.Argument(help="Widget ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a widget."""
    svc = _get_service()

    try:
        widget = unwrap_response(svc.get(widget_id))
        widget_name = widget.get("name", f"ID:{widget_id}")
    except Exception:
        widget_name = f"ID:{widget_id}"

    if not force:
        confirm = typer.confirm(f"Delete widget '{widget_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(widget_id)
        console.print(f"[green]Deleted widget '{widget_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete widget: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("clone")
def clone_widget(
    widget_id: Annotated[int, typer.Argument(help="Widget ID to clone")],
    dashboard_id: Annotated[int, typer.Option("--to-dashboard", "-d", help="Target dashboard ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Clone a widget to another dashboard."""
    svc = _get_service()

    try:
        result = unwrap_response(svc.clone(widget_id, dashboard_id))
        new_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Cloned widget {widget_id} -> {new_id} to dashboard {dashboard_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to clone widget: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("export")
def export_widget(
    widget_id: Annotated[int, typer.Argument(help="Widget ID to export")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file path")] = None,
) -> None:
    """Export a widget configuration as JSON."""
    svc = _get_service()
    widget = unwrap_response(svc.get(widget_id))
    json_output = json.dumps(widget, indent=2)

    if output:
        from pathlib import Path

        Path(output).write_text(json_output)
        console.print(f"[green]Exported to {output}[/green]")
    else:
        console.print(json_output)
