"""
Raw API access commands.

Provides direct access to the LogicMonitor API for power users.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer
from rich.console import Console

from lmn_tools.cli.utils import get_client

app = typer.Typer(help="Raw API access")
console = Console()


@app.command("get")
def api_get(
    path: Annotated[str, typer.Argument(help="API path (e.g., /device/devices)")],
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="Filter string")] = None,
    fields: Annotated[str | None, typer.Option("--fields", help="Comma-separated fields")] = None,
    size: Annotated[int, typer.Option("--size", "-s", help="Page size")] = 50,
    offset: Annotated[int, typer.Option("--offset", "-o", help="Offset")] = 0,
    raw: Annotated[
        bool, typer.Option("--raw", "-r", help="Show raw response without formatting")
    ] = False,
) -> None:
    """Make a GET request to the API."""
    client = get_client(console)

    params: dict[str, Any] = {"size": size, "offset": offset}
    if filter:
        params["filter"] = filter
    if fields:
        params["fields"] = fields

    try:
        response = client.get(path, params=params)
        if raw:
            console.print(json.dumps(response, indent=2))
        else:
            console.print_json(data=response)
    except Exception as e:
        console.print(f"[red]API Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("post")
def api_post(
    path: Annotated[str, typer.Argument(help="API path")],
    data: Annotated[str, typer.Option("--data", "-d", help="JSON data to send")],
    raw: Annotated[bool, typer.Option("--raw", "-r", help="Show raw response")] = False,
) -> None:
    """Make a POST request to the API."""
    client = get_client(console)

    try:
        json_data = json.loads(data)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1) from None

    try:
        response = client.post(path, json_data=json_data)
        if raw:
            console.print(json.dumps(response, indent=2))
        else:
            console.print_json(data=response)
    except Exception as e:
        console.print(f"[red]API Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("patch")
def api_patch(
    path: Annotated[str, typer.Argument(help="API path")],
    data: Annotated[str, typer.Option("--data", "-d", help="JSON data to send")],
    raw: Annotated[bool, typer.Option("--raw", "-r", help="Show raw response")] = False,
) -> None:
    """Make a PATCH request to the API."""
    client = get_client(console)

    try:
        json_data = json.loads(data)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1) from None

    try:
        response = client.patch(path, json_data=json_data)
        if raw:
            console.print(json.dumps(response, indent=2))
        else:
            console.print_json(data=response)
    except Exception as e:
        console.print(f"[red]API Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("put")
def api_put(
    path: Annotated[str, typer.Argument(help="API path")],
    data: Annotated[str, typer.Option("--data", "-d", help="JSON data to send")],
    raw: Annotated[bool, typer.Option("--raw", "-r", help="Show raw response")] = False,
) -> None:
    """Make a PUT request to the API."""
    client = get_client(console)

    try:
        json_data = json.loads(data)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1) from None

    try:
        response = client.put(path, json_data=json_data)
        if raw:
            console.print(json.dumps(response, indent=2))
        else:
            console.print_json(data=response)
    except Exception as e:
        console.print(f"[red]API Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def api_delete(
    path: Annotated[str, typer.Argument(help="API path")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
    raw: Annotated[bool, typer.Option("--raw", "-r", help="Show raw response")] = False,
) -> None:
    """Make a DELETE request to the API."""
    if not force:
        confirm = typer.confirm(f"Delete {path}?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    client = get_client(console)

    try:
        response = client.delete(path)
        if raw:
            console.print(json.dumps(response, indent=2))
        else:
            console.print_json(data=response)
    except Exception as e:
        console.print(f"[red]API Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("endpoints")
def list_endpoints() -> None:
    """Show common API endpoints."""
    endpoints = [
        ("/device/devices", "List all devices"),
        ("/device/groups", "List device groups"),
        ("/alert/alerts", "List alerts"),
        ("/sdt/sdts", "List SDTs (maintenance windows)"),
        ("/dashboard/dashboards", "List dashboards"),
        ("/dashboard/groups", "List dashboard groups"),
        ("/setting/datasources", "List DataSources"),
        ("/setting/propertyrules", "List PropertySources"),
        ("/setting/eventsources", "List EventSources"),
        ("/setting/configsources", "List ConfigSources"),
        ("/setting/topologysources", "List TopologySources"),
        ("/setting/collector/collectors", "List collectors"),
        ("/setting/admins", "List users/admins"),
        ("/setting/roles", "List roles"),
        ("/setting/alert/chains", "List escalation chains"),
        ("/setting/integrations", "List integrations"),
        ("/report/reports", "List reports"),
        ("/report/groups", "List report groups"),
        ("/website/websites", "List websites (synthetic)"),
    ]

    from rich.table import Table

    table = Table(title="Common API Endpoints")
    table.add_column("Endpoint", style="cyan")
    table.add_column("Description")

    for endpoint, desc in endpoints:
        table.add_row(endpoint, desc)

    console.print(table)
    console.print("\n[dim]Usage: lmn api get <endpoint> [--filter FILTER][/dim]")
