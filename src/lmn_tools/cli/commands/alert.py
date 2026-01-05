"""
Alert management commands.

Provides commands for viewing and managing LogicMonitor alerts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import get_settings
from lmn_tools.services.alerts import AlertService

app = typer.Typer(help="Manage alerts")
console = Console()


def _get_client() -> LMClient:
    """Get authenticated API client."""
    settings = get_settings()
    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        raise typer.Exit(1)
    return LMClient.from_credentials(settings.credentials)  # type: ignore


def _get_service() -> AlertService:
    """Get alert service."""
    return AlertService(_get_client())


def _format_timestamp(ts: int | None) -> str:
    """Format millisecond timestamp to readable string."""
    if not ts:
        return "N/A"
    try:
        return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)


# Map integer severity to string (LM API returns integers)
SEVERITY_INT_MAP = {
    2: "warning",
    3: "error",
    4: "critical",
}


def _severity_name(severity: str | int) -> str:
    """Convert severity to display name."""
    if isinstance(severity, int):
        return SEVERITY_INT_MAP.get(severity, str(severity))
    return str(severity) if severity else ""


def _severity_style(severity: str | int) -> str:
    """Get Rich style for severity."""
    name = _severity_name(severity).lower()
    styles = {
        "critical": "red bold",
        "error": "red",
        "warning": "yellow",
    }
    return styles.get(name, "white")


@app.command("list")
def list_alerts(
    filter: Annotated[Optional[str], typer.Option("--filter", "-f", help="LM filter string")] = None,
    severity: Annotated[Optional[str], typer.Option("--severity", "-s", help="Filter by severity")] = None,
    acked: Annotated[Optional[bool], typer.Option("--acked", help="Filter by acked status")] = None,
    cleared: Annotated[bool, typer.Option("--cleared", help="Include cleared alerts")] = False,
    device: Annotated[Optional[int], typer.Option("--device", "-d", help="Filter by device ID")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List alerts with optional filtering."""
    svc = _get_service()

    filters = []
    if filter:
        filters.append(filter)
    if severity:
        filters.append(f"severity:{severity}")
    if acked is not None:
        filters.append(f"acked:{str(acked).lower()}")
    if not cleared:
        filters.append("cleared:false")
    if device:
        filters.append(f"monitorObjectId:{device}")

    filter_str = ",".join(filters) if filters else None
    alerts = svc.list(filter=filter_str, max_items=limit)

    if format == "json":
        console.print_json(data=alerts)
    elif format == "ids":
        for a in alerts:
            console.print(a["id"])
    else:
        if not alerts:
            console.print("[green]No alerts found[/green]")
            return

        table = Table(title=f"Alerts ({len(alerts)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Severity")
        table.add_column("Device", style="cyan")
        table.add_column("DataSource")
        table.add_column("Message")
        table.add_column("Start")
        table.add_column("Acked")

        for a in alerts:
            sev = a.get("severity", "")
            sev_name = _severity_name(sev)
            severity_styled = f"[{_severity_style(sev)}]{sev_name}[/{_severity_style(sev)}]"
            acked_status = "[green]Yes[/green]" if a.get("acked") else "[dim]No[/dim]"
            msg = a.get("alertValue", "") or a.get("instanceName", "")
            if len(msg) > 30:
                msg = msg[:30] + "..."

            table.add_row(
                str(a.get("id", "")),
                severity_styled,
                a.get("monitorObjectName", ""),
                a.get("dataSourceName", ""),
                msg,
                _format_timestamp(a.get("startEpoch")),
                acked_status,
            )
        console.print(table)


@app.command("active")
def list_active_alerts(
    severity: Annotated[Optional[str], typer.Option("--severity", "-s", help="Filter by severity")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List active (uncleared, unacked) alerts."""
    svc = _get_service()
    alerts = svc.list_active(severity=severity, max_items=limit)

    if format == "json":
        console.print_json(data=alerts)
        return

    if not alerts:
        console.print("[green]No active alerts[/green]")
        return

    table = Table(title=f"Active Alerts ({len(alerts)})")
    table.add_column("Severity")
    table.add_column("Device", style="cyan")
    table.add_column("DataSource")
    table.add_column("Instance")
    table.add_column("Duration")

    for a in alerts:
        sev = a.get("severity", "")
        sev_name = _severity_name(sev)
        severity_styled = f"[{_severity_style(sev)}]{sev_name}[/{_severity_style(sev)}]"

        # Calculate duration
        start = a.get("startEpoch", 0)
        if start:
            duration_mins = int((datetime.now().timestamp() * 1000 - start) / 60000)
            if duration_mins < 60:
                duration = f"{duration_mins}m"
            elif duration_mins < 1440:
                duration = f"{duration_mins // 60}h {duration_mins % 60}m"
            else:
                duration = f"{duration_mins // 1440}d {(duration_mins % 1440) // 60}h"
        else:
            duration = "N/A"

        table.add_row(
            severity_styled,
            a.get("monitorObjectName", ""),
            a.get("dataSourceName", ""),
            a.get("instanceName", ""),
            duration,
        )
    console.print(table)


@app.command("critical")
def list_critical_alerts(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List critical severity alerts."""
    svc = _get_service()
    alerts = svc.list_critical(max_items=limit)

    if format == "json":
        console.print_json(data=alerts)
        return

    if not alerts:
        console.print("[green]No critical alerts[/green]")
        return

    table = Table(title=f"[red bold]Critical Alerts ({len(alerts)})[/red bold]")
    table.add_column("ID", style="dim")
    table.add_column("Device", style="cyan")
    table.add_column("DataSource")
    table.add_column("Instance")
    table.add_column("Start")

    for a in alerts:
        table.add_row(
            str(a.get("id", "")),
            a.get("monitorObjectName", ""),
            a.get("dataSourceName", ""),
            a.get("instanceName", ""),
            _format_timestamp(a.get("startEpoch")),
        )
    console.print(table)


@app.command("get")
def get_alert(
    alert_id: Annotated[str, typer.Argument(help="Alert ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get alert details."""
    svc = _get_service()
    response = svc.get(alert_id)
    alert = response.get("data", response) if "data" in response else response

    if format == "json":
        console.print_json(data=alert)
        return

    sev = alert.get("severity", "")
    sev_name = _severity_name(sev)
    console.print(f"\n[{_severity_style(sev)}]Alert: {alert_id}[/{_severity_style(sev)}]")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Severity", f"[{_severity_style(sev)}]{sev_name}[/{_severity_style(sev)}]")
    detail_table.add_row("Device", alert.get("monitorObjectName", "N/A"))
    detail_table.add_row("Device ID", str(alert.get("monitorObjectId", "N/A")))
    detail_table.add_row("DataSource", alert.get("dataSourceName", "N/A"))
    detail_table.add_row("Instance", alert.get("instanceName", "N/A"))
    detail_table.add_row("Datapoint", alert.get("dataPointName", "N/A"))
    detail_table.add_row("Alert Value", str(alert.get("alertValue", "N/A")))
    detail_table.add_row("Threshold", alert.get("threshold", "N/A"))
    detail_table.add_row("Start", _format_timestamp(alert.get("startEpoch")))
    detail_table.add_row("End", _format_timestamp(alert.get("endEpoch")))
    detail_table.add_row("Acknowledged", "Yes" if alert.get("acked") else "No")
    detail_table.add_row("Cleared", "Yes" if alert.get("cleared") else "No")

    console.print(detail_table)


@app.command("ack")
def acknowledge_alert(
    alert_id: Annotated[str, typer.Argument(help="Alert ID to acknowledge")],
    comment: Annotated[str, typer.Option("--comment", "-c", help="Acknowledgement comment")] = "",
) -> None:
    """Acknowledge an alert."""
    svc = _get_service()

    try:
        svc.acknowledge(alert_id, comment)
        console.print(f"[green]Alert {alert_id} acknowledged[/green]")
    except Exception as e:
        console.print(f"[red]Failed to acknowledge alert: {e}[/red]")
        raise typer.Exit(1)


@app.command("summary")
def alert_summary() -> None:
    """Show alert summary by severity."""
    svc = _get_service()

    console.print("\n[bold]Alert Summary[/bold]")

    # Count by severity
    critical = len(svc.list_critical())
    errors = len(svc.list_active(severity="error"))
    warnings = len(svc.list_active(severity="warning"))
    acked = len(svc.list_acknowledged())

    table = Table(show_header=False, box=None)
    table.add_column("Category", style="dim")
    table.add_column("Count", justify="right")

    table.add_row("[red bold]Critical[/red bold]", f"[red bold]{critical}[/red bold]")
    table.add_row("[red]Error[/red]", f"[red]{errors}[/red]")
    table.add_row("[yellow]Warning[/yellow]", f"[yellow]{warnings}[/yellow]")
    table.add_row("Acknowledged", str(acked))
    table.add_row("[bold]Total Active[/bold]", f"[bold]{critical + errors + warnings}[/bold]")

    console.print(table)
