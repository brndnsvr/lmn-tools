"""
Batch job management commands.

Provides commands for viewing and managing LogicMonitor batch jobs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import get_client, unwrap_response
from lmn_tools.services.batch import BatchJobService

app = typer.Typer(help="Manage batch jobs")
console = Console()


def _get_service() -> BatchJobService:
    """Get batch job service."""
    return BatchJobService(get_client(console))


def _format_timestamp(ts: int | None) -> str:
    """Format epoch timestamp to readable string."""
    if not ts:
        return "N/A"
    try:
        ts_secs: float = ts / 1000 if ts >= 1e12 else float(ts)
        return datetime.fromtimestamp(ts_secs).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)


def _status_style(status: str) -> str:
    """Get Rich style for job status."""
    styles = {
        "running": "blue",
        "pending": "yellow",
        "completed": "green",
        "failed": "red",
        "cancelled": "dim",
    }
    return styles.get(status.lower(), "white")


@app.command("list")
def list_jobs(
    status: Annotated[str | None, typer.Option("--status", "-s", help="Filter by status")] = None,
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, ids")
    ] = "table",
) -> None:
    """List batch jobs with optional filtering."""
    svc = _get_service()

    if status:
        jobs = svc.list_by_status(status, max_items=limit)
    else:
        jobs = svc.list(filter=filter, max_items=limit)

    if format == "json":
        console.print_json(data=jobs)
    elif format == "ids":
        for j in jobs:
            console.print(j.get("id", ""))
    else:
        if not jobs:
            console.print("[dim]No batch jobs found[/dim]")
            return

        table = Table(title=f"Batch Jobs ({len(jobs)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Description")
        table.add_column("Status")
        table.add_column("Progress")
        table.add_column("Created")

        for j in jobs:
            job_status = j.get("status", "")
            status_styled = (
                f"[{_status_style(job_status)}]{job_status}[/{_status_style(job_status)}]"
            )

            progress = j.get("progress", 0)
            total = j.get("totalCount", 0)
            progress_str = f"{progress}/{total}" if total else str(progress) + "%"

            table.add_row(
                str(j.get("id", "")),
                j.get("description", "")[:40] or "N/A",
                status_styled,
                progress_str,
                _format_timestamp(j.get("createdOn")),
            )
        console.print(table)


@app.command("get")
def get_job(
    job_id: Annotated[int, typer.Argument(help="Batch job ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get batch job details."""
    svc = _get_service()
    response = svc.get(job_id)
    job = unwrap_response(response)

    if format == "json":
        console.print_json(data=job)
        return

    job_status = job.get("status", "")
    console.print(f"\n[bold]Batch Job {job_id}[/bold]")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    status_styled = f"[{_status_style(job_status)}]{job_status}[/{_status_style(job_status)}]"
    detail_table.add_row("Status", status_styled)
    detail_table.add_row("Description", job.get("description", "N/A") or "N/A")
    detail_table.add_row("Created", _format_timestamp(job.get("createdOn")))
    detail_table.add_row("Completed", _format_timestamp(job.get("completedOn")))
    detail_table.add_row("Progress", f"{job.get('progress', 0)}%")
    detail_table.add_row("Success Count", str(job.get("successCount", 0)))
    detail_table.add_row("Fail Count", str(job.get("failCount", 0)))
    detail_table.add_row("Total Count", str(job.get("totalCount", 0)))

    console.print(detail_table)


@app.command("status")
def job_status(
    job_id: Annotated[int, typer.Argument(help="Batch job ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get batch job status."""
    svc = _get_service()
    status = svc.get_status(job_id)

    if format == "json":
        console.print_json(data=status)
        return

    job_status_val = status.get("status", "")
    status_styled = (
        f"[{_status_style(job_status_val)}]{job_status_val}[/{_status_style(job_status_val)}]"
    )

    console.print(f"\n[bold]Batch Job {job_id}:[/bold] {status_styled}")

    if status.get("totalCount"):
        success = status.get("successCount", 0)
        fail = status.get("failCount", 0)
        total = status.get("totalCount", 0)
        console.print(f"Progress: {success + fail}/{total} (Success: {success}, Failed: {fail})")


@app.command("cancel")
def cancel_job(
    job_id: Annotated[int, typer.Argument(help="Batch job ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Cancel a running or pending batch job."""
    svc = _get_service()

    if not force:
        confirm = typer.confirm(f"Cancel batch job {job_id}?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.cancel(job_id)
        console.print(f"[yellow]Cancelled batch job {job_id}[/yellow]")
    except Exception as e:
        console.print(f"[red]Failed to cancel batch job: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("wait")
def wait_for_job(
    job_id: Annotated[int, typer.Argument(help="Batch job ID")],
    timeout: Annotated[int, typer.Option("--timeout", "-t", help="Timeout in seconds")] = 300,
    interval: Annotated[int, typer.Option("--interval", "-i", help="Poll interval in seconds")] = 5,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Wait for a batch job to complete."""
    svc = _get_service()

    console.print(f"[dim]Waiting for batch job {job_id} to complete...[/dim]")

    try:
        result = svc.wait_for_completion(job_id, poll_interval=interval, timeout=timeout)

        if format == "json":
            console.print_json(data=result)
            return

        job_status = result.get("status", "")
        status_styled = f"[{_status_style(job_status)}]{job_status}[/{_status_style(job_status)}]"
        console.print(f"\nBatch job {job_id} finished: {status_styled}")

        if result.get("totalCount"):
            console.print(
                f"Results: {result.get('successCount', 0)} success, "
                f"{result.get('failCount', 0)} failed of {result.get('totalCount', 0)} total"
            )

    except TimeoutError:
        console.print(f"[red]Timeout waiting for batch job {job_id}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Error waiting for batch job: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("running")
def list_running(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List running batch jobs."""
    svc = _get_service()
    jobs = svc.list_running(max_items=limit)

    if format == "json":
        console.print_json(data=jobs)
        return

    if not jobs:
        console.print("[green]No running batch jobs[/green]")
        return

    table = Table(title=f"Running Batch Jobs ({len(jobs)})")
    table.add_column("ID", style="dim")
    table.add_column("Description")
    table.add_column("Progress")
    table.add_column("Started")

    for j in jobs:
        progress = f"{j.get('progress', 0)}%"
        table.add_row(
            str(j.get("id", "")),
            j.get("description", "")[:40] or "N/A",
            progress,
            _format_timestamp(j.get("createdOn")),
        )
    console.print(table)
