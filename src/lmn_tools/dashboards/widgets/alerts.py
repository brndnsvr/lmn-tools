"""
Alert-focused widget builders for LogicMonitor NOC dashboards.

This module provides functions to create NOC alert widgets:
- Resource alerts (device-level)
- Interface alerts (instance-level)
- Errors and discards tables
- Discard percentage graphs

These widgets are designed for NOC technicians troubleshooting customer issues.
"""

import re
import logging
from typing import Optional

from ..lm_client import LMClient, LMAPIError
from ..lm_helpers import ResolvedInterface
from .common import (
    WidgetPosition,
    GRID_COLUMNS,
    DEFAULT_TABLE_HEIGHT,
)

logger = logging.getLogger(__name__)


def create_resource_alerts_widget(
    client: LMClient,
    dashboard_id: int,
    devices: list[str],
    position: WidgetPosition
) -> Optional[int]:
    """
    Create NOC grid widget showing alerts for customer devices.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        devices: List of device hostnames
        position: Position tracker

    Returns:
        Widget ID if created, None otherwise
    """
    if not devices:
        logger.warning("No devices for resource alerts widget")
        return None

    items = []
    for hostname in devices:
        items.append({
            'type': 'device',
            'deviceGroupFullPath': '*',
            'deviceDisplayName': hostname,
            'dataSourceDisplayName': '*',
            'instanceName': '*',
            'dataPointName': '*',
            'groupBy': 'device',
            'name': hostname
        })

    widget_data = {
        'dashboardId': dashboard_id,
        'name': 'Resource Alerts – Customer Devices',
        'type': 'noc',
        'col': position.col,
        'row': position.row,
        'colSpan': GRID_COLUMNS,
        'rowSpan': 3,
        'displaySettings': {
            'showTypeIcon': True,
            'displayAs': 'grid'
        },
        'displayWarnAlert': True,
        'displayErrorAlert': True,
        'displayCriticalAlert': True,
        'ackChecked': True,
        'sdtChecked': True,
        'sortBy': 'alertSeverity',
        'displayColumn': 4,
        'items': items
    }

    try:
        response = client.post('/dashboard/widgets', json=widget_data)
        widget_id = response.get('data', {}).get('id') or response.get('id')
        position.next_row(3)
        logger.info(f"Created resource alerts widget -> {widget_id}")
        return widget_id
    except LMAPIError as e:
        logger.error(f"Failed to create resource alerts widget: {e}")
        return None


def create_interface_alerts_widget(
    client: LMClient,
    dashboard_id: int,
    interfaces: list[ResolvedInterface],
    position: WidgetPosition,
    datasource_display_name: str = 'Interfaces-'
) -> Optional[int]:
    """
    Create NOC grid showing alerts for customer interfaces.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        interfaces: List of resolved interfaces
        position: Position tracker
        datasource_display_name: Display name of the interface datasource

    Returns:
        Widget ID if created, None otherwise
    """
    if not interfaces:
        logger.warning("No interfaces for interface alerts widget")
        return None

    items = []
    for iface in interfaces:
        items.append({
            'type': 'device',
            'deviceGroupFullPath': '*',
            'deviceDisplayName': iface.hostname,
            'dataSourceDisplayName': datasource_display_name,
            'instanceName': iface.instance_name,
            'dataPointName': '*',
            'groupBy': 'instance',
            'name': f'{iface.hostname} - {iface.interface_name}'
        })

    widget_data = {
        'dashboardId': dashboard_id,
        'name': 'Interface Alerts – Customer Circuits',
        'type': 'noc',
        'col': position.col,
        'row': position.row,
        'colSpan': GRID_COLUMNS,
        'rowSpan': 3,
        'displaySettings': {
            'showTypeIcon': True,
            'displayAs': 'grid'
        },
        'displayWarnAlert': True,
        'displayErrorAlert': True,
        'displayCriticalAlert': True,
        'ackChecked': True,
        'sdtChecked': True,
        'sortBy': 'alertSeverity',
        'displayColumn': 4,
        'items': items
    }

    try:
        response = client.post('/dashboard/widgets', json=widget_data)
        widget_id = response.get('data', {}).get('id') or response.get('id')
        position.next_row(3)
        logger.info(f"Created interface alerts widget -> {widget_id}")
        return widget_id
    except LMAPIError as e:
        logger.error(f"Failed to create interface alerts widget: {e}")
        return None


def create_errors_discards_table(
    client: LMClient,
    dashboard_id: int,
    interfaces: list[ResolvedInterface],
    position: WidgetPosition
) -> Optional[int]:
    """
    Create dynamicTable showing error/discard metrics for troubleshooting.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        interfaces: List of resolved interfaces
        position: Position tracker

    Returns:
        Widget ID if created, None otherwise
    """
    if not interfaces:
        logger.warning("No interfaces for errors/discards table")
        return None

    # Build rows for each interface
    rows = []
    for iface in interfaces:
        rows.append({
            'label': f'{iface.hostname} - {iface.interface_name}',
            'groupFullPath': '*',
            'deviceDisplayName': iface.hostname,
            'instanceName': iface.instance_name
        })

    # Get the dataSourceFullName from the first interface
    first_iface = interfaces[0]
    ds_full_name = f"{first_iface.datasource_display_name} ({first_iface.datasource_name})"

    widget_data = {
        'dashboardId': dashboard_id,
        'name': 'Interface Errors & Discards',
        'type': 'dynamicTable',
        'col': position.col,
        'row': position.row,
        'colSpan': GRID_COLUMNS,
        'rowSpan': DEFAULT_TABLE_HEIGHT,
        'dataSourceFullName': ds_full_name,
        'columns': [
            {
                'columnName': 'In Discards',
                'dataPointName': 'InDiscards',
                'unitLabel': ' pkts/s',
                'enableForecast': False,
                'roundingDecimal': 2,
                'rpn': '',
                'displayType': 'raw',
                'colorThresholds': [
                    {'relation': '>', 'threshold': 100.0, 'level': 2},
                    {'relation': '>', 'threshold': 1000.0, 'level': 3}
                ],
                'maxValue': 10000.0,
                'minValue': 0.0
            },
            {
                'columnName': 'Out Discards',
                'dataPointName': 'OutDiscards',
                'unitLabel': ' pkts/s',
                'enableForecast': False,
                'roundingDecimal': 2,
                'rpn': '',
                'displayType': 'raw',
                'colorThresholds': [
                    {'relation': '>', 'threshold': 100.0, 'level': 2},
                    {'relation': '>', 'threshold': 1000.0, 'level': 3}
                ],
                'maxValue': 10000.0,
                'minValue': 0.0
            },
            {
                'columnName': 'In Errors',
                'dataPointName': 'InErrors',
                'unitLabel': ' pkts/s',
                'enableForecast': False,
                'roundingDecimal': 2,
                'rpn': '',
                'displayType': 'raw',
                'colorThresholds': [
                    {'relation': '>', 'threshold': 10.0, 'level': 2},
                    {'relation': '>', 'threshold': 100.0, 'level': 3}
                ],
                'maxValue': 1000.0,
                'minValue': 0.0
            },
            {
                'columnName': 'Out Errors',
                'dataPointName': 'OutErrors',
                'unitLabel': ' pkts/s',
                'enableForecast': False,
                'roundingDecimal': 2,
                'rpn': '',
                'displayType': 'raw',
                'colorThresholds': [
                    {'relation': '>', 'threshold': 10.0, 'level': 2},
                    {'relation': '>', 'threshold': 100.0, 'level': 3}
                ],
                'maxValue': 1000.0,
                'minValue': 0.0
            },
            {
                'columnName': 'In Discard %',
                'dataPointName': 'InDiscardPercent',
                'unitLabel': '%',
                'enableForecast': False,
                'roundingDecimal': 2,
                'rpn': '',
                'displayType': 'raw',
                'colorThresholds': [
                    {'relation': '>', 'threshold': 1.0, 'level': 2},
                    {'relation': '>', 'threshold': 5.0, 'level': 3}
                ],
                'maxValue': 100.0,
                'minValue': 0.0
            },
            {
                'columnName': 'Out Discard %',
                'dataPointName': 'OutDiscardPercent',
                'unitLabel': '%',
                'enableForecast': False,
                'roundingDecimal': 2,
                'rpn': '',
                'displayType': 'raw',
                'colorThresholds': [
                    {'relation': '>', 'threshold': 1.0, 'level': 2},
                    {'relation': '>', 'threshold': 5.0, 'level': 3}
                ],
                'maxValue': 100.0,
                'minValue': 0.0
            }
        ],
        'rows': rows,
        'displaySettings': {
            'columns': [
                {'visible': True, 'columnLabel': 'Interface', 'columnSize': 280, 'columnKey': 'device-name-1452842526600'},
                {'visible': True, 'columnLabel': 'In Discards', 'columnSize': 100, 'columnKey': '0'},
                {'visible': True, 'columnLabel': 'Out Discards', 'columnSize': 100, 'columnKey': '1'},
                {'visible': True, 'columnLabel': 'In Errors', 'columnSize': 90, 'columnKey': '2'},
                {'visible': True, 'columnLabel': 'Out Errors', 'columnSize': 90, 'columnKey': '3'},
                {'visible': True, 'columnLabel': 'In Discard %', 'columnSize': 100, 'columnKey': '4'},
                {'visible': True, 'columnLabel': 'Out Discard %', 'columnSize': 100, 'columnKey': '5'}
            ],
            'pageSize': '25'
        },
        'topX': -1,
        'sortOrder': 'descending'
    }

    try:
        response = client.post('/dashboard/widgets', json=widget_data)
        widget_id = response.get('data', {}).get('id') or response.get('id')
        position.next_row(DEFAULT_TABLE_HEIGHT)
        logger.info(f"Created errors/discards table widget -> {widget_id}")
        return widget_id
    except LMAPIError as e:
        logger.error(f"Failed to create errors/discards table widget: {e}")
        return None


def create_discard_percentage_graph(
    client: LMClient,
    dashboard_id: int,
    interfaces: list[ResolvedInterface],
    position: WidgetPosition
) -> Optional[int]:
    """
    Create graph showing discard percentages over time for troubleshooting.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        interfaces: List of resolved interfaces
        position: Position tracker

    Returns:
        Widget ID if created, None otherwise
    """
    if not interfaces:
        logger.warning("No interfaces for discard percentage graph")
        return None

    # Color palette for different interfaces
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e91e63', '#00bcd4']

    data_points = []
    for i, iface in enumerate(interfaces):
        # Sanitize name for datapoint name field
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', f'{iface.hostname}_{iface.interface_name}')
        color = colors[i % len(colors)]

        # Build dataSourceFullName from resolved interface info
        ds_full_name = f"{iface.datasource_display_name} ({iface.datasource_name})"

        # In Discard %
        data_points.append({
            'name': f'in_discard_{safe_name}',
            'dataPointName': 'InDiscardPercent',
            'dataSourceFullName': ds_full_name,
            'instanceName': {'value': iface.instance_name, 'isGlob': False},
            'deviceDisplayName': {'value': iface.hostname, 'isGlob': False},
            'deviceGroupFullPath': {'value': '*', 'isGlob': True},
            'consolidateFunction': 'average',
            'display': {
                'option': 'custom',
                'legend': f'{iface.hostname}-{iface.interface_name} In',
                'type': 'line',
                'color': color
            }
        })

    widget_data = {
        'dashboardId': dashboard_id,
        'name': 'Discard Percentage - All Interfaces',
        'type': 'cgraph',
        'col': position.col,
        'row': position.row,
        'colSpan': GRID_COLUMNS,
        'rowSpan': 5,
        'graphInfo': {
            'verticalLabel': '%',
            'minValue': 0,
            'maxValue': 10,
            'aggregate': False,
            'dataPoints': data_points
        },
        'timescale': '4hour'
    }

    try:
        response = client.post('/dashboard/widgets', json=widget_data)
        widget_id = response.get('data', {}).get('id') or response.get('id')
        position.next_row(5)
        logger.info(f"Created discard percentage graph -> {widget_id}")
        return widget_id
    except LMAPIError as e:
        logger.error(f"Failed to create discard percentage graph: {e}")
        return None
