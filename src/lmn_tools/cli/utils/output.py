"""
Output utilities for CLI commands.

Provides formatted output helpers for diffs, syntax highlighting, and tables.
"""

from __future__ import annotations

import difflib
from collections.abc import Callable
from typing import Any

from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

# Default console
_console = Console()


def show_diff(
    old: str,
    new: str,
    old_label: str = "original",
    new_label: str = "modified",
    console: Console | None = None,
    max_lines: int = 80,
    title: str | None = None,
) -> bool:
    """Display unified diff with color coding.

    Shows additions in green, deletions in red, context in default color.

    Args:
        old: Original content
        new: New/modified content
        old_label: Label for original in diff header
        new_label: Label for new in diff header
        console: Console for output (uses default if None)
        max_lines: Maximum lines to display (truncates with message)
        title: Optional title to display before diff

    Returns:
        True if there were differences, False if identical
    """
    console = console or _console

    if old == new:
        return False

    diff = list(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=old_label,
            tofile=new_label,
        )
    )

    if not diff:
        return False

    if title:
        console.print(f"\n[bold]{title}[/bold]")

    lines_shown = 0
    for line in diff:
        if lines_shown >= max_lines:
            remaining = len(diff) - lines_shown
            console.print(f"[dim]... and {remaining} more lines[/dim]")
            break

        line_stripped = line.rstrip()
        if line.startswith("+") and not line.startswith("+++"):
            console.print(f"[green]{line_stripped}[/green]")
        elif line.startswith("-") and not line.startswith("---"):
            console.print(f"[red]{line_stripped}[/red]")
        else:
            console.print(line_stripped)
        lines_shown += 1

    console.print()
    return True


def show_syntax(
    code: str,
    lexer: str,
    console: Console | None = None,
    line_numbers: bool = True,
    theme: str = "monokai",
    title: str | None = None,
) -> None:
    """Display code with syntax highlighting.

    Args:
        code: Source code to display
        lexer: Pygments lexer name (e.g., "groovy", "bash", "json")
        console: Console for output
        line_numbers: Whether to show line numbers
        theme: Syntax highlighting theme
        title: Optional title to display before code
    """
    console = console or _console

    if title:
        console.print(f"\n[bold cyan]{title}[/bold cyan]\n")

    syntax = Syntax(code, lexer, theme=theme, line_numbers=line_numbers)
    console.print(syntax)


def get_syntax_lexer(script_type: str) -> str:
    """Get Pygments lexer name for script type.

    Args:
        script_type: Script type identifier (groovy, linux, windows)

    Returns:
        Pygments lexer name
    """
    lexer_map = {
        "groovy": "groovy",
        "linux": "bash",
        "windows": "powershell",
        "json": "json",
        "xml": "xml",
        "yaml": "yaml",
    }
    return lexer_map.get(script_type, "text")


def create_table(
    title: str,
    columns: list[tuple[str, str, str | None]],
    items: list[dict[str, Any]],
    item_count: int | None = None,
) -> Table:
    """Create a Rich table from items.

    Args:
        title: Table title (count will be appended)
        columns: List of (header, style, key) tuples where:
            - header: Column header text
            - style: Rich style string (e.g., "cyan", "dim")
            - key: Dictionary key to extract value (None for custom handling)
        items: List of dictionaries to display
        item_count: Override count in title (uses len(items) if None)

    Returns:
        Configured Rich Table

    Example:
        >>> table = create_table(
        ...     "DataSources",
        ...     [("ID", "dim", "id"), ("Name", "cyan", "name")],
        ...     [{"id": 1, "name": "foo"}]
        ... )
    """
    count = item_count if item_count is not None else len(items)
    table = Table(title=f"{title} ({count})")

    for header, style, _ in columns:
        if header == "ID":
            table.add_column(header, style=style, no_wrap=True)
        else:
            table.add_column(header, style=style)

    return table


def add_table_rows(
    table: Table,
    columns: list[tuple[str, str, str | None]],
    items: list[dict[str, Any]],
    formatters: dict[str, Callable[[Any], str]] | None = None,
) -> None:
    """Add rows to a table from items.

    Args:
        table: Table to add rows to
        columns: Column definitions (same as create_table)
        items: Items to add as rows
        formatters: Optional dict of key -> formatter function
    """
    formatters = formatters or {}

    for item in items:
        row = []
        for _, _, key in columns:
            if key is None:
                row.append("")
            elif key in formatters:
                row.append(formatters[key](item.get(key)))
            else:
                value = item.get(key, "")
                row.append(str(value) if value is not None else "")
        table.add_row(*row)


def format_status(value: str | None, normal: str = "normal") -> str:
    """Format a status value with color.

    Args:
        value: Status value
        normal: Value that indicates "normal" status

    Returns:
        Formatted string with Rich markup
    """
    if value is None:
        return "[dim]N/A[/dim]"
    if value == normal:
        return f"[green]{value}[/green]"
    return f"[red]{value}[/red]"


def format_enabled(value: bool | None) -> str:
    """Format a boolean enabled/disabled value.

    Args:
        value: Boolean or None

    Returns:
        Formatted string with Rich markup
    """
    if value is None:
        return "[dim]N/A[/dim]"
    if value:
        return "[green]Yes[/green]"
    return "[dim]No[/dim]"


def truncate(value: str | None, max_len: int = 60) -> str:
    """Truncate a string with ellipsis.

    Args:
        value: String to truncate
        max_len: Maximum length

    Returns:
        Truncated string or original if shorter
    """
    if not value:
        return ""
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."
