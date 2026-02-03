"""
Alert management commands.

Provides commands for viewing and managing LogicMonitor alerts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import get_client
from lmn_tools.services.alerts import AlertService, AlertSeverity

app = typer.Typer(help="Manage alerts")
console = Console()


def _get_service() -> AlertService:
    """Get alert service."""
    return AlertService(get_client(console))


def _format_timestamp(ts: int | None) -> str:
    """Format epoch timestamp to readable string (handles both seconds and milliseconds)."""
    if not ts:
        return "N/A"
    try:
        # Timestamps >= 10^12 are in milliseconds, < 10^12 are in seconds
        ts_secs: float = ts / 1000 if ts >= 1e12 else float(ts)
        return datetime.fromtimestamp(ts_secs).strftime("%Y-%m-%d %H:%M")
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
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    severity: Annotated[
        str | None, typer.Option("--severity", "-s", help="Filter by severity")
    ] = None,
    acked: Annotated[bool | None, typer.Option("--acked", help="Filter by acked status")] = None,
    cleared: Annotated[bool, typer.Option("--cleared", help="Include cleared alerts")] = False,
    device: Annotated[
        int | None, typer.Option("--device", "-d", help="Filter by device ID")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, ids")
    ] = "table",
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
    severity: Annotated[
        str | None, typer.Option("--severity", "-s", help="Filter by severity")
    ] = None,
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
            # Convert to seconds if in milliseconds
            start_secs = start / 1000 if start >= 1e12 else start
            duration_mins = int((datetime.now().timestamp() - start_secs) / 60)
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
        raise typer.Exit(1) from None


@app.command("summary")
def alert_summary() -> None:
    """Show alert summary by severity."""
    svc = _get_service()

    console.print("\n[bold]Alert Summary[/bold]")

    # Count by severity
    critical = len(svc.list_critical())
    errors = len(svc.list_active(severity=AlertSeverity.ERROR))
    warnings = len(svc.list_active(severity=AlertSeverity.WARNING))
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


@app.command("history")
def alert_history(
    device: Annotated[
        int | None, typer.Option("--device", "-d", help="Filter by device ID")
    ] = None,
    group: Annotated[int | None, typer.Option("--group", "-g", help="Filter by group ID")] = None,
    severity: Annotated[
        str | None, typer.Option("--severity", "-s", help="Filter by severity")
    ] = None,
    days: Annotated[int, typer.Option("--days", help="Number of days to look back")] = 7,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 100,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List historical alerts (including cleared)."""
    import time

    svc = _get_service()

    now = int(time.time() * 1000)
    start_time = now - (days * 24 * 60 * 60 * 1000)

    alerts = svc.list_history(
        device_id=device,
        group_id=group,
        severity=severity,
        start_time=start_time,
        max_items=limit,
    )

    if format == "json":
        console.print_json(data=alerts)
        return

    if not alerts:
        console.print(f"[dim]No alerts in last {days} days[/dim]")
        return

    table = Table(title=f"Alert History (last {days} days, {len(alerts)} alerts)")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Severity")
    table.add_column("Device", style="cyan")
    table.add_column("DataSource")
    table.add_column("Start")
    table.add_column("Cleared")

    for a in alerts:
        sev = a.get("severity", "")
        sev_name = _severity_name(sev)
        severity_styled = f"[{_severity_style(sev)}]{sev_name}[/{_severity_style(sev)}]"
        cleared = "[green]Yes[/green]" if a.get("cleared") else "[dim]No[/dim]"

        table.add_row(
            str(a.get("id", "")),
            severity_styled,
            a.get("monitorObjectName", ""),
            a.get("dataSourceName", ""),
            _format_timestamp(a.get("startEpoch")),
            cleared,
        )
    console.print(table)


@app.command("trends")
def alert_trends(
    period: Annotated[str, typer.Option("--period", "-p", help="Time period: 7d, 30d, 90d")] = "7d",
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Show alert trends over time."""
    svc = _get_service()

    # Parse period
    period_days = 7
    if period.endswith("d"):
        try:
            period_days = int(period[:-1])
        except ValueError:
            console.print("[red]Invalid period format. Use: 7d, 30d, 90d[/red]")
            raise typer.Exit(1) from None

    trends = svc.get_trends(days=period_days)

    if format == "json":
        console.print_json(data=trends)
        return

    console.print(f"\n[bold]Alert Trends (last {period_days} days)[/bold]")
    console.print(f"\nTotal Alerts: {trends['total_alerts']}")

    # By severity
    console.print("\n[bold]By Severity:[/bold]")
    severity_table = Table(show_header=False, box=None)
    severity_table.add_column("Severity", style="dim")
    severity_table.add_column("Count", justify="right")

    severity_map = {2: "warning", 3: "error", 4: "critical"}
    for sev, count in trends["by_severity"].items():
        sev_name = severity_map.get(int(sev), str(sev)) if sev.isdigit() else sev
        severity_table.add_row(sev_name, str(count))
    console.print(severity_table)

    # Top devices
    if trends["by_device"]:
        console.print("\n[bold]Top Devices:[/bold]")
        for device, count in list(trends["by_device"].items())[:10]:
            console.print(f"  {device}: {count}")

    # Top datasources
    if trends["by_datasource"]:
        console.print("\n[bold]Top DataSources:[/bold]")
        for ds, count in list(trends["by_datasource"].items())[:10]:
            console.print(f"  {ds}: {count}")

    # Daily breakdown
    if trends["by_day"]:
        console.print("\n[bold]Daily Breakdown:[/bold]")
        for day, count in list(trends["by_day"].items())[-7:]:
            console.print(f"  {day}: {count}")
