"""
Text and HTML widget builders for LogicMonitor dashboards.

This module provides functions to create text-based widgets:
- Header widgets
- Section header widgets
- Generic text/HTML widgets
"""

import logging
from typing import Optional

from ..lm_client import LMClient, LMAPIError
from .common import (
    WidgetPosition,
    GRID_COLUMNS,
    DEFAULT_TEXT_HEIGHT,
)

logger = logging.getLogger(__name__)


def create_text_widget(
    client: LMClient,
    dashboard_id: int,
    name: str,
    content: str,
    position: WidgetPosition,
    width: int = GRID_COLUMNS,
    height: int = DEFAULT_TEXT_HEIGHT
) -> Optional[int]:
    """
    Create a text/HTML widget on a dashboard.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        name: Widget name
        content: HTML/Markdown content
        position: Current position tracker
        width: Widget width in grid columns
        height: Widget height in grid rows

    Returns:
        Widget ID if created, None otherwise
    """
    widget_data = {
        'dashboardId': dashboard_id,
        'name': name,
        'type': 'text',
        'content': content,
        'col': position.col,
        'row': position.row,
        'colSpan': width,
        'rowSpan': height
    }

    try:
        response = client.post('/dashboard/widgets', json=widget_data)
        widget_id = response.get('data', {}).get('id') or response.get('id')
        position.next_row(height)
        logger.info(f"Created text widget: {name} -> {widget_id}")
        return widget_id
    except LMAPIError as e:
        logger.error(f"Failed to create text widget {name}: {e}")
        return None


def create_header_widget(
    client: LMClient,
    dashboard_id: int,
    customer_name: str,
    ban: str,
    position: WidgetPosition
) -> Optional[int]:
    """
    Create the header text widget for a customer dashboard.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        customer_name: Customer name (will use token)
        ban: BAN number (will use token)
        position: Position tracker

    Returns:
        Widget ID if created, None otherwise
    """
    content = """<div style="font-family: Arial, sans-serif; padding: 10px;">
<h1 style="margin-bottom: 10px;">##CUSTOMER_NAME## – Network Overview</h1>
<p><strong>BAN:</strong> ##BAN##</p>
<p style="margin-top: 15px; color: #666;">
This dashboard shows throughput, interface statistics, BGP (if applicable),
and optical health for the customer's services across the DFW fabric.
</p>
<p style="margin-top: 10px; font-size: 0.9em; color: #888;">
For assistance, contact: <a href="mailto:noc@csquare.com">noc@csquare.com</a>
</p>
</div>"""

    return create_text_widget(
        client, dashboard_id,
        name=f'Customer Overview - ##BAN##',
        content=content,
        position=position,
        width=GRID_COLUMNS,
        height=DEFAULT_TEXT_HEIGHT
    )


def create_section_header(
    client: LMClient,
    dashboard_id: int,
    title: str,
    position: WidgetPosition
) -> Optional[int]:
    """
    Create a section header widget.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        title: Section title
        position: Position tracker

    Returns:
        Widget ID if created, None otherwise
    """
    content = f"""<div style="background-color: #2c3e50; color: white; padding: 8px 15px; border-radius: 4px;">
<h3 style="margin: 0;">{title}</h3>
</div>"""

    return create_text_widget(
        client, dashboard_id,
        name=title,
        content=content,
        position=position,
        width=GRID_COLUMNS,
        height=1
    )


def create_noc_header_widget(
    client: LMClient,
    dashboard_id: int,
    customer_name: str,
    ban: str,
    position: WidgetPosition
) -> Optional[int]:
    """
    Create the header text widget for a NOC dashboard.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        customer_name: Customer name (will use token)
        ban: BAN number (will use token)
        position: Position tracker

    Returns:
        Widget ID if created, None otherwise
    """
    content = """<div style="font-family: Arial, sans-serif; padding: 10px;">
<h1 style="margin-bottom: 5px;">NOC View – ##CUSTOMER_NAME##</h1>
<p style="margin-top: 0;"><strong>BAN:</strong> ##BAN##</p>
<p style="margin-top: 10px; color: #666;">
This dashboard is designed for NOC technicians troubleshooting customer issues.
It shows alerts, errors, discards, and traffic metrics for customer circuits.
</p>
<p style="margin-top: 10px; font-size: 0.9em; color: #888;">
<strong>Color Legend:</strong>
<span style="color: #2ecc71;">● Green = Normal</span> |
<span style="color: #f39c12;">● Yellow = Warning</span> |
<span style="color: #e74c3c;">● Red = Critical</span>
</p>
</div>"""

    return create_text_widget(
        client, dashboard_id,
        name=f'NOC Overview - ##BAN##',
        content=content,
        position=position,
        width=GRID_COLUMNS,
        height=DEFAULT_TEXT_HEIGHT
    )
