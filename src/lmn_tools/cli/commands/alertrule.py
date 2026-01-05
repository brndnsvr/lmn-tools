"""
Alert rule management commands.

Provides commands for managing LogicMonitor alert threshold rules.
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import get_settings
from lmn_tools.services.alerts import AlertRuleService

app = typer.Typer(help="Manage alert rules")
console = Console()


def _get_client() -> LMClient:
    """Get authenticated API client."""
    settings = get_settings()
    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        raise typer.Exit(1)
    return LMClient.from_credentials(settings.credentials)  # type: ignore


def _get_service() -> AlertRuleService:
    """Get alert rule service."""
    return AlertRuleService(_get_client())


@app.command("list")
def list_alertrules(
    filter: Annotated[Optional[str], typer.Option("--filter", "-f", help="LM filter string")] = None,
    datasource: Annotated[Optional[int], typer.Option("--datasource", "-d", help="Filter by DataSource ID")] = None,
    severity: Annotated[Optional[str], typer.Option("--severity", "-s", help="Filter by severity (warning, error, critical)")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List alert rules with optional filtering."""
    svc = _get_service()

    # Use specialized methods if applicable
    if datasource and not filter and not severity:
        rules = svc.list_by_datasource(datasource)
    elif severity and not filter and not datasource:
        rules = svc.list_by_severity(severity)
    else:
        # Build filter
        filters = []
        if filter:
            filters.append(filter)
        if datasource:
            filters.append(f"dataSourceId:{datasource}")
        if severity:
            filters.append(f"levelStr:{severity}")
        filter_str = ",".join(filters) if filters else None
        rules = svc.list(filter=filter_str, max_items=limit)

    # Apply limit
    rules = rules[:limit]

    if format == "json":
        console.print_json(data=rules)
    elif format == "ids":
        for rule in rules:
            console.print(rule["id"])
    else:
        table = Table(title=f"Alert Rules ({len(rules)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("DataSource")
        table.add_column("Datapoint")
        table.add_column("Severity")
        table.add_column("Enabled", justify="center")

        for rule in rules:
            enabled = "[green]Yes[/green]" if not rule.get("disableAlerting", False) else "[dim]No[/dim]"
            table.add_row(
                str(rule["id"]),
                rule.get("name", ""),
                rule.get("dataSourceName", str(rule.get("dataSourceId", ""))),
                rule.get("dataPointName", ""),
                rule.get("levelStr", ""),
                enabled,
            )
        console.print(table)


@app.command("get")
def get_alertrule(
    rule_id: Annotated[int, typer.Argument(help="Alert rule ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get alert rule details."""
    svc = _get_service()

    try:
        response = svc.get(rule_id)
        rule = response.get("data", response) if "data" in response else response
    except Exception as e:
        console.print(f"[red]Alert rule not found: {rule_id}[/red]")
        raise typer.Exit(1)

    if format == "json":
        console.print_json(data=rule)
        return

    console.print(f"\n[bold cyan]{rule.get('name', 'N/A')}[/bold cyan] (ID: {rule_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("DataSource", rule.get("dataSourceName", str(rule.get("dataSourceId", "N/A"))))
    detail_table.add_row("Datapoint", rule.get("dataPointName", "N/A"))
    detail_table.add_row("Severity", rule.get("levelStr", "N/A"))
    detail_table.add_row("Threshold", rule.get("alertExpr", "N/A"))
    enabled = "Yes" if not rule.get("disableAlerting", False) else "No"
    detail_table.add_row("Enabled", enabled)
    detail_table.add_row("Escalation Chain", rule.get("escalatingChainName", "N/A"))

    console.print(detail_table)


@app.command("search")
def search_alertrules(
    query: Annotated[str, typer.Argument(help="Search term")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 25,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """Search alert rules by name."""
    svc = _get_service()
    results = svc.list(filter=f'name~"{query}"', max_items=limit)

    if format == "json":
        console.print_json(data=results)
    elif format == "ids":
        for rule in results:
            console.print(rule["id"])
    else:
        if not results:
            console.print(f"[dim]No alert rules matching '{query}'[/dim]")
            return

        table = Table(title=f"Search Results for '{query}' ({len(results)})")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("DataSource")
        table.add_column("Severity")

        for rule in results[:limit]:
            table.add_row(
                str(rule["id"]),
                rule.get("name", ""),
                rule.get("dataSourceName", ""),
                rule.get("levelStr", ""),
            )
        console.print(table)


@app.command("create")
def create_alertrule(
    name: Annotated[str, typer.Option("--name", "-n", help="Alert rule name")],
    datasource_id: Annotated[int, typer.Option("--datasource", "-d", help="DataSource ID")],
    datapoint: Annotated[str, typer.Option("--datapoint", "-p", help="Datapoint name")],
    threshold: Annotated[str, typer.Option("--threshold", "-t", help="Alert threshold expression (e.g., '> 90')")],
    severity: Annotated[str, typer.Option("--severity", "-s", help="Severity level: warning, error, critical")] = "error",
    escalation_chain: Annotated[Optional[int], typer.Option("--chain", "-c", help="Escalation chain ID")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new alert rule."""
    svc = _get_service()

    # Map severity to level number
    severity_map = {"warning": 2, "error": 3, "critical": 4}
    level = severity_map.get(severity.lower(), 3)

    rule_data = {
        "name": name,
        "dataSourceId": datasource_id,
        "dataPointName": datapoint,
        "alertExpr": threshold,
        "level": level,
        "levelStr": severity.lower(),
    }

    if escalation_chain:
        rule_data["escalatingChainId"] = escalation_chain

    try:
        response = svc.create(rule_data)
        result = response.get("data", response) if "data" in response else response
        rule_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created alert rule '{name}' (ID: {rule_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create alert rule: {e}[/red]")
        raise typer.Exit(1)


@app.command("update")
def update_alertrule(
    rule_id: Annotated[int, typer.Argument(help="Alert rule ID")],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="New name")] = None,
    threshold: Annotated[Optional[str], typer.Option("--threshold", "-t", help="New threshold expression")] = None,
    severity: Annotated[Optional[str], typer.Option("--severity", "-s", help="New severity level")] = None,
    escalation_chain: Annotated[Optional[int], typer.Option("--chain", "-c", help="Escalation chain ID")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update an alert rule."""
    svc = _get_service()

    update_data: dict = {}

    if name is not None:
        update_data["name"] = name
    if threshold is not None:
        update_data["alertExpr"] = threshold
    if severity is not None:
        severity_map = {"warning": 2, "error": 3, "critical": 4}
        update_data["level"] = severity_map.get(severity.lower(), 3)
        update_data["levelStr"] = severity.lower()
    if escalation_chain is not None:
        update_data["escalatingChainId"] = escalation_chain

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0)

    try:
        response = svc.update(rule_id, update_data)
        result = response.get("data", response) if "data" in response else response

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated alert rule {rule_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update alert rule: {e}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_alertrule(
    rule_id: Annotated[int, typer.Argument(help="Alert rule ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete an alert rule."""
    svc = _get_service()

    # Get rule info first
    try:
        response = svc.get(rule_id)
        rule = response.get("data", response) if "data" in response else response
        rule_name = rule.get("name", f"ID:{rule_id}")
    except Exception:
        rule_name = f"ID:{rule_id}"

    if not force:
        confirm = typer.confirm(f"Delete alert rule '{rule_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    try:
        svc.delete(rule_id)
        console.print(f"[green]Deleted alert rule '{rule_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete alert rule: {e}[/red]")
        raise typer.Exit(1)


@app.command("enable")
def enable_alertrule(
    rule_id: Annotated[int, typer.Argument(help="Alert rule ID")],
) -> None:
    """Enable an alert rule."""
    svc = _get_service()

    try:
        svc.enable(rule_id)
        console.print(f"[green]Enabled alert rule {rule_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to enable alert rule: {e}[/red]")
        raise typer.Exit(1)


@app.command("disable")
def disable_alertrule(
    rule_id: Annotated[int, typer.Argument(help="Alert rule ID")],
) -> None:
    """Disable an alert rule."""
    svc = _get_service()

    try:
        svc.disable(rule_id)
        console.print(f"[yellow]Disabled alert rule {rule_id}[/yellow]")
    except Exception as e:
        console.print(f"[red]Failed to disable alert rule: {e}[/red]")
        raise typer.Exit(1)
