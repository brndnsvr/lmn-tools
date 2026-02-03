"""
NOC (Network Operations Center) widget builders for LogicMonitor dashboards.

This module provides functions to create NOC-type widgets:
- Interface statistics tables (NOC type)
- BGP peer tables (NOC type)

These widgets use the 'noc' widget type which displays alert status
with colored indicators.
"""

import logging

from ..lm_client import LMAPIError, LMClient
from ..lm_helpers import ResolvedBGPPeer, ResolvedInterface
from .common import (
    DEFAULT_TABLE_HEIGHT,
    GRID_COLUMNS,
    WidgetPosition,
)

logger = logging.getLogger(__name__)


def create_interface_table_widget(
    client: LMClient,
    dashboard_id: int,
    interfaces: list[ResolvedInterface],
    datasource_name: str,
    position: WidgetPosition,
    datasource_display_name: str = "Interfaces-",
) -> int | None:
    """
    Create an interface statistics table widget using deviceNOC widget type.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        interfaces: List of resolved interfaces to include
        datasource_name: Interface datasource name
        position: Position tracker
        datasource_display_name: Display name of the interface datasource

    Returns:
        Widget ID if created, None otherwise
    """
    if not interfaces:
        logger.warning("No interfaces to include in table widget")
        return None

    # Build items for each interface - using NOC widget format
    items = []
    for iface in interfaces:
        if not iface.include_in_table:
            continue

        item = {
            "type": "device",  # Required for NOC widget items
            "deviceGroupFullPath": "*",
            "deviceDisplayName": iface.hostname,
            "dataSourceDisplayName": datasource_display_name,
            "instanceName": iface.instance_name,
            "dataPointName": "*",
            "groupBy": "instance",
            "name": f"{iface.hostname} - {iface.interface_name}",
        }
        items.append(item)

    if not items:
        logger.warning("No interfaces to include in table widget")
        return None

    # Build widget data using 'noc' type
    widget_data = {
        "dashboardId": dashboard_id,
        "name": "Interface Statistics – BAN ##BAN##",
        "type": "noc",
        "col": position.col,
        "row": position.row,
        "colSpan": GRID_COLUMNS,
        "rowSpan": DEFAULT_TABLE_HEIGHT + 2,
        "items": items,
        "displaySettings": {"displayAs": "table"},
        "displayWarnAlert": True,
        "displayErrorAlert": True,
        "displayCriticalAlert": True,
        "ackChecked": True,
        "sdtChecked": True,
    }

    try:
        response = client.post("/dashboard/widgets", json=widget_data)
        widget_id: int | None = response.get("data", {}).get("id") or response.get("id")
        position.next_row(DEFAULT_TABLE_HEIGHT + 2)
        logger.info(f"Created interface table widget -> {widget_id}")
        return widget_id
    except LMAPIError as e:
        logger.error(f"Failed to create interface table widget: {e}")
        return None


def create_bgp_table_widget(
    client: LMClient,
    dashboard_id: int,
    bgp_peers: list[ResolvedBGPPeer],
    position: WidgetPosition,
    bgp_datasource_display_name: str = "BGP-",
) -> int | None:
    """
    Create a BGP peers table widget.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        bgp_peers: List of resolved BGP peers
        position: Position tracker
        bgp_datasource_display_name: Display name of the BGP datasource

    Returns:
        Widget ID if created, None otherwise
    """
    if not bgp_peers:
        logger.debug("No BGP peers to include in table")
        return None

    # Build items for each peer using NOC widget format
    items = []
    for peer in bgp_peers:
        item = {
            "type": "device",  # Required for NOC widget items
            "deviceGroupFullPath": "*",
            "deviceDisplayName": peer.hostname,
            "dataSourceDisplayName": bgp_datasource_display_name,
            "instanceName": peer.neighbor_ip,
            "dataPointName": "*",
            "groupBy": "instance",
            "name": f"{peer.hostname} - {peer.neighbor_ip}",
        }
        items.append(item)

    widget_data = {
        "dashboardId": dashboard_id,
        "name": "BGP Peers – BAN ##BAN##",
        "type": "noc",
        "col": position.col,
        "row": position.row,
        "colSpan": GRID_COLUMNS,
        "rowSpan": DEFAULT_TABLE_HEIGHT,
        "items": items,
        "displaySettings": {"displayAs": "table"},
        "displayWarnAlert": True,
        "displayErrorAlert": True,
        "displayCriticalAlert": True,
        "ackChecked": True,
        "sdtChecked": True,
    }

    try:
        response = client.post("/dashboard/widgets", json=widget_data)
        widget_id: int | None = response.get("data", {}).get("id") or response.get("id")
        position.next_row(DEFAULT_TABLE_HEIGHT)
        logger.info(f"Created BGP table widget -> {widget_id}")
        return widget_id
    except LMAPIError as e:
        logger.error(f"Failed to create BGP table widget: {e}")
        return None
