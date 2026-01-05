"""
Output formatters for lmn-tools.

Provides formatting for LogicMonitor script output
in various formats (BATCHSCRIPT, JSON, table).
"""

from __future__ import annotations

from lmn_tools.formatters.output import (
    OutputFormatter,
    print_collection,
    print_collection_table,
    print_discovery,
    print_discovery_table,
)

__all__ = [
    "OutputFormatter",
    "print_discovery",
    "print_collection",
    "print_discovery_table",
    "print_collection_table",
]
