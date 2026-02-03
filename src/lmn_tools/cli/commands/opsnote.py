"""
OpsNote management commands.

Provides commands for managing LogicMonitor operational notes.
"""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from lmn_tools.cli.utils import format_timestamp, get_client, unwrap_response
from lmn_tools.services.operations import OpsNoteService

app = typer.Typer(help="Manage operational notes")
console = Console()


def _get_service() -> OpsNoteService:
    """Get OpsNote service."""
    return OpsNoteService(get_client(console))


def _format_scopes(scopes: list[dict[str, Any]]) -> str:
    """Format scopes list to readable string."""
    if not scopes:
        return "N/A"
    parts = []
    for s in scopes:
        scope_type = s.get("type", "?")
        scope_id = s.get("id", "?")
        parts.append(f"{scope_type}:{scope_id}")
    return ", ".join(parts)


def _format_tags(tags: list[dict[str, Any]]) -> str:
    """Format tags list to readable string."""
    if not tags:
        return ""
    return ", ".join(t.get("name", "?") for t in tags)


@app.command("list")
def list_opsnotes(
    device: Annotated[
        int | None, typer.Option("--device", "-d", help="Filter by device ID")
    ] = None,
    group: Annotated[int | None, typer.Option("--group", "-g", help="Filter by group ID")] = None,
    tag: Annotated[str | None, typer.Option("--tag", "-t", help="Filter by tag")] = None,
    filter: Annotated[str | None, typer.Option("--filter", "-f", help="LM filter string")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results")] = 50,
    format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, ids")
    ] = "table",
) -> None:
    """List OpsNotes with optional filtering."""
    svc = _get_service()

    if device:
        notes = svc.list_by_device(device, max_items=limit)
    elif group:
        notes = svc.list_by_group(group, max_items=limit)
    elif tag:
        notes = svc.list_by_tag(tag, max_items=limit)
    else:
        notes = svc.list(filter=filter, max_items=limit)

    if format == "json":
        console.print_json(data=notes)
    elif format == "ids":
        for n in notes:
            console.print(n.get("id", ""))
    else:
        if not notes:
            console.print("[dim]No OpsNotes found[/dim]")
            return

        table = Table(title=f"OpsNotes ({len(notes)})")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Note", style="cyan")
        table.add_column("Scopes")
        table.add_column("Tags")
        table.add_column("Created")

        for n in notes:
            note_text = n.get("note", "")
            if len(note_text) > 40:
                note_text = note_text[:40] + "..."
            table.add_row(
                str(n.get("id", "")),
                note_text,
                _format_scopes(n.get("scopes", [])),
                _format_tags(n.get("tags", [])),
                format_timestamp(n.get("createdOn")),
            )
        console.print(table)


@app.command("get")
def get_opsnote(
    note_id: Annotated[int, typer.Argument(help="OpsNote ID")],
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Get OpsNote details."""
    svc = _get_service()
    response = svc.get(note_id)
    note = unwrap_response(response)

    if format == "json":
        console.print_json(data=note)
        return

    console.print(f"\n[bold cyan]OpsNote {note_id}[/bold cyan]")
    console.print()

    detail_table = Table(show_header=False, box=None)
    detail_table.add_column("Field", style="dim")
    detail_table.add_column("Value")

    detail_table.add_row("Note", note.get("note", "N/A"))
    detail_table.add_row("Scopes", _format_scopes(note.get("scopes", [])))
    detail_table.add_row("Tags", _format_tags(note.get("tags", [])) or "N/A")
    detail_table.add_row("Created", format_timestamp(note.get("createdOn")))
    detail_table.add_row("Created By", note.get("createdBy", "N/A"))

    console.print(detail_table)


@app.command("create")
def create_opsnote(
    note: Annotated[str, typer.Argument(help="Note text")],
    device: Annotated[int | None, typer.Option("--device", "-d", help="Device ID")] = None,
    group: Annotated[int | None, typer.Option("--group", "-g", help="Device group ID")] = None,
    tags: Annotated[str | None, typer.Option("--tags", "-t", help="Comma-separated tags")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Create a new OpsNote."""
    svc = _get_service()

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    try:
        if device:
            result = unwrap_response(svc.create_device_note(device, note, tag_list))
        elif group:
            result = unwrap_response(svc.create_group_note(group, note, tag_list))
        else:
            console.print("[red]Must specify --device or --group[/red]")
            raise typer.Exit(1) from None

        new_id = result.get("id")

        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Created OpsNote (ID: {new_id})[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create OpsNote: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("update")
def update_opsnote(
    note_id: Annotated[int, typer.Argument(help="OpsNote ID")],
    note: Annotated[str | None, typer.Option("--note", "-n", help="New note text")] = None,
    tags: Annotated[
        str | None, typer.Option("--tags", "-t", help="New comma-separated tags")
    ] = None,
    format: Annotated[str, typer.Option("--format", help="Output format: table, json")] = "table",
) -> None:
    """Update an OpsNote."""
    svc = _get_service()

    update_data: dict[str, Any] = {}
    if note:
        update_data["note"] = note
    if tags is not None:
        tag_list = [{"name": t.strip()} for t in tags.split(",") if t.strip()]
        update_data["tags"] = tag_list

    if not update_data:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(0) from None

    try:
        result = unwrap_response(svc.update(note_id, update_data))
        if format == "json":
            console.print_json(data=result)
        else:
            console.print(f"[green]Updated OpsNote {note_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update OpsNote: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("delete")
def delete_opsnote(
    note_id: Annotated[int, typer.Argument(help="OpsNote ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete an OpsNote."""
    svc = _get_service()

    if not force:
        confirm = typer.confirm(f"Delete OpsNote {note_id}?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0) from None

    try:
        svc.delete(note_id)
        console.print(f"[green]Deleted OpsNote {note_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to delete OpsNote: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("add-tag")
def add_tag(
    note_id: Annotated[int, typer.Argument(help="OpsNote ID")],
    tag: Annotated[str, typer.Argument(help="Tag to add")],
) -> None:
    """Add a tag to an OpsNote."""
    svc = _get_service()

    try:
        svc.add_tag(note_id, tag)
        console.print(f"[green]Added tag '{tag}' to OpsNote {note_id}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to add tag: {e}[/red]")
        raise typer.Exit(1) from None
