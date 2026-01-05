"""
Escalation chain management commands.

Provides commands for managing LogicMonitor escalation chains.
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import get_settings
from lmn_tools.services.alerts import EscalationChainService

app = typer.Typer(help="Manage escalation chains")
console = Console()


def _get_client() -> LMClient:
    """Get authenticated API client."""
    settings = get_settings()
    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        raise typer.Exit(1)
    return LMClient.from_credentials(settings.credentials)  # type: ignore


def _get_service() -> EscalationChainService:
    """Get escalation chain service."""
    return EscalationChainService(_get_client())


@app.command("list")
def list_chains(
    filter: Annotated[Optional[str], typer.Option("--filter", "-f", help="LM filter string")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List escalation chains."""
    svc = _get_service()
    chains = svc.list(filter=filter, max_items=limit)

    if format == "json":
        console.print_json(data=chains)
    elif format == "ids":
        for c in chains:
            console.print(c["id"])
    else:
        if not chains:
            console.print("[dim]No escalation chains found[/dim]")
            return

        table = Table(title=f"Escalation Chains ({len(chains)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        table.add_column("Destinations", justify="right")
        table.add_column("In Alerting")

        for c in chains:
            # Count destinations across all stages
            destinations = 0
            for dest_list in c.get("destinations", {}).values():
                if isinstance(dest_list, list):
                    destinations += len(dest_list)

            in_alerting = "[green]Yes[/green]" if c.get("inAlerting", False) else "[dim]No[/dim]"

            table.add_row(
                str(c["id"]),
                c.get("name", ""),
                (c.get("description", "") or "")[:40],
                str(destinations),
                in_alerting,
            )
        console.print(table)


@app.command("get")
def get_chain(
    identifier: Annotated[str, typer.Argument(help="Chain ID or name")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get escalation chain details."""
    svc = _get_service()

    # Try as ID first, then search by name
    try:
        chain_id = int(identifier)
        response = svc.get(chain_id)
        chain = response.get("data", response) if "data" in response else response
    except ValueError:
        chains = svc.list(filter=f"name:{identifier}")
        if not chains:
            console.print(f"[red]Escalation chain not found: {identifier}[/red]")
            raise typer.Exit(1)
        chain = chains[0]
        chain_id = chain["id"]

    if format == "json":
        console.print_json(data=chain)
        return

    console.print(f"\n[bold cyan]{chain.get('name', 'N/A')}[/bold cyan] (ID: {chain_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Description", chain.get("description", "N/A") or "N/A")
    detail_table.add_row("In Alerting", str(chain.get("inAlerting", False)))
    detail_table.add_row("Throttle Period", f"{chain.get('throttlingPeriod', 0)} minutes")
    detail_table.add_row("Throttle Alerts", str(chain.get('throttlingAlerts', 0)))

    console.print(detail_table)

    # Show destinations by stage
    destinations = chain.get("destinations", {})
    if destinations:
        console.print("\n[bold]Destinations by Stage:[/bold]")
        for stage, dests in sorted(destinations.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
            if isinstance(dests, list) and dests:
                console.print(f"\n  [cyan]Stage {stage}:[/cyan]")
                for dest in dests:
                    dest_type = dest.get("type", "unknown")
                    method = dest.get("method", "")
                    addr = dest.get("addr", dest.get("contact", ""))
                    console.print(f"    • {dest_type}: {method} → {addr}")


@app.command("search")
def search_chains(
    query: Annotated[str, typer.Argument(help="Search query")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 20,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Search escalation chains by name."""
    svc = _get_service()
    chains = svc.list(filter=f"name~*{query}*", max_items=limit)

    if format == "json":
        console.print_json(data=chains)
        return

    if not chains:
        console.print(f"[dim]No escalation chains matching '{query}'[/dim]")
        return

    table = Table(title=f"Search Results ({len(chains)})")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for c in chains:
        table.add_row(
            str(c["id"]),
            c.get("name", ""),
            (c.get("description", "") or "")[:50],
        )
    console.print(table)


# ============================================================================
# Write Operations (CRUD)
# ============================================================================


@app.command("create")
def create_chain(
    name: Annotated[str, typer.Argument(help="Chain name")],
    description: Annotated[Optional[str], typer.Option("--description", "-d", help="Chain description")] = None,
    destinations: Annotated[Optional[str], typer.Option("--destinations", help="Destinations as JSON")] = None,
    throttling_period: Annotated[int, typer.Option("--throttle-period", help="Throttling period in minutes")] = 0,
    throttling_alerts: Annotated[int, typer.Option("--throttle-alerts", help="Number of throttled alerts")] = 0,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new escalation chain."""
    svc = _get_service()

    chain_data: dict = {
        "name": name,
    }

    if description:
        chain_data["description"] = description

    if destinations:
        try:
            chain_data["destinations"] = json.loads(destinations)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON for destinations: {e}[/red]")
            raise typer.Exit(1)

    if throttling_period:
        chain_data["throttlingPeriod"] = throttling_period
        chain_data["throttlingAlerts"] = throttling_alerts

    try:
        response = svc.create(chain_data)
        result = response.get("data", response) if "data" in response else response
        chain_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created escalation chain '{name}' (ID: {chain_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create escalation chain: {e}[/red]")
        raise typer.Exit(1)


@app.command("update")
def update_chain(
    chain_id: Annotated[int, typer.Argument(help="Chain ID")],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="New chain name")] = None,
    description: Annotated[Optional[str], typer.Option("--description", "-d", help="New description")] = None,
    destinations: Annotated[Optional[str], typer.Option("--destinations", help="Destinations as JSON")] = None,
    throttling_period: Annotated[Optional[int], typer.Option("--throttle-period", help="Throttling period")] = None,
    throttling_alerts: Annotated[Optional[int], typer.Option("--throttle-alerts", help="Throttled alerts")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update an escalation chain."""
    svc = _get_service()

    update_data: dict = {}

    if name:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if destinations:
        try:
            update_data["destinations"] = json.loads(destinations)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON for destinations: {e}[/red]")
            raise typer.Exit(1)
    if throttling_period is not None:
        update_data["throttlingPeriod"] = throttling_period
    if throttling_alerts is not None:
        update_data["throttlingAlerts"] = throttling_alerts

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0)

    try:
        response = svc.update(chain_id, update_data)
        result = response.get("data", response) if "data" in response else response

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated escalation chain {chain_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update escalation chain: {e}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_chain(
    chain_id: Annotated[int, typer.Argument(help="Chain ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete an escalation chain."""
    svc = _get_service()

    # Get chain info first
    try:
        response = svc.get(chain_id)
        chain = response.get("data", response) if "data" in response else response
        chain_name = chain.get("name", f"ID:{chain_id}")
        in_alerting = chain.get("inAlerting", False)
    except Exception:
        chain_name = f"ID:{chain_id}"
        in_alerting = False

    if in_alerting and not force:
        console.print(f"[yellow]Warning: Chain '{chain_name}' is currently in use for alerting![/yellow]")

    if not force:
        confirm = typer.confirm(f"Delete escalation chain '{chain_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    try:
        svc.delete(chain_id)
        console.print(f"[green]Deleted escalation chain '{chain_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete escalation chain: {e}[/red]")
        raise typer.Exit(1)
