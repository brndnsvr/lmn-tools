"""
User/Admin management commands.

Provides commands for listing LogicMonitor users (read-only).
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import get_settings
from lmn_tools.services.base import BaseService

app = typer.Typer(help="View users (read-only)")
console = Console()


class UserService(BaseService):
    """Service for viewing LogicMonitor users/admins."""

    @property
    def base_path(self) -> str:
        return "/setting/admins"


def _get_client() -> LMClient:
    """Get authenticated API client."""
    settings = get_settings()
    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        raise typer.Exit(1) from None
    return LMClient.from_credentials(settings.credentials)  # type: ignore


def _get_service() -> UserService:
    """Get user service."""
    return UserService(_get_client())


@app.command("list")
def list_users(
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    role: Annotated[str | None, typer.Option("--role", "-r", help="Filter by role name")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json, ids")] = "table",
) -> None:
    """List users/admins."""
    svc = _get_service()

    filters = []
    if filter:
        filters.append(filter)
    if role:
        filters.append(f'roles.name:"{role}"')
    filter_str = ",".join(filters) if filters else None

    users = svc.list(filter=filter_str, max_items=limit)

    if format == "json":
        console.print_json(data=users)
    elif format == "ids":
        for u in users:
            console.print(u["id"])
    else:
        table = Table(title=f"Users ({len(users)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Username", style="cyan")
        table.add_column("First Name")
        table.add_column("Last Name")
        table.add_column("Email")
        table.add_column("Status")

        for u in users:
            status = u.get("status", "")
            status_style = "green" if status == "active" else "dim"
            table.add_row(
                str(u["id"]),
                u.get("username", ""),
                u.get("firstName", ""),
                u.get("lastName", ""),
                u.get("email", ""),
                f"[{status_style}]{status}[/{status_style}]",
            )
        console.print(table)


@app.command("get")
def get_user(
    identifier: Annotated[str, typer.Argument(help="User ID or username")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get user details."""
    svc = _get_service()

    try:
        user_id = int(identifier)
        response = svc.get(user_id)
        user = response.get("data", response) if "data" in response else response
    except ValueError:
        results = svc.list(filter=f'username:"{identifier}"', max_items=1)
        if not results:
            console.print(f"[red]User not found: {identifier}[/red]")
            raise typer.Exit(1) from None
        user = results[0]
        user_id = user["id"]

    if format == "json":
        console.print_json(data=user)
        return

    console.print(f"\n[bold cyan]{user.get('username', 'N/A')}[/bold cyan] (ID: {user_id})")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("First Name", user.get("firstName", "N/A"))
    detail_table.add_row("Last Name", user.get("lastName", "N/A"))
    detail_table.add_row("Email", user.get("email", "N/A"))
    detail_table.add_row("Status", user.get("status", "N/A"))
    detail_table.add_row("Last Login", str(user.get("lastLoginOn", "N/A")))
    detail_table.add_row("API Only", str(user.get("apionly", False)))
    detail_table.add_row("Two-Factor", str(user.get("twoFAEnabled", False)))

    # Show roles
    roles = user.get("roles", [])
    if roles:
        role_names = ", ".join(r.get("name", "") for r in roles)
        detail_table.add_row("Roles", role_names)

    console.print(detail_table)


@app.command("roles")
def list_roles(
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """List available roles."""
    client = _get_client()
    response = client.get("/setting/roles")
    roles = response.get("items", response.get("data", {}).get("items", []))

    if format == "json":
        console.print_json(data=roles)
        return

    if not roles:
        console.print("[dim]No roles found[/dim]")
        return

    table = Table(title=f"Roles ({len(roles)})")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for r in roles:
        desc = r.get("description", "") or ""
        if len(desc) > 40:
            desc = desc[:40] + "..."
        table.add_row(
            str(r.get("id", "")),
            r.get("name", ""),
            desc,
        )
    console.print(table)
