"""
LogicMonitor helper functions for dashboard, device, and instance resolution.

This module provides reusable functions for common LogicMonitor operations
including finding devices, resolving datasource instances, and managing dashboards.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from lmn_tools.api.client import LMClient
from lmn_tools.core.exceptions import APIError as LMAPIError

logger = logging.getLogger(__name__)


@dataclass
class ResolvedInterface:
    """Represents a resolved interface with all necessary LM identifiers."""
    device_id: int
    hostname: str
    instance_id: int
    instance_name: str
    interface_name: str
    alias: str
    role: str
    include_in_traffic_graphs: bool = True
    include_in_table: bool = True
    dom: bool = False
    datasource_id: int = None
    device_datasource_id: int = None
    datasource_name: str = None  # Internal datasource name (e.g., SNMP_Network_Interfaces)
    datasource_display_name: str = None  # Display name (e.g., Network Interfaces)


@dataclass
class ResolvedBGPPeer:
    """Represents a resolved BGP peer with LM identifiers."""
    device_id: int
    hostname: str
    instance_id: int
    neighbor_ip: str
    description: str
    datasource_id: int = None
    device_datasource_id: int = None


@dataclass
class ResolutionSummary:
    """Summary of resolution results for reporting."""
    devices_defined: int = 0
    devices_resolved: int = 0
    interfaces_defined: int = 0
    interfaces_resolved: int = 0
    bgp_peers_defined: int = 0
    bgp_peers_resolved: int = 0
    unresolved_devices: list = field(default_factory=list)
    unresolved_interfaces: list = field(default_factory=list)
    unresolved_bgp_peers: list = field(default_factory=list)


def find_device_by_hostname(client: LMClient, hostname: str) -> Optional[int]:
    """
    Find a device by hostname in LogicMonitor.

    Searches using system.displayname first, then falls back to system.sysname.

    Args:
        client: LMClient instance
        hostname: Device hostname to search for

    Returns:
        Device ID if found, None otherwise
    """
    # Try displayName first (most common match)
    filter_str = f'displayName:"{hostname}"'
    logger.debug(f"Searching for device with displayName: {hostname}")

    try:
        response = client.get('/device/devices', params={
            'filter': filter_str,
            'fields': 'id,displayName,systemProperties',
            'size': 10
        })
    except LMAPIError as e:
        logger.error(f"Error searching for device {hostname}: {e}")
        return None

    items = response.get('data', {}).get('items', [])

    if items:
        if len(items) > 1:
            logger.warning(f"Multiple devices found for hostname {hostname}, using first match")
        device = items[0]
        device_id = device['id']
        logger.info(f"Found device {hostname} -> deviceId: {device_id}")
        return device_id

    # Try sysname as fallback
    logger.debug(f"No displayName match, trying systemProperties filter for {hostname}")

    # Search by system.sysname property
    filter_str = f'systemProperties.name:system.sysname,systemProperties.value:"{hostname}"'
    try:
        response = client.get('/device/devices', params={
            'filter': filter_str,
            'fields': 'id,displayName',
            'size': 10
        })
    except LMAPIError as e:
        logger.debug(f"Sysname search failed for {hostname}: {e}")
        return None

    items = response.get('data', {}).get('items', [])
    if items:
        device = items[0]
        device_id = device['id']
        logger.info(f"Found device {hostname} via sysname -> deviceId: {device_id}")
        return device_id

    logger.warning(f"Device not found in LogicMonitor: {hostname}")
    return None


def find_datasource_by_name(client: LMClient, datasource_name: str) -> Optional[int]:
    """
    Find a datasource by name.

    Args:
        client: LMClient instance
        datasource_name: Datasource name (can include display name in parens)

    Returns:
        Datasource ID if found, None otherwise
    """
    # Extract the base name if format is "Display Name (internal_name)"
    # or just use as-is
    search_name = datasource_name

    # Try to match by displayName or name
    filter_str = f'displayName:"{search_name}"'

    try:
        response = client.get('/setting/datasources', params={
            'filter': filter_str,
            'fields': 'id,name,displayName',
            'size': 10
        })
    except LMAPIError as e:
        logger.error(f"Error searching for datasource {datasource_name}: {e}")
        return None

    items = response.get('data', {}).get('items', [])
    if items:
        ds = items[0]
        logger.debug(f"Found datasource {datasource_name} -> id: {ds['id']}")
        return ds['id']

    # Try by internal name
    filter_str = f'name:"{search_name}"'
    try:
        response = client.get('/setting/datasources', params={
            'filter': filter_str,
            'fields': 'id,name,displayName',
            'size': 10
        })
    except LMAPIError as e:
        return None

    items = response.get('data', {}).get('items', [])
    if items:
        ds = items[0]
        logger.debug(f"Found datasource {datasource_name} by name -> id: {ds['id']}")
        return ds['id']

    logger.warning(f"Datasource not found: {datasource_name}")
    return None


def find_device_datasource(
    client: LMClient,
    device_id: int,
    datasource_name: str
) -> Optional[tuple]:
    """
    Find the deviceDatasource for a specific device and datasource.

    Args:
        client: LMClient instance
        device_id: Device ID
        datasource_name: Datasource name to find

    Returns:
        Tuple of (deviceDatasourceId, datasourceId, dataSourceName, dataSourceDisplayName) if found, None otherwise
    """
    # Get all datasources applied to this device
    try:
        # First, try to get the datasource ID
        ds_id = find_datasource_by_name(client, datasource_name)

        if ds_id:
            # If we have the datasource ID, filter by it
            response = client.get(
                f'/device/devices/{device_id}/devicedatasources',
                params={
                    'filter': f'dataSourceId:{ds_id}',
                    'fields': 'id,dataSourceId,dataSourceName,dataSourceDisplayName',
                    'size': 10
                }
            )
        else:
            # Otherwise search by name pattern
            response = client.get(
                f'/device/devices/{device_id}/devicedatasources',
                params={
                    'fields': 'id,dataSourceId,dataSourceName,dataSourceDisplayName',
                    'size': 1000
                }
            )
    except LMAPIError as e:
        logger.error(f"Error getting device datasources for device {device_id}: {e}")
        return None

    items = response.get('data', {}).get('items', [])

    # If we filtered by ID, we should have a direct match
    if ds_id and items:
        item = items[0]
        logger.debug(
            f"Found deviceDatasource for device {device_id}, "
            f"datasource {datasource_name} -> {item['id']}"
        )
        return (item['id'], item['dataSourceId'], item.get('dataSourceName', ''), item.get('dataSourceDisplayName', ''))

    # Otherwise search through all datasources
    for item in items:
        ds_name = item.get('dataSourceName', '')
        ds_display = item.get('dataSourceDisplayName', '')

        if datasource_name in ds_name or datasource_name in ds_display:
            logger.debug(
                f"Found deviceDatasource for device {device_id}, "
                f"datasource {datasource_name} -> {item['id']}"
            )
            return (item['id'], item['dataSourceId'], ds_name, ds_display)

        # Also check for partial match (e.g., "SNMP_Network_Interfaces" in full name)
        if datasource_name.lower() in ds_name.lower() or datasource_name.lower() in ds_display.lower():
            logger.debug(
                f"Found deviceDatasource (partial match) for device {device_id}, "
                f"datasource {datasource_name} -> {item['id']}"
            )
            return (item['id'], item['dataSourceId'], ds_name, ds_display)

    logger.warning(f"DeviceDatasource not found for device {device_id}, datasource {datasource_name}")
    return None


def find_datasource_instance(
    client: LMClient,
    device_id: int,
    device_datasource_id: int,
    interface_name: str,
    alias: str = None
) -> Optional[tuple]:
    """
    Find a datasource instance by interface name or alias.

    Args:
        client: LMClient instance
        device_id: Device ID
        device_datasource_id: DeviceDatasource ID
        interface_name: Interface name to match (e.g., 'ae100.3')
        alias: Optional alias to match (e.g., 'VLAN_724636_1460')

    Returns:
        Tuple of (instanceId, displayName) if found, None otherwise
    """
    try:
        # Get all instances for this device datasource
        response = client.get(
            f'/device/devices/{device_id}/devicedatasources/{device_datasource_id}/instances',
            params={
                'fields': 'id,name,displayName,description,wildValue,wildValue2',
                'size': 1000
            }
        )
    except LMAPIError as e:
        logger.error(f"Error getting instances for device {device_id}: {e}")
        return None

    items = response.get('data', {}).get('items', [])

    # First pass: exact match on displayName or name
    for item in items:
        display_name = item.get('displayName', '')
        name = item.get('name', '')
        description = item.get('description', '')
        wild_value = item.get('wildValue', '')

        if interface_name == display_name or interface_name == name or interface_name == wild_value:
            logger.debug(f"Found instance by exact name match: {interface_name} -> {item['id']}")
            return (item['id'], display_name or name)

    # Second pass: match by alias in description or displayName
    if alias:
        for item in items:
            display_name = item.get('displayName', '')
            description = item.get('description', '')

            if alias in display_name or alias in description:
                logger.debug(f"Found instance by alias match: {alias} -> {item['id']}")
                return (item['id'], display_name or item.get('name', ''))

    # Third pass: partial match on interface name (for subinterfaces)
    for item in items:
        display_name = item.get('displayName', '')
        name = item.get('name', '')
        wild_value = item.get('wildValue', '')

        # Check if the interface name is contained in the display name
        if interface_name in display_name or interface_name in name or interface_name in wild_value:
            logger.debug(f"Found instance by partial name match: {interface_name} -> {item['id']}")
            return (item['id'], display_name or name)

    logger.warning(
        f"Instance not found for interface {interface_name} "
        f"(alias: {alias}) on device datasource {device_datasource_id}"
    )
    return None


def find_dom_instance(
    client: LMClient,
    device_id: int,
    device_datasource_id: int,
    interface_name: str
) -> Optional[tuple]:
    """
    Find a DOM datasource instance for a given interface.

    DOM instances are typically keyed by base port (e.g., 'xe-0/0/37')
    rather than the full subinterface (e.g., 'xe-0/0/37.1460').

    Args:
        client: LMClient instance
        device_id: Device ID
        device_datasource_id: DeviceDatasource ID for DOM datasource
        interface_name: Interface name (may include unit, e.g., 'xe-0/0/37.1460')

    Returns:
        Tuple of (instanceId, displayName) if found, None otherwise
    """
    # Strip the unit number to get base port
    base_port = re.sub(r'\.\d+$', '', interface_name)
    logger.debug(f"Looking for DOM instance for base port: {base_port} (from {interface_name})")

    try:
        response = client.get(
            f'/device/devices/{device_id}/devicedatasources/{device_datasource_id}/instances',
            params={
                'fields': 'id,name,displayName,description,wildValue',
                'size': 500
            }
        )
    except LMAPIError as e:
        logger.error(f"Error getting DOM instances for device {device_id}: {e}")
        return None

    items = response.get('data', {}).get('items', [])

    # Look for exact match on base port
    for item in items:
        display_name = item.get('displayName', '')
        name = item.get('name', '')
        wild_value = item.get('wildValue', '')

        if base_port == display_name or base_port == name or base_port == wild_value:
            logger.debug(f"Found DOM instance for {base_port} -> {item['id']}")
            return (item['id'], display_name or name)

        # Also check if base port is contained (in case of different naming)
        if base_port in display_name or base_port in name:
            logger.debug(f"Found DOM instance (partial match) for {base_port} -> {item['id']}")
            return (item['id'], display_name or name)

    logger.warning(f"DOM instance not found for port {base_port} on device {device_id}")
    return None


def find_bgp_instance(
    client: LMClient,
    device_id: int,
    device_datasource_id: int,
    neighbor_ip: str
) -> Optional[tuple]:
    """
    Find a BGP datasource instance by neighbor IP.

    Args:
        client: LMClient instance
        device_id: Device ID
        device_datasource_id: DeviceDatasource ID for BGP datasource
        neighbor_ip: BGP neighbor IP address

    Returns:
        Tuple of (instanceId, displayName) if found, None otherwise
    """
    try:
        response = client.get(
            f'/device/devices/{device_id}/devicedatasources/{device_datasource_id}/instances',
            params={
                'fields': 'id,name,displayName,description,wildValue',
                'size': 500
            }
        )
    except LMAPIError as e:
        logger.error(f"Error getting BGP instances for device {device_id}: {e}")
        return None

    items = response.get('data', {}).get('items', [])

    for item in items:
        display_name = item.get('displayName', '')
        name = item.get('name', '')
        description = item.get('description', '')
        wild_value = item.get('wildValue', '')

        # Check if neighbor IP appears in any field
        if neighbor_ip in display_name or neighbor_ip in name or \
           neighbor_ip in description or neighbor_ip in wild_value:
            logger.debug(f"Found BGP instance for {neighbor_ip} -> {item['id']}")
            return (item['id'], display_name or name)

    logger.warning(f"BGP instance not found for neighbor {neighbor_ip} on device {device_id}")
    return None


def ensure_dashboard_group(client: LMClient, group_path: str) -> Optional[int]:
    """
    Ensure a dashboard group exists, creating nested groups as needed.

    Args:
        client: LMClient instance
        group_path: Full path like "Operations/Customer Dashboards"

    Returns:
        Dashboard group ID if successful, None otherwise
    """
    parts = [p.strip() for p in group_path.split('/') if p.strip()]
    parent_id = 1  # Root group ID

    for i, part in enumerate(parts):
        current_path = '/'.join(parts[:i + 1])
        logger.debug(f"Ensuring dashboard group exists: {current_path}")

        # Search for existing group
        try:
            response = client.get('/dashboard/groups', params={
                'filter': f'parentId:{parent_id},name:"{part}"',
                'fields': 'id,name,parentId,fullPath',
                'size': 50
            })
        except LMAPIError as e:
            logger.error(f"Error searching for dashboard group {part}: {e}")
            return None

        items = response.get('data', {}).get('items', [])

        found = None
        for item in items:
            if item['name'] == part and item['parentId'] == parent_id:
                found = item
                break

        if found:
            parent_id = found['id']
            logger.debug(f"Found existing dashboard group: {part} -> {parent_id}")
        else:
            # Create the group
            logger.info(f"Creating dashboard group: {part} under parent {parent_id}")
            try:
                response = client.post('/dashboard/groups', json={
                    'name': part,
                    'parentId': parent_id,
                    'description': f'Auto-created by LM Dashboard Builder'
                })
            except LMAPIError as e:
                logger.error(f"Error creating dashboard group {part}: {e}")
                return None

            parent_id = response.get('data', {}).get('id') or response.get('id')
            if not parent_id:
                logger.error(f"Failed to get ID for created group {part}")
                return None

            logger.info(f"Created dashboard group: {part} -> {parent_id}")

    return parent_id


def find_dashboard_by_name(client: LMClient, group_id: int, name: str) -> Optional[dict]:
    """
    Find a dashboard by name within a group.

    Args:
        client: LMClient instance
        group_id: Dashboard group ID
        name: Dashboard name

    Returns:
        Dashboard dict if found, None otherwise
    """
    try:
        response = client.get('/dashboard/dashboards', params={
            'filter': f'groupId:{group_id},name:"{name}"',
            'fields': 'id,name,groupId,widgetTokens',
            'size': 50
        })
    except LMAPIError as e:
        logger.error(f"Error searching for dashboard {name}: {e}")
        return None

    items = response.get('data', {}).get('items', [])

    for item in items:
        if item['name'] == name:
            return item

    return None


def sanitize_dashboard_name(name: str) -> str:
    """
    Sanitize a dashboard name by removing characters not allowed by LM API.

    Args:
        name: Original dashboard name

    Returns:
        Sanitized name safe for LM API
    """
    # LM doesn't allow: comma, backslash, and possibly others
    # Replace them with safe alternatives
    sanitized = name.replace(',', ' -').replace('\\', '-')
    return sanitized


def ensure_dashboard(
    client: LMClient,
    group_id: int,
    name: str,
    tokens: dict,
    description: str = ''
) -> Optional[int]:
    """
    Ensure a dashboard exists with the specified tokens.

    Args:
        client: LMClient instance
        group_id: Dashboard group ID
        name: Dashboard name
        tokens: Dictionary of token name -> value
        description: Dashboard description

    Returns:
        Dashboard ID if successful, None otherwise
    """
    # Sanitize the dashboard name
    name = sanitize_dashboard_name(name)

    # Check if dashboard exists
    existing = find_dashboard_by_name(client, group_id, name)

    # Convert tokens dict to LM format
    # Token names should NOT include ## - LM adds those automatically
    widget_tokens = [
        {'name': k, 'value': str(v)}
        for k, v in tokens.items()
    ]

    if existing:
        dashboard_id = existing['id']
        logger.info(f"Found existing dashboard: {name} -> {dashboard_id}")

        # Update tokens if needed
        try:
            client.patch(f'/dashboard/dashboards/{dashboard_id}', json={
                'widgetTokens': widget_tokens,
                'description': description
            })
            logger.debug(f"Updated dashboard tokens for {name}")
        except LMAPIError as e:
            logger.warning(f"Failed to update dashboard tokens: {e}")

        return dashboard_id

    # Create new dashboard
    logger.info(f"Creating dashboard: {name}")

    try:
        response = client.post('/dashboard/dashboards', json={
            'name': name,
            'groupId': group_id,
            'description': description,
            'widgetTokens': widget_tokens,
            'sharable': True
        })
    except LMAPIError as e:
        logger.error(f"Error creating dashboard {name}: {e}")
        return None

    dashboard_id = response.get('data', {}).get('id') or response.get('id')
    if not dashboard_id:
        logger.error(f"Failed to get ID for created dashboard {name}")
        return None

    logger.info(f"Created dashboard: {name} -> {dashboard_id}")
    return dashboard_id


def delete_dashboard_widgets(client: LMClient, dashboard_id: int) -> int:
    """
    Delete all widgets from a dashboard.

    Args:
        client: LMClient instance
        dashboard_id: Dashboard ID

    Returns:
        Number of widgets deleted
    """
    try:
        response = client.get(f'/dashboard/dashboards/{dashboard_id}/widgets', params={
            'fields': 'id,name,type',
            'size': 500
        })
    except LMAPIError as e:
        logger.error(f"Error getting widgets for dashboard {dashboard_id}: {e}")
        return 0

    items = response.get('data', {}).get('items', [])
    deleted_count = 0

    for widget in items:
        widget_id = widget['id']
        try:
            client.delete(f'/dashboard/widgets/{widget_id}')
            deleted_count += 1
            logger.debug(f"Deleted widget {widget_id}: {widget.get('name', 'unnamed')}")
        except LMAPIError as e:
            logger.warning(f"Failed to delete widget {widget_id}: {e}")

    logger.info(f"Deleted {deleted_count} widgets from dashboard {dashboard_id}")
    return deleted_count


def get_datapoint_info(client: LMClient, datasource_id: int) -> dict:
    """
    Get datapoint information for a datasource.

    Args:
        client: LMClient instance
        datasource_id: Datasource ID

    Returns:
        Dictionary mapping datapoint names to their info
    """
    try:
        response = client.get(f'/setting/datasources/{datasource_id}/datapoints', params={
            'fields': 'id,name,description,type',
            'size': 100
        })
    except LMAPIError as e:
        logger.error(f"Error getting datapoints for datasource {datasource_id}: {e}")
        return {}

    items = response.get('data', {}).get('items', [])
    return {item['name']: item for item in items}
