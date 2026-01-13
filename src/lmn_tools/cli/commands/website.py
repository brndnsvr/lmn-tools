"""
Website (synthetic monitoring) management commands.

Provides commands for managing LogicMonitor website monitors.
"""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import get_settings
from lmn_tools.services.alerts import WebsiteService

app = typer.Typer(help="Manage website monitors (synthetic)")
console = Console()


def _get_client() -> LMClient:
    """Get authenticated API client."""
    settings = get_settings()
    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        raise typer.Exit(1) from None
    return LMClient.from_credentials(settings.credentials)  # type: ignore


def _get_service() -> WebsiteService:
    """Get website service."""
    return WebsiteService(_get_client())


@app.command("list")
def list_websites(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    group: Annotated[int | None, typer.Option("--group", "-g", help="Filter by group ID")] = None,
    type: Annotated[str | None, typer.Option("--type", "-t", help="Filter by type: webcheck, pingcheck")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List website monitors."""
    svc = _get_service()

    filters = []
    if filter:
        filters.append(filter)
    if group:
        filters.append(f"groupId:{group}")
    if type:
        filters.append(f"type:{type}")
    filter_str = ",".join(filters) if filters else None

    websites = svc.list(filter=filter_str, max_items=limit)

    if format == "json":
        console.print_json(data=websites)
    elif format == "ids":
        for w in websites:
            console.print(w["id"])
    else:
        if not websites:
            console.print("[dim]No website monitors found[/dim]")
            return

        table = Table(title=f"Website Monitors ({len(websites)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("URL/Host")
        table.add_column("Status")
        table.add_column("Overall Status")

        for w in websites:
            # Determine status style
            status = w.get("status", "unknown")
            status_style = "green" if status == "active" else "yellow" if status == "dead" else "dim"

            overall = w.get("overallAlertLevel", "")
            overall_style = "green" if overall == "normal" else "red" if overall in ("error", "critical") else "yellow"

            # Get URL or host based on type
            url_host = w.get("domain", "") or w.get("host", "") or "N/A"
            if len(url_host) > 40:
                url_host = url_host[:40] + "..."

            table.add_row(
                str(w["id"]),
                w.get("name", ""),
                w.get("type", ""),
                url_host,
                f"[{status_style}]{status}[/{status_style}]",
                f"[{overall_style}]{overall}[/{overall_style}]",
            )
        console.print(table)


@app.command("get")
def get_website(
    identifier: Annotated[str, typer.Argument(help="Website ID or name")],
    show_checks: Annotated[bool, typer.Option("--checks", "-c", help="Show checkpoint status")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get website monitor details."""
    svc = _get_service()

    # Try as ID first, then search by name
    try:
        website_id = int(identifier)
        response = svc.get(website_id)
        website = response.get("data", response) if "data" in response else response
    except ValueError:
        websites = svc.list(filter=f"name:{identifier}")
        if not websites:
            console.print(f"[red]Website not found: {identifier}[/red]")
            raise typer.Exit(1) from None
        website = websites[0]
        website_id = website["id"]

    if format == "json":
        console.print_json(data=website)
        return

    console.print(f"\n[bold cyan]{website.get('name', 'N/A')}[/bold cyan] (ID: {website_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Type", website.get("type", "N/A"))
    detail_table.add_row("Domain/Host", website.get("domain", "") or website.get("host", "N/A"))
    detail_table.add_row("Description", website.get("description", "N/A") or "N/A")
    detail_table.add_row("Status", website.get("status", "N/A"))
    detail_table.add_row("Overall Alert", website.get("overallAlertLevel", "N/A"))
    detail_table.add_row("Group ID", str(website.get("groupId", "N/A")))
    detail_table.add_row("Polling Interval", f"{website.get('pollingInterval', 0)} minutes")
    detail_table.add_row("Alerting Disabled", str(website.get("disableAlerting", False)))

    # Type-specific fields
    if website.get("type") == "webcheck":
        detail_table.add_row("", "")
        detail_table.add_row("[bold]Web Check Config:[/bold]", "")
        detail_table.add_row("  HTTP Type", website.get("httpType", "N/A"))
        detail_table.add_row("  Use SSL", str(website.get("useSSL", False)))
        if website.get("schema"):
            detail_table.add_row("  Schema", website.get("schema", ""))

    console.print(detail_table)

    if show_checks:
        console.print("\n[bold]Checkpoint Status:[/bold]")
        checks = svc.list_checks(website_id)
        if checks:
            check_table = Table(show_header=True, box=None)
            check_table.add_column("ID", style="dim")
            check_table.add_column("Name")
            check_table.add_column("Status")

            for check in checks:
                check_status = check.get("status", "unknown")
                check_style = "green" if check_status == "active" else "red"
                check_table.add_row(
                    str(check.get("id", "")),
                    check.get("name", check.get("geoInfo", "Unknown")),
                    f"[{check_style}]{check_status}[/{check_style}]",
                )
            console.print(check_table)
        else:
            console.print("  [dim]No checkpoints configured[/dim]")


@app.command("search")
def search_websites(
    query: Annotated[str, typer.Argument(help="Search query")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 20,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Search website monitors by name."""
    svc = _get_service()
    websites = svc.list(filter=f'name~"{query}"', max_items=limit)

    if format == "json":
        console.print_json(data=websites)
        return

    if not websites:
        console.print(f"[dim]No websites matching '{query}'[/dim]")
        return

    table = Table(title=f"Search Results ({len(websites)})")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("URL/Host")

    for w in websites:
        url_host = w.get("domain", "") or w.get("host", "") or "N/A"
        table.add_row(
            str(w["id"]),
            w.get("name", ""),
            w.get("type", ""),
            url_host[:50],
        )
    console.print(table)


@app.command("status")
def website_status(
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Show overall website monitoring status."""
    svc = _get_service()
    websites = svc.list(max_items=500)

    if format == "json":
        by_status: dict[str, int] = {}
        by_alert_level: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for w in websites:
            status = w.get("status", "unknown")
            alert = w.get("overallAlertLevel", "unknown")
            wtype = w.get("type", "unknown")

            by_status[status] = by_status.get(status, 0) + 1
            by_alert_level[alert] = by_alert_level.get(alert, 0) + 1
            by_type[wtype] = by_type.get(wtype, 0) + 1

        summary: dict[str, Any] = {
            "total": len(websites),
            "by_status": by_status,
            "by_alert_level": by_alert_level,
            "by_type": by_type,
        }
        console.print_json(data=summary)
        return

    # Count by status and alert level
    status_counts: dict[str, int] = {}
    alert_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}

    for w in websites:
        status = w.get("status", "unknown")
        alert = w.get("overallAlertLevel", "unknown")
        wtype = w.get("type", "unknown")

        status_counts[status] = status_counts.get(status, 0) + 1
        alert_counts[alert] = alert_counts.get(alert, 0) + 1
        type_counts[wtype] = type_counts.get(wtype, 0) + 1

    console.print(f"\n[bold]Website Monitor Status[/bold] (Total: {len(websites)})")
    console.print()

    # Status breakdown
    console.print("[bold]By Status:[/bold]")
    for status, count in sorted(status_counts.items()):
        style = "green" if status == "active" else "yellow" if status == "dead" else "dim"
        console.print(f"  [{style}]{status}[/{style}]: {count}")

    # Alert level breakdown
    console.print("\n[bold]By Alert Level:[/bold]")
    for alert, count in sorted(alert_counts.items()):
        style = "green" if alert == "normal" else "red" if alert in ("error", "critical") else "yellow"
        console.print(f"  [{style}]{alert}[/{style}]: {count}")

    # Type breakdown
    console.print("\n[bold]By Type:[/bold]")
    for wtype, count in sorted(type_counts.items()):
        console.print(f"  {wtype}: {count}")


@app.command("groups")
def list_website_groups(
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List website groups."""
    client = _get_client()
    response = client.get("/website/groups")
    groups = response.get("items", response.get("data", {}).get("items", []))

    if format == "json":
        console.print_json(data=groups)
        return

    if not groups:
        console.print("[dim]No website groups found[/dim]")
        return

    table = Table(title=f"Website Groups ({len(groups)})")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Full Path")
    table.add_column("Websites", justify="right")

    for g in groups:
        table.add_row(
            str(g.get("id", "")),
            g.get("name", ""),
            g.get("fullPath", ""),
            str(g.get("numOfWebsites", 0)),
        )
    console.print(table)


# ============================================================================
# Write Operations (CRUD)
# ============================================================================


@app.command("create")
def create_website(
    name: Annotated[str, typer.Argument(help="Website name")],
    domain: Annotated[str, typer.Option("--domain", "-d", help="Domain or URL to monitor")],
    type: Annotated[str, typer.Option("--type", "-t", help="Monitor type: webcheck, pingcheck")] = "webcheck",
    group: Annotated[int, typer.Option("--group", "-g", help="Website group ID")] = 1,
    description: Annotated[str | None, typer.Option("--description", help="Description")] = None,
    polling_interval: Annotated[int, typer.Option("--interval", help="Polling interval in minutes")] = 5,
    use_ssl: Annotated[bool, typer.Option("--ssl/--no-ssl", help="Use SSL")] = True,
    disable_alerting: Annotated[bool, typer.Option("--disable-alerting", help="Disable alerting")] = False,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new website monitor."""
    svc = _get_service()

    website_data: dict[str, Any] = {
        "name": name,
        "type": type,
        "domain": domain,
        "groupId": group,
        "pollingInterval": polling_interval,
        "disableAlerting": disable_alerting,
    }

    if description:
        website_data["description"] = description

    if type == "webcheck":
        website_data["useSSL"] = use_ssl
        website_data["httpType"] = "https" if use_ssl else "http"

    try:
        response = svc.create(website_data)
        result = response.get("data", response) if "data" in response else response
        website_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created website monitor '{name}' (ID: {website_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create website: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("update")
def update_website(
    website_id: Annotated[int, typer.Argument(help="Website ID")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New name")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="New description")] = None,
    domain: Annotated[str | None, typer.Option("--domain", help="New domain")] = None,
    polling_interval: Annotated[int | None, typer.Option("--interval", help="Polling interval")] = None,
    disable_alerting: Annotated[bool | None, typer.Option("--disable-alerting/--enable-alerting", help="Toggle alerting")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update a website monitor."""
    svc = _get_service()

    update_data: dict[str, Any] = {}

    if name:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if domain:
        update_data["domain"] = domain
    if polling_interval is not None:
        update_data["pollingInterval"] = polling_interval
    if disable_alerting is not None:
        update_data["disableAlerting"] = disable_alerting

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0) from None

    try:
        response = svc.update(website_id, update_data)
        result = response.get("data", response) if "data" in response else response

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated website {website_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update website: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_website(
    website_id: Annotated[int, typer.Argument(help="Website ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a website monitor."""
    svc = _get_service()

    # Get website info first
    try:
        response = svc.get(website_id)
        website = response.get("data", response) if "data" in response else response
        website_name = website.get("name", f"ID:{website_id}")
    except Exception:
        website_name = f"ID:{website_id}"

    if not force:
        confirm = typer.confirm(f"Delete website monitor '{website_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(website_id)
        console.print(f"[green]Deleted website monitor '{website_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete website: {e}[/red]")
        raise typer.Exit(1) from None
