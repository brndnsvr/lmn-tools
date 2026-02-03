"""
DOM (Digital Optical Monitoring) graph widget builders for LogicMonitor dashboards.

This module provides functions to create DOM optics-related cgraph widgets:
- Single datapoint DOM graphs (Laser Bias, Module Temp)
- Combined optical power graphs (Rx + Tx power)
- DOM graph builder for multiple interfaces
"""

import logging
import re
from typing import Any

from ..lm_client import LMAPIError, LMClient
from ..lm_helpers import ResolvedInterface
from .common import (
    DEFAULT_GRAPH_HEIGHT,
    WidgetPosition,
)
from .text_widgets import create_section_header

logger = logging.getLogger(__name__)


def create_dom_graph_widget(
    client: LMClient,
    dashboard_id: int,
    interface: ResolvedInterface,
    dom_instance_id: int,
    dom_instance_name: str,
    dom_datasource_id: int,
    datapoint_name: str,
    position: WidgetPosition,
    width: int = 6,
    dom_datasource_full_name: str = "Juniper DOM- (Juniper DOM-)",
) -> int | None:
    """
    Create a DOM optics graph widget for a single datapoint.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        interface: Interface info (for hostname)
        dom_instance_id: DOM datasource instance ID
        dom_instance_name: DOM instance display name
        dom_datasource_id: DOM datasource ID
        datapoint_name: Datapoint to graph (e.g., 'LaserBiasCurrent')
        position: Position tracker
        width: Widget width
        dom_datasource_full_name: Full name of the DOM datasource (DisplayName (name))

    Returns:
        Widget ID if created, None otherwise
    """
    # Map datapoint names to display names and units
    # Using actual Juniper DOM datapoint names
    datapoint_display = {
        "LaserBiasCurrent": ("Laser Bias", "mA"),
        "ModuleTemp": ("Module Temperature", "°C"),
        "RxLaserPower": ("Rx Power", "dBm"),
        "TxLaserOutputPower": ("Tx Power", "dBm"),
    }

    display_name, unit = datapoint_display.get(datapoint_name, (datapoint_name, ""))

    # Extract base port name (strip unit number)
    base_port = re.sub(r"\.\d+$", "", interface.interface_name)

    title = f"{interface.hostname} – DOM – {base_port} – {display_name}"

    # dataPoints with GlobMatchToggle format and display settings
    data_points = [
        {
            "name": "domMetric",
            "dataPointName": datapoint_name,
            "dataSourceFullName": dom_datasource_full_name,
            "instanceName": {"value": dom_instance_name, "isGlob": False},
            "deviceDisplayName": {"value": interface.hostname, "isGlob": False},
            "deviceGroupFullPath": {"value": "*", "isGlob": True},
            "consolidateFunction": "average",
            "display": {
                "option": "custom",
                "legend": display_name,
                "type": "line",
                "color": "#9b59b6",
            },
        }
    ]

    widget_data = {
        "dashboardId": dashboard_id,
        "name": title,
        "type": "cgraph",
        "col": position.col,
        "row": position.row,
        "colSpan": width,
        "rowSpan": DEFAULT_GRAPH_HEIGHT,
        "graphInfo": {
            "verticalLabel": unit or "Value",
            "minValue": 0,
            "aggregate": False,
            "dataPoints": data_points,
        },
        "timescale": "6hour",  # Longer timescale for sparse DOM data
    }

    try:
        response = client.post("/dashboard/widgets", json=widget_data)
        widget_id: int | None = response.get("data", {}).get("id") or response.get("id")
        position.next_col(width)
        logger.debug(f"Created DOM graph widget: {title} -> {widget_id}")
        return widget_id
    except LMAPIError as e:
        logger.error(f"Failed to create DOM graph widget {title}: {e}")
        return None


def create_dom_optical_power_graph(
    client: LMClient,
    dashboard_id: int,
    interface: ResolvedInterface,
    dom_instance_id: int,
    dom_instance_name: str,
    dom_datasource_id: int,
    position: WidgetPosition,
    width: int = 6,
    dom_datasource_full_name: str = "Juniper DOM- (Juniper DOM-)",
) -> int | None:
    """
    Create a combined DOM optical power graph with Rx and Tx power.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        interface: Interface info (for hostname)
        dom_instance_id: DOM datasource instance ID
        dom_instance_name: DOM instance display name
        dom_datasource_id: DOM datasource ID
        position: Position tracker
        width: Widget width
        dom_datasource_full_name: Full name of the DOM datasource (DisplayName (name))

    Returns:
        Widget ID if created, None otherwise
    """
    # Extract base port name (strip unit number)
    base_port = re.sub(r"\.\d+$", "", interface.interface_name)

    title = f"{interface.hostname} – DOM – {base_port} – Optical Power"

    # Combined Rx and Tx power datapoints
    data_points = [
        {
            "name": "rxPower",
            "dataPointName": "RxLaserPower",
            "dataSourceFullName": dom_datasource_full_name,
            "instanceName": {"value": dom_instance_name, "isGlob": False},
            "deviceDisplayName": {"value": interface.hostname, "isGlob": False},
            "deviceGroupFullPath": {"value": "*", "isGlob": True},
            "consolidateFunction": "average",
            "display": {
                "option": "custom",
                "legend": "Rx Power",
                "type": "line",
                "color": "#2ecc71",  # Green for Rx
            },
        },
        {
            "name": "txPower",
            "dataPointName": "TxLaserOutputPower",
            "dataSourceFullName": dom_datasource_full_name,
            "instanceName": {"value": dom_instance_name, "isGlob": False},
            "deviceDisplayName": {"value": interface.hostname, "isGlob": False},
            "deviceGroupFullPath": {"value": "*", "isGlob": True},
            "consolidateFunction": "average",
            "display": {
                "option": "custom",
                "legend": "Tx Power",
                "type": "line",
                "color": "#3498db",  # Blue for Tx
            },
        },
    ]

    widget_data = {
        "dashboardId": dashboard_id,
        "name": title,
        "type": "cgraph",
        "col": position.col,
        "row": position.row,
        "colSpan": width,
        "rowSpan": DEFAULT_GRAPH_HEIGHT,
        "graphInfo": {"verticalLabel": "dBm", "aggregate": False, "dataPoints": data_points},
        "timescale": "6hour",  # Longer timescale for sparse DOM data
    }

    try:
        response = client.post("/dashboard/widgets", json=widget_data)
        widget_id: int | None = response.get("data", {}).get("id") or response.get("id")
        position.next_col(width)
        logger.debug(f"Created DOM optical power graph: {title} -> {widget_id}")
        return widget_id
    except LMAPIError as e:
        logger.error(f"Failed to create DOM optical power graph {title}: {e}")
        return None


def build_dom_graphs(
    client: LMClient,
    dashboard_id: int,
    dom_interfaces: list[
        tuple[Any, ...]
    ],  # List of (interface, instance_id, instance_name, datasource_id, datasource_full_name)
    position: WidgetPosition,
) -> int:
    """
    Create DOM optics graphs for leaf interfaces.

    Creates 3 graphs per interface:
    - Laser Bias (solo)
    - Module Temperature (solo)
    - Optical Power (combined Rx + Tx)

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        dom_interfaces: List of tuples with DOM interface info
        position: Position tracker

    Returns:
        Number of widgets created
    """
    if not dom_interfaces:
        return 0

    # Create section header
    create_section_header(client, dashboard_id, "DOM Optics – Leaf Interfaces", position)
    widgets_created = 1

    # Solo DOM datapoints (Laser Bias and Module Temp)
    solo_datapoints = [
        "LaserBiasCurrent",
        "ModuleTemp",
    ]

    for (
        interface,
        dom_instance_id,
        dom_instance_name,
        dom_datasource_id,
        dom_ds_full_name,
    ) in dom_interfaces:
        # Create solo graphs for Laser Bias and Module Temp
        for dp_name in solo_datapoints:
            widget_id = create_dom_graph_widget(
                client,
                dashboard_id,
                interface,
                dom_instance_id,
                dom_instance_name,
                dom_datasource_id,
                dp_name,
                position,
                width=6,
                dom_datasource_full_name=dom_ds_full_name,
            )
            if widget_id:
                widgets_created += 1

        # Create combined Optical Power graph (Rx + Tx)
        widget_id = create_dom_optical_power_graph(
            client,
            dashboard_id,
            interface,
            dom_instance_id,
            dom_instance_name,
            dom_datasource_id,
            position,
            width=6,
            dom_datasource_full_name=dom_ds_full_name,
        )
        if widget_id:
            widgets_created += 1

        # Start new row after each interface's DOM graphs (3 graphs at width 6 = 18 cols)
        if position.col > 0:
            position.next_row(DEFAULT_GRAPH_HEIGHT)

    return widgets_created
