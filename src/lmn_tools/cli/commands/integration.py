"""
Integration management commands.

Provides commands for managing LogicMonitor integrations (PagerDuty, Slack, etc).
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import get_settings
from lmn_tools.services.alerts import IntegrationService

app = typer.Typer(help="Manage integrations")
console = Console()


def _get_client() -> LMClient:
    """Get authenticated API client."""
    settings = get_settings()
    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        raise typer.Exit(1)
    return LMClient.from_credentials(settings.credentials)  # type: ignore


def _get_service() -> IntegrationService:
    """Get integration service."""
    return IntegrationService(_get_client())


@app.command("list")
def list_integrations(
    filter: Annotated[Optional[str], typer.Option("--filter", "-f", help="LM filter string")] = None,
    type: Annotated[Optional[str], typer.Option("--type", "-t", help="Filter by integration type")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List integrations."""
    svc = _get_service()

    filters = []
    if filter:
        filters.append(filter)
    if type:
        filters.append(f"type:{type}")
    filter_str = ",".join(filters) if filters else None

    integrations = svc.list(filter=filter_str, max_items=limit)

    if format == "json":
        console.print_json(data=integrations)
    elif format == "ids":
        for i in integrations:
            console.print(i["id"])
    else:
        if not integrations:
            console.print("[dim]No integrations found[/dim]")
            return

        table = Table(title=f"Integrations ({len(integrations)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Description")

        for i in integrations:
            table.add_row(
                str(i["id"]),
                i.get("name", ""),
                i.get("type", ""),
                (i.get("description", "") or "")[:40],
            )
        console.print(table)


@app.command("get")
def get_integration(
    identifier: Annotated[str, typer.Argument(help="Integration ID or name")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get integration details."""
    svc = _get_service()

    # Try as ID first, then search by name
    try:
        integration_id = int(identifier)
        response = svc.get(integration_id)
        integration = response.get("data", response) if "data" in response else response
    except ValueError:
        integrations = svc.list(filter=f"name:{identifier}")
        if not integrations:
            console.print(f"[red]Integration not found: {identifier}[/red]")
            raise typer.Exit(1)
        integration = integrations[0]
        integration_id = integration["id"]

    if format == "json":
        console.print_json(data=integration)
        return

    console.print(f"\n[bold cyan]{integration.get('name', 'N/A')}[/bold cyan] (ID: {integration_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Type", integration.get("type", "N/A"))
    detail_table.add_row("Description", integration.get("description", "N/A") or "N/A")

    # Type-specific fields
    extra_info = integration.get("extra", {}) or {}
    # Parse JSON string if needed
    if isinstance(extra_info, str):
        try:
            extra_info = json.loads(extra_info)
        except json.JSONDecodeError:
            extra_info = {}
    if extra_info and isinstance(extra_info, dict):
        detail_table.add_row("", "")  # Separator
        detail_table.add_row("[bold]Configuration:[/bold]", "")
        for key, value in extra_info.items():
            # Mask sensitive values
            if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower():
                value = "***" if value else "N/A"
            detail_table.add_row(f"  {key}", str(value)[:60])

    console.print(detail_table)


@app.command("search")
def search_integrations(
    query: Annotated[str, typer.Argument(help="Search query")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 20,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Search integrations by name."""
    svc = _get_service()
    integrations = svc.list(filter=f'name~"{query}"', max_items=limit)

    if format == "json":
        console.print_json(data=integrations)
        return

    if not integrations:
        console.print(f"[dim]No integrations matching '{query}'[/dim]")
        return

    table = Table(title=f"Search Results ({len(integrations)})")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Type")

    for i in integrations:
        table.add_row(
            str(i["id"]),
            i.get("name", ""),
            i.get("type", ""),
        )
    console.print(table)


@app.command("types")
def list_integration_types() -> None:
    """Show available integration types."""
    types = [
        ("pagerduty", "PagerDuty incident management"),
        ("slack", "Slack messaging"),
        ("msteams", "Microsoft Teams"),
        ("email", "Email notifications"),
        ("http", "Custom HTTP/webhook"),
        ("servicenow", "ServiceNow ITSM"),
        ("jira", "Atlassian Jira"),
        ("autotask", "Datto Autotask"),
        ("connectwise", "ConnectWise Manage"),
        ("victorops", "Splunk On-Call (VictorOps)"),
        ("opsgenie", "Atlassian Opsgenie"),
    ]

    table = Table(title="Integration Types")
    table.add_column("Type", style="cyan")
    table.add_column("Description")

    for type_name, desc in types:
        table.add_row(type_name, desc)

    console.print(table)
    console.print("\n[dim]Use --type filter with lmn integration list[/dim]")


# ============================================================================
# Write Operations (CRUD)
# ============================================================================


@app.command("create")
def create_integration(
    name: Annotated[str, typer.Argument(help="Integration name")],
    type: Annotated[str, typer.Option("--type", "-t", help="Integration type")],
    description: Annotated[Optional[str], typer.Option("--description", "-d", help="Description")] = None,
    extra: Annotated[Optional[str], typer.Option("--extra", "-e", help="Extra config as JSON")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new integration."""
    svc = _get_service()

    integration_data: dict = {
        "name": name,
        "type": type,
    }

    if description:
        integration_data["description"] = description

    if extra:
        try:
            integration_data["extra"] = json.loads(extra)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON for extra config: {e}[/red]")
            raise typer.Exit(1)

    try:
        response = svc.create(integration_data)
        result = response.get("data", response) if "data" in response else response
        integration_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created integration '{name}' (ID: {integration_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create integration: {e}[/red]")
        raise typer.Exit(1)


@app.command("update")
def update_integration(
    integration_id: Annotated[int, typer.Argument(help="Integration ID")],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="New name")] = None,
    description: Annotated[Optional[str], typer.Option("--description", "-d", help="New description")] = None,
    extra: Annotated[Optional[str], typer.Option("--extra", "-e", help="Extra config as JSON")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update an integration."""
    svc = _get_service()

    update_data: dict = {}

    if name:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if extra:
        try:
            update_data["extra"] = json.loads(extra)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON for extra config: {e}[/red]")
            raise typer.Exit(1)

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0)

    try:
        response = svc.update(integration_id, update_data)
        result = response.get("data", response) if "data" in response else response

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated integration {integration_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update integration: {e}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_integration(
    integration_id: Annotated[int, typer.Argument(help="Integration ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete an integration."""
    svc = _get_service()

    # Get integration info first
    try:
        response = svc.get(integration_id)
        integration = response.get("data", response) if "data" in response else response
        integration_name = integration.get("name", f"ID:{integration_id}")
    except Exception:
        integration_name = f"ID:{integration_id}"

    if not force:
        confirm = typer.confirm(f"Delete integration '{integration_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    try:
        svc.delete(integration_id)
        console.print(f"[green]Deleted integration '{integration_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete integration: {e}[/red]")
        raise typer.Exit(1)


@app.command("test")
def test_integration(
    integration_id: Annotated[int, typer.Argument(help="Integration ID to test")],
) -> None:
    """Test an integration (send test notification)."""
    client = _get_client()

    try:
        # LogicMonitor API test endpoint
        response = client.post(
            f"/setting/integrations/{integration_id}/test",
            json_data={},
        )

        result = response.get("data", response) if "data" in response else response
        console.print(f"[green]Test notification sent for integration {integration_id}[/green]")

        if result:
            console.print_json(data=result)
    except Exception as e:
        console.print(f"[red]Failed to test integration: {e}[/red]")
        raise typer.Exit(1)
