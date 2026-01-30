"""
Recipient group management commands.

Provides commands for managing LogicMonitor notification recipient groups.
"""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import get_client, load_json_file, unwrap_response
from lmn_tools.services.notifications import RecipientGroupService

app = typer.Typer(help="Manage recipient groups")
console = Console()


def _get_service() -> RecipientGroupService:
    """Get recipient group service."""
    return RecipientGroupService(get_client(console))


def _format_recipients(recipients: list[dict[str, Any]]) -> str:
    """Format recipients list to readable string."""
    if not recipients:
        return "None"
    return str(len(recipients)) + " recipients"


@app.command("list")
def list_groups(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List recipient groups."""
    svc = _get_service()
    groups = svc.list(filter=filter, max_items=limit)

    if format == "json":
        console.print_json(data=groups)
    elif format == "ids":
        for g in groups:
            console.print(g.get("id", ""))
    else:
        if not groups:
            console.print("[dim]No recipient groups found[/dim]")
            return

        table = Table(title=f"Recipient Groups ({len(groups)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        table.add_column("Recipients")

        for g in groups:
            table.add_row(
                str(g.get("id", "")),
                g.get("groupName", ""),
                (g.get("description", "") or "")[:30],
                _format_recipients(g.get("recipients", [])),
            )
        console.print(table)


@app.command("get")
def get_group(
    group_id: Annotated[int, typer.Argument(help="Recipient group ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get recipient group details."""
    svc = _get_service()
    response = svc.get(group_id)
    group = unwrap_response(response)

    if format == "json":
        console.print_json(data=group)
        return

    console.print(f"\n[bold cyan]{group.get('groupName', 'N/A')}[/bold cyan] (ID: {group_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Description", group.get("description", "N/A") or "N/A")

    console.print(detail_table)

    recipients = group.get("recipients", [])
    if recipients:
        console.print("\n[bold]Recipients:[/bold]")
        for r in recipients:
            rtype = r.get("type", "?")
            method = r.get("method", "?")
            if rtype == "ARBITRARY":
                console.print(f"  - [{method}] {r.get('addr', 'N/A')}")
            elif rtype == "ADMIN":
                console.print(f"  - [{method}] Admin ID: {r.get('admin', 'N/A')}")
            else:
                console.print(f"  - [{rtype}] {method}")
    else:
        console.print("\n[dim]No recipients configured[/dim]")


@app.command("create")
def create_group(
    name: Annotated[str, typer.Option("--name", "-n", help="Group name")],
    description: Annotated[str | None, typer.Option("--description", "-d", help="Description")] = None,
    config_file: Annotated[str | None, typer.Option("--config", help="JSON config file")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new recipient group."""
    svc = _get_service()

    group_data: dict[str, Any]
    if config_file:
        group_data = load_json_file(config_file, console)
    else:
        group_data = {
            "groupName": name,
            "recipients": [],
        }
        if description:
            group_data["description"] = description

    try:
        result = unwrap_response(svc.create(group_data))
        new_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created recipient group '{name}' (ID: {new_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create recipient group: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("update")
def update_group(
    group_id: Annotated[int, typer.Argument(help="Recipient group ID")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New name")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="New description")] = None,
    config_file: Annotated[str | None, typer.Option("--config", help="JSON config file")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update a recipient group."""
    svc = _get_service()

    update_data: dict[str, Any]
    if config_file:
        update_data = load_json_file(config_file, console)
    else:
        update_data = {}
        if name:
            update_data["groupName"] = name
        if description is not None:
            update_data["description"] = description

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0) from None

    try:
        result = unwrap_response(svc.update(group_id, update_data))
        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated recipient group {group_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update recipient group: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_group(
    group_id: Annotated[int, typer.Argument(help="Recipient group ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a recipient group."""
    svc = _get_service()

    try:
        group = unwrap_response(svc.get(group_id))
        group_name = group.get("groupName", f"ID:{group_id}")
    except Exception:
        group_name = f"ID:{group_id}"

    if not force:
        confirm = typer.confirm(f"Delete recipient group '{group_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(group_id)
        console.print(f"[green]Deleted recipient group '{group_name}'[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete recipient group: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("add-email")
def add_email_recipient(
    group_id: Annotated[int, typer.Argument(help="Recipient group ID")],
    email: Annotated[str, typer.Argument(help="Email address to add")],
) -> None:
    """Add an email recipient to a group."""
    svc = _get_service()

    try:
        svc.add_email_recipient(group_id, email)
        console.print(f"[green]Added {email} to recipient group {group_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to add recipient: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("add-admin")
def add_admin_recipient(
    group_id: Annotated[int, typer.Argument(help="Recipient group ID")],
    admin_id: Annotated[int, typer.Argument(help="Admin user ID to add")],
    method: Annotated[str, typer.Option("--method", "-m", help="Contact method")] = "email",
) -> None:
    """Add an admin user as a recipient."""
    svc = _get_service()

    try:
        svc.add_admin_recipient(group_id, admin_id, method)
        console.print(f"[green]Added admin {admin_id} to recipient group {group_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to add recipient: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("recipients")
def list_recipients(
    group_id: Annotated[int, typer.Argument(help="Recipient group ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List recipients in a group."""
    svc = _get_service()
    recipients = svc.get_recipients(group_id)

    if format == "json":
        console.print_json(data=recipients)
        return

    if not recipients:
        console.print("[dim]No recipients in this group[/dim]")
        return

    table = Table(title=f"Recipients in Group {group_id}")
    table.add_column("Type")
    table.add_column("Method")
    table.add_column("Address/ID")

    for r in recipients:
        rtype = r.get("type", "?")
        method = r.get("method", "?")
        if rtype == "ARBITRARY":
            addr = r.get("addr", "N/A")
        elif rtype == "ADMIN":
            addr = f"Admin: {r.get('admin', 'N/A')}"
        else:
            addr = str(r)

        table.add_row(rtype, method, addr)

    console.print(table)
