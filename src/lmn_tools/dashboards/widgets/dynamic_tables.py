"""
Dynamic table widget builders for LogicMonitor dashboards.

This module provides functions to create dynamicTable widgets:
- BGP statistics tables with detailed metrics
- Other metric tables with custom columns and thresholds

The dynamicTable widget type allows for custom columns with RPN expressions,
color thresholds, and various display options.
"""

import logging
from typing import Optional

from ..lm_client import LMClient, LMAPIError
from ..lm_helpers import ResolvedBGPPeer
from .common import (
    WidgetPosition,
    GRID_COLUMNS,
    DEFAULT_TABLE_HEIGHT,
)

logger = logging.getLogger(__name__)


def create_bgp_statistics_widget(
    client: LMClient,
    dashboard_id: int,
    bgp_peers: list[ResolvedBGPPeer],
    position: WidgetPosition,
    bgp_datasource_full_name: str = 'BGP- (BGP-)'
) -> Optional[int]:
    """
    Create a BGP statistics table widget using dynamicTable type.

    Shows detailed BGP metrics including:
    - Established Time (converted to hours)
    - Peer State (with critical alert if not established)
    - PeerRestart (converted to hours)
    - Peer In Updates
    - Peer Out Updates

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID
        bgp_peers: List of resolved BGP peers
        position: Position tracker
        bgp_datasource_full_name: Full name of the BGP datasource (DisplayName (name))

    Returns:
        Widget ID if created, None otherwise
    """
    if not bgp_peers:
        logger.debug("No BGP peers to include in statistics table")
        return None

    # Build rows for each peer
    # Instance name needs BGP- prefix (matches LM instance name format)
    rows = []
    for peer in bgp_peers:
        rows.append({
            'label': f'{peer.hostname} - {peer.neighbor_ip}',
            'groupFullPath': '*',
            'deviceDisplayName': peer.hostname,
            'instanceName': f'BGP-{peer.neighbor_ip}'
        })

    widget_data = {
        'dashboardId': dashboard_id,
        'name': 'BGP Statistics – BAN ##BAN##',
        'type': 'dynamicTable',
        'col': position.col,
        'row': position.row,
        'colSpan': GRID_COLUMNS,
        'rowSpan': DEFAULT_TABLE_HEIGHT,
        'dataSourceFullName': bgp_datasource_full_name,
        'columns': [
            {
                'columnName': 'Established',
                'dataPointName': 'EstablishedTime',
                'unitLabel': ' hrs',
                'enableForecast': False,
                'roundingDecimal': 2,
                'rpn': 'EstablishedTime/3600',
                'displayType': 'raw',
                'colorThresholds': [],
                'maxValue': 100000.0,
                'minValue': 0.0
            },
            {
                'columnName': 'Peer State',
                'dataPointName': 'PeerState',
                'unitLabel': '',
                'enableForecast': False,
                'roundingDecimal': 0,
                'rpn': '',
                'displayType': 'raw',
                'colorThresholds': [
                    {'relation': '<', 'threshold': 6.0, 'level': 3}
                ],
                'maxValue': 6.0,
                'minValue': 0.0
            },
            {
                'columnName': 'PeerRestart',
                'dataPointName': 'PeerRestart',
                'unitLabel': ' hrs',
                'enableForecast': False,
                'roundingDecimal': 2,
                'rpn': 'PeerRestart/3600',
                'displayType': 'raw',
                'colorThresholds': [],
                'maxValue': 100000.0,
                'minValue': 0.0
            },
            {
                'columnName': 'Peer In Updates',
                'dataPointName': 'PeerInUpdates',
                'unitLabel': ' updates',
                'enableForecast': False,
                'roundingDecimal': 0,
                'rpn': '',
                'displayType': 'raw',
                'colorThresholds': [],
                'maxValue': 1000000.0,
                'minValue': 0.0
            },
            {
                'columnName': 'Peer Out Updates',
                'dataPointName': 'PeerOutUpdates',
                'unitLabel': ' updates',
                'enableForecast': False,
                'roundingDecimal': 0,
                'rpn': '',
                'displayType': 'raw',
                'colorThresholds': [],
                'maxValue': 1000000.0,
                'minValue': 0.0
            }
        ],
        'rows': rows,
        'displaySettings': {
            'columns': [
                {'visible': True, 'columnLabel': 'Name', 'columnSize': 250, 'columnKey': 'device-name-1452842526600'},
                {'visible': True, 'columnLabel': 'Established', 'columnSize': 120, 'columnKey': '0'},
                {'visible': True, 'columnLabel': 'Peer State', 'columnSize': 100, 'columnKey': '1'},
                {'visible': True, 'columnLabel': 'PeerRestart', 'columnSize': 120, 'columnKey': '2'},
                {'visible': True, 'columnLabel': 'Peer In Updates', 'columnSize': 130, 'columnKey': '3'},
                {'visible': True, 'columnLabel': 'Peer Out Updates', 'columnSize': 130, 'columnKey': '4'}
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
        logger.info(f"Created BGP statistics widget -> {widget_id}")
        return widget_id
    except LMAPIError as e:
        logger.error(f"Failed to create BGP statistics widget: {e}")
        return None
