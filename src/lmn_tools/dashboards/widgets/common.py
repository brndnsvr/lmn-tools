"""
Common utilities, constants, and classes for widget builders.

This module contains shared functionality used across all widget types:
- WidgetPosition class for tracking widget placement
- Grid constants
- Color palettes
- Helper functions
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Widget positioning - LM uses a 24-column grid
GRID_COLUMNS = 24
DEFAULT_WIDGET_WIDTH = 12
DEFAULT_GRAPH_HEIGHT = 4
DEFAULT_TABLE_HEIGHT = 6
DEFAULT_TEXT_HEIGHT = 3


@dataclass
class WidgetPosition:
    """Track widget positioning on dashboard."""
    col: int = 0
    row: int = 0

    def next_row(self, height: int):
        """Move to next row."""
        self.row += height
        self.col = 0

    def next_col(self, width: int):
        """Move to next column, wrapping if needed."""
        self.col += width
        if self.col >= GRID_COLUMNS:
            self.col = 0
            self.row += DEFAULT_GRAPH_HEIGHT


# Color palette for multi-interface graphs
INTERFACE_COLORS = [
    ('#2ecc71', '#27ae60'),  # Green pair (In/Out)
    ('#3498db', '#2980b9'),  # Blue pair
    ('#e74c3c', '#c0392b'),  # Red pair
    ('#9b59b6', '#8e44ad'),  # Purple pair
    ('#f39c12', '#d68910'),  # Orange pair
    ('#1abc9c', '#16a085'),  # Teal pair
    ('#e91e63', '#c2185b'),  # Pink pair
    ('#00bcd4', '#0097a7'),  # Cyan pair
]


def get_interface_type(device_role: str, interface_name: str, alias: str = '') -> str:
    """
    Determine interface type based on device role and interface name.

    Args:
        device_role: Role of the device (router, leaf, etc.)
        interface_name: Name of the interface (ae100.3, irb.1008, xe-0/0/37.1460, etc.)
        alias: Interface alias/description

    Returns:
        Interface type: 'internet', 'cloudconnect', 'access', or 'other'
    """
    if device_role == 'router':
        if interface_name.startswith('irb'):
            return 'internet'
        elif interface_name.startswith(('ae100', 'ae110', 'ae120')) or alias.startswith('CC_'):
            return 'cloudconnect'
    elif device_role == 'leaf':
        return 'access'
    return 'other'
