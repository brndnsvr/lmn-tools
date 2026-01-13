"""
Helper utilities for CLI commands.

Provides common functionality for response handling, file operations,
filter building, and editor workflows.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

# Default console for error output
_console = Console()


def unwrap_response(response: dict[str, Any]) -> dict[str, Any]:
    """Extract data from API response wrapper.

    LogicMonitor API responses are often wrapped in {"data": ...}.
    This function extracts the inner data consistently.

    Args:
        response: API response dictionary

    Returns:
        Unwrapped data dictionary
    """
    if "data" in response:
        result: dict[str, Any] = response["data"]
        return result
    return response


def load_json_file(
    path: str | Path,
    console: Console | None = None,
    unwrap: bool = True,
) -> dict[str, Any]:
    """Load and parse a JSON file with error handling.

    Args:
        path: Path to JSON file
        console: Console for error output (uses default if None)
        unwrap: If True, unwrap {"data": ...} wrapper

    Returns:
        Parsed JSON data

    Raises:
        typer.Exit: If file not found or invalid JSON
    """
    console = console or _console
    file_path = Path(path)

    if not file_path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1)

    try:
        data = json.loads(file_path.read_text())
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1) from None

    if unwrap and "data" in data:
        result: dict[str, Any] = data["data"]
        return result
    result2: dict[str, Any] = data
    return result2


def build_filter(*conditions: str | None) -> str | None:
    """Combine filter conditions into LM filter string.

    Args:
        *conditions: Filter condition strings (None values are ignored)

    Returns:
        Combined filter string or None if no conditions

    Example:
        >>> build_filter('name:"foo"', None, 'group:"bar"')
        'name:"foo",group:"bar"'
    """
    valid = [c for c in conditions if c]
    return ",".join(valid) if valid else None


def edit_in_editor(
    content: str,
    suffix: str = ".json",
    console: Console | None = None,
) -> tuple[str, bool]:
    """Open content in $EDITOR and return modified content.

    Creates a temporary file with the content, opens it in the user's
    editor ($EDITOR env var, defaults to vim), and returns the modified
    content after the editor closes.

    Args:
        content: Initial content to edit
        suffix: File extension for temp file (for syntax highlighting)
        console: Console for status output

    Returns:
        Tuple of (modified_content, was_modified)

    Raises:
        typer.Exit: If editor fails or content becomes invalid
    """
    console = console or _console
    editor = os.environ.get("EDITOR", "vim")

    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
        f.write(content)
        temp_path = f.name

    console.print(f"[dim]Opening in {editor}...[/dim]")

    try:
        subprocess.run([editor, temp_path], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Editor exited with error: {e}[/red]")
        Path(temp_path).unlink(missing_ok=True)
        raise typer.Exit(1) from None
    except FileNotFoundError:
        console.print(f"[red]Editor not found: {editor}[/red]")
        console.print("[dim]Set $EDITOR environment variable to your preferred editor[/dim]")
        Path(temp_path).unlink(missing_ok=True)
        raise typer.Exit(1) from None

    new_content = Path(temp_path).read_text()
    Path(temp_path).unlink(missing_ok=True)

    was_modified = new_content != content
    return new_content, was_modified


def edit_json_in_editor(
    data: dict[str, Any],
    console: Console | None = None,
) -> tuple[dict[str, Any], bool]:
    """Edit JSON data in $EDITOR.

    Serializes data to JSON, opens in editor, parses result.

    Args:
        data: Dictionary to edit
        console: Console for output

    Returns:
        Tuple of (modified_data, was_modified)

    Raises:
        typer.Exit: If editor fails or result is invalid JSON
    """
    console = console or _console
    original_json = json.dumps(data, indent=2)

    new_json, was_modified = edit_in_editor(original_json, suffix=".json", console=console)

    if not was_modified:
        return data, False

    try:
        new_data = json.loads(new_json)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON after edit: {e}[/red]")
        # Save to temp file so user doesn't lose work
        recovery_path = Path(tempfile.gettempdir()) / "lm_edit_recovery.json"
        recovery_path.write_text(new_json)
        console.print(f"[dim]Your changes saved to: {recovery_path}[/dim]")
        raise typer.Exit(1) from None

    return new_data, True
