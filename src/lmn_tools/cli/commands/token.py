"""
API token management commands.

Provides commands for managing LogicMonitor API tokens.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import get_client, unwrap_response
from lmn_tools.services.tokens import APITokenService

app = typer.Typer(help="Manage API tokens")
console = Console()


def _get_service() -> APITokenService:
    """Get API token service."""
    return APITokenService(get_client(console))


def _format_timestamp(ts: int | None) -> str:
    """Format epoch timestamp to readable string."""
    if not ts:
        return "N/A"
    try:
        ts_secs: float = ts / 1000 if ts >= 1e12 else float(ts)
        return datetime.fromtimestamp(ts_secs).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)


@app.command("list")
def list_tokens(
    user: Annotated[int | None, typer.Option("--user", "-u", help="Filter by admin user ID")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List API tokens."""
    svc = _get_service()

    if user:
        tokens = svc.list_for_user(user, max_items=limit)
    else:
        tokens = svc.list_all_tokens(max_items=limit)

    if format == "json":
        console.print_json(data=tokens)
    elif format == "ids":
        for t in tokens:
            console.print(t.get("id", ""))
    else:
        if not tokens:
            console.print("[dim]No API tokens found[/dim]")
            return

        table = Table(title=f"API Tokens ({len(tokens)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Access ID", style="cyan")
        table.add_column("Note")
        table.add_column("User")
        table.add_column("Status")
        table.add_column("Created")

        for t in tokens:
            access_id = t.get("accessId", "")
            # Truncate access ID for display
            access_id_display = access_id[:12] + "..." if len(access_id) > 12 else access_id
            status = "[green]Active[/green]" if t.get("status") == 2 else "[red]Inactive[/red]"
            admin_info = t.get("adminName", str(t.get("adminId", "")))

            table.add_row(
                str(t.get("id", "")),
                access_id_display,
                (t.get("note", "") or "")[:25],
                admin_info,
                status,
                _format_timestamp(t.get("createdOn")),
            )
        console.print(table)


@app.command("get")
def get_token(
    user_id: Annotated[int, typer.Argument(help="Admin user ID")],
    token_id: Annotated[int, typer.Argument(help="Token ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get API token details."""
    svc = _get_service()
    response = svc.get_token(user_id, token_id)
    token = unwrap_response(response)

    if format == "json":
        console.print_json(data=token)
        return

    console.print(f"\n[bold]API Token {token_id}[/bold]")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Access ID", token.get("accessId", "N/A"))
    detail_table.add_row("Note", token.get("note", "N/A") or "N/A")
    detail_table.add_row("Admin ID", str(token.get("adminId", "N/A")))
    detail_table.add_row("Admin Name", token.get("adminName", "N/A"))
    status = "Active" if token.get("status") == 2 else "Inactive"
    detail_table.add_row("Status", status)
    detail_table.add_row("Created", _format_timestamp(token.get("createdOn")))
    detail_table.add_row("Last Used", _format_timestamp(token.get("lastUsedOn")))

    console.print(detail_table)

    roles = token.get("roles", [])
    if roles:
        console.print("\n[bold]Roles:[/bold]")
        for r in roles:
            console.print(f"  - {r.get('name', r.get('id', 'N/A'))}")


@app.command("create")
def create_token(
    user_id: Annotated[int, typer.Argument(help="Admin user ID")],
    note: Annotated[str, typer.Option("--note", "-n", help="Token description")] = "",
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new API token for a user."""
    svc = _get_service()

    try:
        result = unwrap_response(svc.create_for_user(user_id, note))

        if format == "json":
            console.print_json(data=result)
        else:
            console.print("[green]Created API token[/green]")
            console.print()
            console.print("[bold yellow]IMPORTANT: Save these credentials - the access key is only shown once![/bold yellow]")
            console.print()
            console.print(f"Access ID:  [cyan]{result.get('accessId', 'N/A')}[/cyan]")
            console.print(f"Access Key: [cyan]{result.get('accessKey', 'N/A')}[/cyan]")
            console.print(f"Token ID:   {result.get('id', 'N/A')}")
    except Exception as e:
        console.print(f"[red]Failed to create API token: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_token(
    user_id: Annotated[int, typer.Argument(help="Admin user ID")],
    token_id: Annotated[int, typer.Argument(help="Token ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete an API token."""
    svc = _get_service()

    if not force:
        confirm = typer.confirm(f"Delete API token {token_id} for user {user_id}?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete_token(user_id, token_id)
        console.print(f"[green]Deleted API token {token_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete API token: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("user-tokens")
def list_user_tokens(
    user_id: Annotated[int, typer.Argument(help="Admin user ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List all tokens for a specific user."""
    svc = _get_service()
    tokens = svc.list_for_user(user_id)

    if format == "json":
        console.print_json(data=tokens)
        return

    if not tokens:
        console.print(f"[dim]No API tokens for user {user_id}[/dim]")
        return

    table = Table(title=f"API Tokens for User {user_id}")
    table.add_column("ID", style="dim")
    table.add_column("Access ID", style="cyan")
    table.add_column("Note")
    table.add_column("Status")
    table.add_column("Last Used")

    for t in tokens:
        access_id = t.get("accessId", "")
        access_id_display = access_id[:12] + "..." if len(access_id) > 12 else access_id
        status = "[green]Active[/green]" if t.get("status") == 2 else "[red]Inactive[/red]"

        table.add_row(
            str(t.get("id", "")),
            access_id_display,
            (t.get("note", "") or "")[:30],
            status,
            _format_timestamp(t.get("lastUsedOn")),
        )
    console.print(table)
