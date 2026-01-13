"""
Report management commands.

Provides commands for listing and viewing LogicMonitor reports.
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import get_settings
from lmn_tools.services.base import BaseService

app = typer.Typer(help="View reports")
console = Console()


class ReportService(BaseService):
    """Service for viewing LogicMonitor reports."""

    @property
    def base_path(self) -> str:
        return "/report/reports"


def _get_client() -> LMClient:
    """Get authenticated API client."""
    settings = get_settings()
    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        raise typer.Exit(1) from None
    return LMClient.from_credentials(settings.credentials)  # type: ignore


def _get_service() -> ReportService:
    """Get report service."""
    return ReportService(_get_client())


@app.command("list")
def list_reports(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    type: Annotated[str | None, typer.Option("--type", "-t", help="Filter by report type")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List reports."""
    svc = _get_service()

    filters = []
    if filter:
        filters.append(filter)
    if type:
        filters.append(f"type:{type}")
    filter_str = ",".join(filters) if filters else None

    reports = svc.list(filter=filter_str, max_items=limit)

    if format == "json":
        console.print_json(data=reports)
    elif format == "ids":
        for r in reports:
            console.print(r["id"])
    else:
        table = Table(title=f"Reports ({len(reports)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Group ID")
        table.add_column("Format")

        for r in reports:
            table.add_row(
                str(r["id"]),
                r.get("name", ""),
                r.get("type", ""),
                str(r.get("groupId", "")),
                r.get("format", ""),
            )
        console.print(table)


@app.command("get")
def get_report(
    report_id: Annotated[int, typer.Argument(help="Report ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get report details."""
    svc = _get_service()
    response = svc.get(report_id)
    report = response.get("data", response) if "data" in response else response

    if format == "json":
        console.print_json(data=report)
        return

    console.print(f"\n[bold cyan]{report.get('name', 'N/A')}[/bold cyan] (ID: {report_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Type", report.get("type", "N/A"))
    detail_table.add_row("Format", report.get("format", "N/A"))
    detail_table.add_row("Group ID", str(report.get("groupId", "N/A")))
    detail_table.add_row("Description", report.get("description", "N/A") or "N/A")
    detail_table.add_row("Delivery", report.get("delivery", "N/A"))
    detail_table.add_row("Schedule", report.get("schedule", "N/A"))

    console.print(detail_table)


@app.command("groups")
def list_report_groups(
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List report groups."""
    client = _get_client()
    response = client.get("/report/groups")
    groups = response.get("items", response.get("data", {}).get("items", []))

    if format == "json":
        console.print_json(data=groups)
        return

    if not groups:
        console.print("[dim]No report groups found[/dim]")
        return

    table = Table(title=f"Report Groups ({len(groups)})")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for g in groups:
        table.add_row(
            str(g.get("id", "")),
            g.get("name", ""),
            g.get("description", "") or "",
        )
    console.print(table)
