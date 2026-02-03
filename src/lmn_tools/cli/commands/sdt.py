"""
SDT (Scheduled Downtime) management commands.

Provides commands for creating and managing maintenance windows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import get_settings
from lmn_tools.services.sdt import SDTService

app = typer.Typer(help="Manage SDT (maintenance windows)")
console = Console()


def _get_client() -> LMClient:
    """Get authenticated API client."""
    settings = get_settings()
    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        raise typer.Exit(1) from None
    return LMClient.from_credentials(settings.credentials)  # type: ignore


def _get_service() -> SDTService:
    """Get SDT service."""
    return SDTService(_get_client())


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


def _format_duration(start: int, end: int) -> str:
    """Format duration between timestamps (handles both seconds and milliseconds)."""
    if not start or not end:
        return "N/A"
    # Convert to seconds if in milliseconds
    start_secs = start / 1000 if start >= 1e12 else start
    end_secs = end / 1000 if end >= 1e12 else end
    duration_mins = int((end_secs - start_secs) / 60)
    if duration_mins < 60:
        return f"{duration_mins}m"
    elif duration_mins < 1440:
        return f"{duration_mins // 60}h {duration_mins % 60}m"
    else:
        return f"{duration_mins // 1440}d {(duration_mins % 1440) // 60}h"


@app.command("list")
def list_sdts(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    device: Annotated[
        int | None, typer.Option("--device", "-d", help="Filter by device ID")
    ] = None,
    active: Annotated[bool, typer.Option("--active", "-a", help="Show only active SDTs")] = False,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, ids")
    ] = "table",
) -> None:
    """List SDT (maintenance windows)."""
    svc = _get_service()

    if active:
        sdts = svc.list_active()
    elif device:
        sdts = svc.list_for_device(device)
    else:
        sdts = svc.list(filter=filter, max_items=limit)

    if format == "json":
        console.print_json(data=sdts)
    elif format == "ids":
        for s in sdts:
            console.print(s["id"])
    else:
        if not sdts:
            console.print("[dim]No SDTs found[/dim]")
            return

        table = Table(title=f"SDTs ({len(sdts)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Type")
        table.add_column("Target", style="cyan")
        table.add_column("Start")
        table.add_column("End")
        table.add_column("Duration")
        table.add_column("Comment")

        for s in sdts:
            # Determine target name
            target = (
                s.get("deviceDisplayName")
                or s.get("deviceGroupFullPath")
                or s.get("websiteName")
                or s.get("collectorDescription")
                or "N/A"
            )
            comment = s.get("comment", "")
            if len(comment) > 20:
                comment = comment[:20] + "..."

            table.add_row(
                str(s.get("id", "")),
                s.get("type", "").replace("SDT", ""),
                target,
                _format_timestamp(s.get("startDateTime")),
                _format_timestamp(s.get("endDateTime")),
                _format_duration(s.get("startDateTime", 0), s.get("endDateTime", 0)),
                comment,
            )
        console.print(table)


@app.command("active")
def list_active_sdts(
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List currently active SDTs."""
    svc = _get_service()
    sdts = svc.list_active()

    if format == "json":
        console.print_json(data=sdts)
        return

    if not sdts:
        console.print("[dim]No active SDTs[/dim]")
        return

    table = Table(title=f"Active SDTs ({len(sdts)})")
    table.add_column("ID", style="dim")
    table.add_column("Type")
    table.add_column("Target", style="cyan")
    table.add_column("Ends")
    table.add_column("Remaining")
    table.add_column("Comment")

    now = datetime.now().timestamp() * 1000

    for s in sdts:
        target = s.get("deviceDisplayName") or s.get("deviceGroupFullPath") or "N/A"
        end_ts = s.get("endDateTime", 0)
        remaining_mins = int((end_ts - now) / 60000) if end_ts else 0

        if remaining_mins < 60:
            remaining = f"{remaining_mins}m"
        else:
            remaining = f"{remaining_mins // 60}h {remaining_mins % 60}m"

        comment = s.get("comment", "")[:20]

        table.add_row(
            str(s.get("id", "")),
            s.get("type", "").replace("SDT", ""),
            target,
            _format_timestamp(end_ts),
            remaining,
            comment,
        )
    console.print(table)


@app.command("upcoming")
def list_upcoming_sdts(
    days: Annotated[int, typer.Option("--days", "-d", help="Days ahead to look")] = 7,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List upcoming scheduled SDTs."""
    svc = _get_service()
    sdts = svc.list_upcoming(days=days)

    if format == "json":
        console.print_json(data=sdts)
        return

    if not sdts:
        console.print(f"[dim]No SDTs scheduled in the next {days} days[/dim]")
        return

    table = Table(title=f"Upcoming SDTs (next {days} days)")
    table.add_column("Type")
    table.add_column("Target", style="cyan")
    table.add_column("Start")
    table.add_column("Duration")
    table.add_column("Comment")

    for s in sdts:
        target = s.get("deviceDisplayName") or s.get("deviceGroupFullPath") or "N/A"
        comment = s.get("comment", "")[:30]

        table.add_row(
            s.get("type", "").replace("SDT", ""),
            target,
            _format_timestamp(s.get("startDateTime")),
            _format_duration(s.get("startDateTime", 0), s.get("endDateTime", 0)),
            comment,
        )
    console.print(table)


@app.command("create")
def create_sdt(
    type: Annotated[
        str, typer.Option("--type", "-t", help="SDT type: device, group, datasource")
    ] = "device",
    device: Annotated[int | None, typer.Option("--device", "-d", help="Device ID")] = None,
    group: Annotated[int | None, typer.Option("--group", "-g", help="Device group ID")] = None,
    duration: Annotated[int, typer.Option("--duration", help="Duration in minutes")] = 60,
    comment: Annotated[str, typer.Option("--comment", "-c", help="SDT comment")] = "",
) -> None:
    """Create an SDT (maintenance window)."""
    svc = _get_service()

    try:
        if type == "device":
            if not device:
                console.print("[red]--device is required for device SDT[/red]")
                raise typer.Exit(1) from None
            result = svc.create_device_sdt(device, duration, comment)
        elif type == "group":
            if not group:
                console.print("[red]--group is required for group SDT[/red]")
                raise typer.Exit(1) from None
            result = svc.create_group_sdt(group, duration, comment)
        else:
            console.print(f"[red]Unknown SDT type: {type}[/red]")
            raise typer.Exit(1) from None

        sdt_id = result.get("data", result).get("id") if "data" in result else result.get("id")
        console.print(f"[green]Created SDT {sdt_id} for {duration} minutes[/green]")

    except Exception as e:
        console.print(f"[red]Failed to create SDT: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_sdt(
    sdt_id: Annotated[str, typer.Argument(help="SDT ID to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete an SDT."""
    svc = _get_service()

    if not force:
        confirm = typer.confirm(f"Delete SDT {sdt_id}?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(int(sdt_id))
        console.print(f"[green]Deleted SDT {sdt_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete SDT: {e}[/red]")
        raise typer.Exit(1) from None
