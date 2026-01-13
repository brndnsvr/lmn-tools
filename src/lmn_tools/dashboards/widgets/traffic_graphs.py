"""
Traffic graph widget builders for LogicMonitor dashboards.

This module provides functions to create traffic-related cgraph widgets:
- Single interface traffic graphs
- Consolidated traffic graphs (multiple interfaces)
- Packet transmission graphs
- Traffic graphs split by interface type
"""

import logging
import re

from ..lm_client import LMAPIError, LMClient
from ..lm_helpers import ResolvedInterface
from .common import (
    DEFAULT_GRAPH_HEIGHT,
    DEFAULT_WIDGET_WIDTH,
    GRID_COLUMNS,
    INTERFACE_COLORS,
    WidgetPosition,
    get_interface_type,
)
from .text_widgets import create_section_header

logger = logging.getLogger(__name__)


def create_traffic_graph_widget(
    client: LMClient,
    dashboard_id: int,
    interface: ResolvedInterface,
    position: WidgetPosition,
    width: int = DEFAULT_WIDGET_WIDTH,
    datasource_full_name: str = 'Interfaces- (snmpIf-)'
) -> int | None:
    """
    Create a traffic throughput graph widget for an interface.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        interface: Resolved interface
        position: Position tracker
        width: Widget width
        datasource_full_name: Full name of the interface datasource

    Returns:
        Widget ID if created, None otherwise
    """
    # Widget title
    title = f'{interface.hostname} – {interface.interface_name}'
    if interface.alias:
        title += f' – {interface.alias}'

    # dataPoints with GlobMatchToggle format and display settings
    data_points = [
        {
            'name': 'inMbps',
            'dataPointName': 'InMbps',
            'dataSourceFullName': datasource_full_name,
            'instanceName': {'value': interface.instance_name, 'isGlob': False},
            'deviceDisplayName': {'value': interface.hostname, 'isGlob': False},
            'deviceGroupFullPath': {'value': '*', 'isGlob': True},
            'consolidateFunction': 'average',
            'display': {
                'option': 'custom',
                'legend': f'{interface.interface_name} In',
                'type': 'line',
                'color': '#2ecc71'
            }
        },
        {
            'name': 'outMbps',
            'dataPointName': 'OutMbps',
            'dataSourceFullName': datasource_full_name,
            'instanceName': {'value': interface.instance_name, 'isGlob': False},
            'deviceDisplayName': {'value': interface.hostname, 'isGlob': False},
            'deviceGroupFullPath': {'value': '*', 'isGlob': True},
            'consolidateFunction': 'average',
            'display': {
                'option': 'custom',
                'legend': f'{interface.interface_name} Out',
                'type': 'line',
                'color': '#3498db'
            }
        }
    ]

    widget_data = {
        'dashboardId': dashboard_id,
        'name': title,
        'type': 'cgraph',
        'col': position.col,
        'row': position.row,
        'colSpan': width,
        'rowSpan': DEFAULT_GRAPH_HEIGHT,
        'graphInfo': {
            'verticalLabel': 'Mbps',
            'minValue': 0,
            'aggregate': False,
            'dataPoints': data_points
        },
        'timescale': '2hour'
    }

    try:
        response = client.post('/dashboard/widgets', json=widget_data)
        widget_id: int | None = response.get('data', {}).get('id') or response.get('id')
        position.next_col(width)
        logger.debug(f"Created traffic graph widget: {title} -> {widget_id}")
        return widget_id
    except LMAPIError as e:
        logger.error(f"Failed to create traffic graph widget {title}: {e}")
        return None


def create_consolidated_traffic_graph(
    client: LMClient,
    dashboard_id: int,
    interfaces: list[ResolvedInterface],
    position: WidgetPosition,
    title: str = 'Bandwidth Utilization - All Interfaces',
    interface_type_filter: str | None = None
) -> int | None:
    """
    Create a consolidated bandwidth utilization graph with filtered interfaces.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        interfaces: List of resolved interfaces to include
        position: Position tracker
        title: Widget title
        interface_type_filter: Filter by interface type ('internet', 'cloudconnect', 'access', or None for all)

    Returns:
        Widget ID if created, None otherwise
    """
    # Filter interfaces
    traffic_interfaces = [i for i in interfaces if i.include_in_traffic_graphs]

    # Apply interface type filter if specified
    if interface_type_filter:
        traffic_interfaces = [
            i for i in traffic_interfaces
            if get_interface_type(i.role, i.interface_name, i.alias) == interface_type_filter
        ]

    if not traffic_interfaces:
        logger.debug(f"No interfaces for traffic graph '{title}' (filter: {interface_type_filter})")
        return None

    # Build dataPoints for all interfaces
    data_points = []
    for idx, iface in enumerate(traffic_interfaces):
        color_idx = idx % len(INTERFACE_COLORS)
        in_color, out_color = INTERFACE_COLORS[color_idx]

        # Build dataSourceFullName from resolved interface info: "DisplayName (internal_name)"
        ds_full_name = f"{iface.datasource_display_name} ({iface.datasource_name})"

        # Sanitize name to only a-zA-Z0-9_ (only for the 'name' field, not instanceName)
        safe_hostname = re.sub(r'[^a-zA-Z0-9_]', '_', iface.hostname)
        safe_iface = re.sub(r'[^a-zA-Z0-9_]', '_', iface.interface_name)

        # Log the instance name being used for debugging
        logger.debug(
            f"Traffic graph '{title}' datapoint: hostname={iface.hostname}, "
            f"interface_name={iface.interface_name}, instance_name={iface.instance_name}, "
            f"type={get_interface_type(iface.role, iface.interface_name, iface.alias)}"
        )

        # In datapoint
        data_points.append({
            'name': f'in_{safe_hostname}_{safe_iface}',
            'dataPointName': 'InMbps',
            'dataSourceFullName': ds_full_name,
            'instanceName': {'value': iface.instance_name, 'isGlob': False},
            'deviceDisplayName': {'value': iface.hostname, 'isGlob': False},
            'deviceGroupFullPath': {'value': '*', 'isGlob': True},
            'consolidateFunction': 'average',
            'display': {
                'option': 'custom',
                'legend': f'{iface.hostname}-{iface.interface_name} In',
                'type': 'line',
                'color': in_color
            }
        })

        # Out datapoint
        data_points.append({
            'name': f'out_{safe_hostname}_{safe_iface}',
            'dataPointName': 'OutMbps',
            'dataSourceFullName': ds_full_name,
            'instanceName': {'value': iface.instance_name, 'isGlob': False},
            'deviceDisplayName': {'value': iface.hostname, 'isGlob': False},
            'deviceGroupFullPath': {'value': '*', 'isGlob': True},
            'consolidateFunction': 'average',
            'display': {
                'option': 'custom',
                'legend': f'{iface.hostname}-{iface.interface_name} Out',
                'type': 'line',
                'color': out_color
            }
        })

    widget_data = {
        'dashboardId': dashboard_id,
        'name': title,
        'type': 'cgraph',
        'col': position.col,
        'row': position.row,
        'colSpan': GRID_COLUMNS,
        'rowSpan': DEFAULT_GRAPH_HEIGHT + 2,  # Taller to accommodate legend
        'graphInfo': {
            'verticalLabel': 'Mbps',
            'minValue': 0,
            'aggregate': False,
            'dataPoints': data_points
        },
        'timescale': '2hour'
    }

    try:
        response = client.post('/dashboard/widgets', json=widget_data)
        widget_id: int | None = response.get('data', {}).get('id') or response.get('id')
        position.next_row(DEFAULT_GRAPH_HEIGHT + 2)
        logger.info(f"Created bandwidth graph '{title}' -> {widget_id}")
        return widget_id
    except LMAPIError as e:
        logger.error(f"Failed to create bandwidth graph '{title}': {e}")
        return None


def create_consolidated_packet_graph(
    client: LMClient,
    dashboard_id: int,
    interfaces: list[ResolvedInterface],
    position: WidgetPosition,
    title: str = 'Packet Transmission - All Interfaces',
    interface_type_filter: str | None = None
) -> int | None:
    """
    Create a consolidated packet transmission graph with filtered interfaces.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        interfaces: List of resolved interfaces to include
        position: Position tracker
        title: Widget title
        interface_type_filter: Filter by interface type ('internet', 'cloudconnect', 'access', or None for all)

    Returns:
        Widget ID if created, None otherwise
    """
    # Filter interfaces
    traffic_interfaces = [i for i in interfaces if i.include_in_traffic_graphs]

    # Apply interface type filter if specified
    if interface_type_filter:
        traffic_interfaces = [
            i for i in traffic_interfaces
            if get_interface_type(i.role, i.interface_name, i.alias) == interface_type_filter
        ]

    if not traffic_interfaces:
        logger.debug(f"No interfaces for packet graph '{title}' (filter: {interface_type_filter})")
        return None

    # Build dataPoints for all interfaces
    data_points = []
    for idx, iface in enumerate(traffic_interfaces):
        color_idx = idx % len(INTERFACE_COLORS)
        in_color, out_color = INTERFACE_COLORS[color_idx]

        # Build dataSourceFullName from resolved interface info: "DisplayName (internal_name)"
        ds_full_name = f"{iface.datasource_display_name} ({iface.datasource_name})"

        # Sanitize name to only a-zA-Z0-9_
        safe_hostname = re.sub(r'[^a-zA-Z0-9_]', '_', iface.hostname)
        safe_iface = re.sub(r'[^a-zA-Z0-9_]', '_', iface.interface_name)

        # In packets datapoint
        data_points.append({
            'name': f'inpkts_{safe_hostname}_{safe_iface}',
            'dataPointName': 'InUcastPkts',
            'dataSourceFullName': ds_full_name,
            'instanceName': {'value': iface.instance_name, 'isGlob': False},
            'deviceDisplayName': {'value': iface.hostname, 'isGlob': False},
            'deviceGroupFullPath': {'value': '*', 'isGlob': True},
            'consolidateFunction': 'average',
            'display': {
                'option': 'custom',
                'legend': f'{iface.hostname}-{iface.interface_name} In',
                'type': 'line',
                'color': in_color
            }
        })

        # Out packets datapoint
        data_points.append({
            'name': f'outpkts_{safe_hostname}_{safe_iface}',
            'dataPointName': 'OutUcastPkts',
            'dataSourceFullName': ds_full_name,
            'instanceName': {'value': iface.instance_name, 'isGlob': False},
            'deviceDisplayName': {'value': iface.hostname, 'isGlob': False},
            'deviceGroupFullPath': {'value': '*', 'isGlob': True},
            'consolidateFunction': 'average',
            'display': {
                'option': 'custom',
                'legend': f'{iface.hostname}-{iface.interface_name} Out',
                'type': 'line',
                'color': out_color
            }
        })

    widget_data = {
        'dashboardId': dashboard_id,
        'name': title,
        'type': 'cgraph',
        'col': position.col,
        'row': position.row,
        'colSpan': GRID_COLUMNS,
        'rowSpan': DEFAULT_GRAPH_HEIGHT + 2,  # Taller to accommodate legend
        'graphInfo': {
            'verticalLabel': 'Packets/sec',
            'minValue': 0,
            'aggregate': False,
            'dataPoints': data_points
        },
        'timescale': '2hour'
    }

    try:
        response = client.post('/dashboard/widgets', json=widget_data)
        widget_id: int | None = response.get('data', {}).get('id') or response.get('id')
        position.next_row(DEFAULT_GRAPH_HEIGHT + 2)
        logger.info(f"Created packet graph '{title}' -> {widget_id}")
        return widget_id
    except LMAPIError as e:
        logger.error(f"Failed to create packet graph '{title}': {e}")
        return None


def build_traffic_graphs_by_type(
    client: LMClient,
    dashboard_id: int,
    interfaces: list[ResolvedInterface],
    position: WidgetPosition
) -> int:
    """
    Create traffic graphs split by interface type.

    Creates separate bandwidth and packet graphs for each interface type:
    - Internet Traffic (router devices with irb interfaces)
    - CloudConnect Traffic (router devices with ae100/ae110/ae120 interfaces)
    - Access Port Traffic (leaf devices)

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        interfaces: List of resolved interfaces
        position: Position tracker

    Returns:
        Number of widgets created
    """
    traffic_interfaces = [i for i in interfaces if i.include_in_traffic_graphs]
    if not traffic_interfaces:
        return 0

    widgets_created = 0

    # Define the graph types to create
    graph_configs = [
        ('internet', 'Internet Traffic - All Sites', 'Internet Packets - All Sites'),
        ('cloudconnect', 'CloudConnect Traffic', 'CloudConnect Packets'),
        ('access', 'Access Port Traffic', 'Access Port Packets'),
    ]

    for interface_type, bandwidth_title, packet_title in graph_configs:
        # Check if there are any interfaces of this type
        type_interfaces = [
            i for i in traffic_interfaces
            if get_interface_type(i.role, i.interface_name, i.alias) == interface_type
        ]

        if not type_interfaces:
            logger.debug(f"No {interface_type} interfaces, skipping graphs")
            continue

        # Create section header for this interface type
        section_title = bandwidth_title.replace(' Traffic', ' Traffic Overview')
        if interface_type == 'access':
            section_title = 'Access Port Traffic Overview'
        create_section_header(client, dashboard_id, section_title, position)
        widgets_created += 1

        # Create bandwidth graph for this type
        widget_id = create_consolidated_traffic_graph(
            client, dashboard_id, interfaces, position,
            title=bandwidth_title,
            interface_type_filter=interface_type
        )
        if widget_id:
            widgets_created += 1

        # Create packet graph for this type
        widget_id = create_consolidated_packet_graph(
            client, dashboard_id, interfaces, position,
            title=packet_title,
            interface_type_filter=interface_type
        )
        if widget_id:
            widgets_created += 1

    return widgets_created


def build_traffic_graphs_by_device(
    client: LMClient,
    dashboard_id: int,
    interfaces: list[ResolvedInterface],
    position: WidgetPosition
) -> int:
    """
    Create consolidated traffic graphs for all interfaces (legacy function).

    Creates two full-width graphs:
    1. Bandwidth Utilization - All Interfaces (InMbps/OutMbps)
    2. Packet Transmission - All Interfaces (InUcastPkts/OutUcastPkts)

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        interfaces: List of resolved interfaces
        position: Position tracker

    Returns:
        Number of widgets created
    """
    traffic_interfaces = [i for i in interfaces if i.include_in_traffic_graphs]
    if not traffic_interfaces:
        return 0

    widgets_created = 0

    # Create section header for traffic graphs
    create_section_header(client, dashboard_id, 'Traffic Overview - All Interfaces', position)
    widgets_created += 1

    # Create consolidated bandwidth graph
    widget_id = create_consolidated_traffic_graph(client, dashboard_id, interfaces, position)
    if widget_id:
        widgets_created += 1

    # Create consolidated packet graph
    widget_id = create_consolidated_packet_graph(client, dashboard_id, interfaces, position)
    if widget_id:
        widgets_created += 1

    return widgets_created
