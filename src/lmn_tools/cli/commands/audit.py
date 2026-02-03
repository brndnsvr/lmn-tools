"""
Audit log management commands.

Provides commands for viewing LogicMonitor audit/access logs.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import format_timestamp, get_client, unwrap_response
from lmn_tools.services.audit import AuditLogService

app = typer.Typer(help="View audit logs")
console = Console()


def _get_service() -> AuditLogService:
    """Get audit log service."""
    return AuditLogService(get_client(console))


def _parse_time_arg(time_str: str) -> int:
    """Parse time argument to epoch milliseconds."""
    try:
        # Try parsing as ISO format
        dt = datetime.fromisoformat(time_str)
        return int(dt.timestamp() * 1000)
    except ValueError:
        pass

    # Try parsing as epoch
    try:
        ts = int(time_str)
        # If less than 1e12, assume seconds
        if ts < 1e12:
            ts = ts * 1000
        return ts
    except ValueError:
        raise typer.BadParameter(f"Invalid time format: {time_str}") from None


@app.command("list")
def list_logs(
    user: Annotated[str | None, typer.Option("--user", "-u", help="Filter by username")] = None,
    action: Annotated[str | None, typer.Option("--action", "-a", help="Filter by action")] = None,
    resource: Annotated[
        str | None, typer.Option("--resource", "-r", help="Filter by resource type")
    ] = None,
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    hours: Annotated[int | None, typer.Option("--hours", help="Filter to last N hours")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, ids")
    ] = "table",
) -> None:
    """List audit logs with optional filtering."""
    svc = _get_service()

    if user:
        logs = svc.list_by_user(user, max_items=limit)
    elif action:
        logs = svc.list_by_action(action, max_items=limit)
    elif resource:
        logs = svc.list_by_resource(resource, max_items=limit)
    elif hours:
        logs = svc.list_recent(hours=hours, max_items=limit)
    else:
        logs = svc.list(filter=filter, max_items=limit)

    if format == "json":
        console.print_json(data=logs)
    elif format == "ids":
        for log in logs:
            console.print(log.get("id", ""))
    else:
        if not logs:
            console.print("[dim]No audit logs found[/dim]")
            return

        table = Table(title=f"Audit Logs ({len(logs)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Time")
        table.add_column("User", style="cyan")
        table.add_column("IP")
        table.add_column("Description")

        for log in logs:
            desc = log.get("description", "")
            if len(desc) > 50:
                desc = desc[:50] + "..."
            table.add_row(
                str(log.get("id", "")),
                format_timestamp(log.get("happenedOn"), format="seconds"),
                log.get("username", ""),
                log.get("ip", ""),
                desc,
            )
        console.print(table)


@app.command("get")
def get_log(
    log_id: Annotated[int, typer.Argument(help="Audit log ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get audit log details."""
    svc = _get_service()
    response = svc.get(log_id)
    log = unwrap_response(response)

    if format == "json":
        console.print_json(data=log)
        return

    console.print(f"\n[bold]Audit Log {log_id}[/bold]")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Time", format_timestamp(log.get("happenedOn"), format="seconds"))
    detail_table.add_row("Username", log.get("username", "N/A"))
    detail_table.add_row("IP Address", log.get("ip", "N/A"))
    detail_table.add_row("Session ID", log.get("sessionId", "N/A") or "N/A")
    detail_table.add_row("Description", log.get("description", "N/A"))

    console.print(detail_table)


@app.command("export")
def export_logs(
    from_time: Annotated[str, typer.Option("--from", help="Start time (ISO or epoch)")],
    to_time: Annotated[str | None, typer.Option("--to", help="End time (ISO or epoch)")] = None,
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file path")] = None,
    format: Annotated[str, typer.Option("--format", help="Export format: json, csv")] = "json",
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 1000,
) -> None:
    """Export audit logs to a file."""
    svc = _get_service()

    start_ts = _parse_time_arg(from_time)
    end_ts = _parse_time_arg(to_time) if to_time else None

    logs = svc.list_by_time_range(start_ts, end_ts, max_items=limit)

    if not logs:
        console.print("[dim]No audit logs found in time range[/dim]")
        return

    if format == "csv":
        output_buffer = StringIO()
        writer = csv.DictWriter(
            output_buffer,
            fieldnames=["id", "happenedOn", "username", "ip", "sessionId", "description"],
        )
        writer.writeheader()
        for log in logs:
            writer.writerow(
                {
                    "id": log.get("id", ""),
                    "happenedOn": format_timestamp(log.get("happenedOn"), format="seconds"),
                    "username": log.get("username", ""),
                    "ip": log.get("ip", ""),
                    "sessionId": log.get("sessionId", ""),
                    "description": log.get("description", ""),
                }
            )
        output_data = output_buffer.getvalue()
    else:
        output_data = json.dumps(logs, indent=2)

    if output:
        Path(output).write_text(output_data)
        console.print(f"[green]Exported {len(logs)} logs to {output}[/green]")
    else:
        console.print(output_data)


@app.command("logins")
def list_logins(
    hours: Annotated[int, typer.Option("--hours", help="Filter to last N hours")] = 24,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List login events."""
    svc = _get_service()
    logs = svc.list_recent(hours=hours, max_items=limit)
    # Filter for login events
    login_logs = [log for log in logs if "login" in log.get("description", "").lower()]

    if format == "json":
        console.print_json(data=login_logs)
        return

    if not login_logs:
        console.print(f"[dim]No login events in last {hours} hours[/dim]")
        return

    table = Table(title=f"Login Events (last {hours}h)")
    table.add_column("Time")
    table.add_column("User", style="cyan")
    table.add_column("IP")
    table.add_column("Result")

    for log in login_logs:
        desc = log.get("description", "").lower()
        if "failed" in desc:
            result = "[red]Failed[/red]"
        elif "success" in desc or "logged in" in desc:
            result = "[green]Success[/green]"
        else:
            result = log.get("description", "")[:20]

        table.add_row(
            format_timestamp(log.get("happenedOn"), format="seconds"),
            log.get("username", ""),
            log.get("ip", ""),
            result,
        )
    console.print(table)


@app.command("recent")
def recent_logs(
    hours: Annotated[int, typer.Option("--hours", help="Hours to look back")] = 24,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List recent audit logs."""
    svc = _get_service()
    logs = svc.list_recent(hours=hours, max_items=limit)

    if format == "json":
        console.print_json(data=logs)
        return

    if not logs:
        console.print(f"[dim]No audit logs in last {hours} hours[/dim]")
        return

    table = Table(title=f"Recent Audit Logs (last {hours}h)")
    table.add_column("Time")
    table.add_column("User", style="cyan")
    table.add_column("Description")

    for log in logs:
        desc = log.get("description", "")
        if len(desc) > 60:
            desc = desc[:60] + "..."
        table.add_row(
            format_timestamp(log.get("happenedOn"), format="seconds"),
            log.get("username", ""),
            desc,
        )
    console.print(table)


@app.command("summary")
def log_summary(
    hours: Annotated[int, typer.Option("--hours", help="Hours to analyze")] = 24,
) -> None:
    """Show audit log summary for a time period."""
    svc = _get_service()
    logs = svc.list_recent(hours=hours, max_items=1000)

    if not logs:
        console.print(f"[dim]No audit logs in last {hours} hours[/dim]")
        return

    # Count by user
    user_counts: dict[str, int] = {}
    for log in logs:
        user = log.get("username", "unknown")
        user_counts[user] = user_counts.get(user, 0) + 1

    console.print(f"\n[bold]Audit Log Summary (last {hours}h)[/bold]")
    console.print(f"\nTotal events: {len(logs)}")
    console.print(f"Unique users: {len(user_counts)}")

    console.print("\n[bold]Top Users:[/bold]")
    sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for user, count in sorted_users:
        console.print(f"  {user}: {count}")
