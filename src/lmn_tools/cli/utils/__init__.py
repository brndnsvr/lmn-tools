"""
CLI utility modules for shared functionality.

Provides common utilities used across CLI commands:
- client: Authentication and API client access
- helpers: Response handling, JSON loading, filters
- output: Diff display, syntax highlighting, table creation
"""

from lmn_tools.cli.utils.client import get_client
from lmn_tools.cli.utils.helpers import (
    build_filter,
    edit_in_editor,
    edit_json_in_editor,
    load_json_file,
    unwrap_response,
)
from lmn_tools.cli.utils.output import (
    add_table_rows,
    create_table,
    format_enabled,
    format_status,
    get_syntax_lexer,
    show_diff,
    show_syntax,
    truncate,
)

__all__ = [
    "add_table_rows",
    "build_filter",
    "create_table",
    "edit_in_editor",
    "edit_json_in_editor",
    "format_enabled",
    "format_status",
    # Client
    "get_client",
    "get_syntax_lexer",
    "load_json_file",
    # Output
    "show_diff",
    "show_syntax",
    "truncate",
    # Helpers
    "unwrap_response",
]
