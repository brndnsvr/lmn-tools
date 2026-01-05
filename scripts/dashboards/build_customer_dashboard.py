#!/usr/bin/env python3
"""
LogicMonitor Customer Dashboard Builder

This tool creates or updates customer network overview dashboards in LogicMonitor
based on a YAML configuration file. It supports:
- Interface statistics tables
- Traffic throughput graphs
- DOM optics graphs for leaf interfaces
- BGP peer tables (optional)

Usage:
    python build_customer_dashboard.py \\
        --config configs/ban_724636.yml \\
        --company evoqedcs \\
        --access-id <LM_ACCESS_ID> \\
        --access-key <LM_ACCESS_KEY> \\
        [--dry-run]

Environment variables (optional, override CLI args):
    LM_COMPANY      - LogicMonitor company name
    LM_ACCESS_ID    - LogicMonitor API access ID
    LM_ACCESS_KEY   - LogicMonitor API access key
"""

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from lmn_tools.api.client import LMClient
from lmn_tools.core.exceptions import APIError as LMClientError
from lmn_tools.dashboards.helpers import (
    ResolvedInterface,
    ResolvedBGPPeer,
    ResolutionSummary,
    find_device_by_hostname,
    find_device_datasource,
    find_datasource_instance,
    find_dom_instance,
    find_bgp_instance,
    ensure_dashboard_group,
    ensure_dashboard,
    delete_dashboard_widgets,
)
from lmn_tools.dashboards.builders import (
    WidgetPosition,
    create_header_widget,
    create_interface_table_widget,
    create_bgp_table_widget,
    create_bgp_statistics_widget,
    build_traffic_graphs_by_type,
    build_traffic_graphs_by_device,
    build_dom_graphs,
    create_consolidated_traffic_graph,
    create_consolidated_packet_graph,
    get_interface_type,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Default datasource names
DEFAULT_INTERFACE_DATASOURCE = 'SNMP_Network_Interfaces'
DEFAULT_DOM_DATASOURCE = 'Juniper_Junos_DOM'
DEFAULT_BGP_DATASOURCE = 'Juniper_BGP_Peers'


@dataclass
class CustomerConfig:
    """Parsed customer configuration from YAML."""
    ban: str
    name: str
    metros: list
    dashboard_group: str
    interface_datasource: str
    dom_datasource: str
    bgp_datasource: str
    devices: list
    bgp_peers: list


def load_config(config_path: str) -> CustomerConfig:
    """
    Load and validate the YAML configuration file.

    Args:
        config_path: Path to the YAML config file

    Returns:
        CustomerConfig object

    Raises:
        ValueError: If required fields are missing
        FileNotFoundError: If config file doesn't exist
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, 'r') as f:
        config = yaml.safe_load(f)

    # Validate required sections
    if 'customer' not in config:
        raise ValueError("Config missing 'customer' section")
    if 'devices' not in config:
        raise ValueError("Config missing 'devices' section")

    customer = config['customer']
    lm_config = config.get('logicmonitor', {})

    # Validate customer fields
    if 'ban' not in customer:
        raise ValueError("Config missing 'customer.ban'")
    if 'name' not in customer:
        raise ValueError("Config missing 'customer.name'")

    return CustomerConfig(
        ban=str(customer['ban']),
        name=customer['name'],
        metros=customer.get('metros', []),
        dashboard_group=lm_config.get('dashboard_group', 'Customer Dashboards'),
        interface_datasource=lm_config.get('interface_datasource', DEFAULT_INTERFACE_DATASOURCE),
        dom_datasource=lm_config.get('dom_datasource', DEFAULT_DOM_DATASOURCE),
        bgp_datasource=lm_config.get('bgp_datasource', DEFAULT_BGP_DATASOURCE),
        devices=config.get('devices', []),
        bgp_peers=config.get('bgp_peers', [])
    )


def resolve_interfaces(
    client: LMClient,
    config: CustomerConfig,
    summary: ResolutionSummary
) -> list[ResolvedInterface]:
    """
    Resolve all interfaces from config to LM IDs.

    Args:
        client: LMClient instance
        config: Customer configuration
        summary: Resolution summary to update

    Returns:
        List of ResolvedInterface objects
    """
    resolved = []

    for device in config.devices:
        hostname = device['hostname']
        device_role = device.get('role', '')  # Device role (router, leaf, etc.)
        summary.devices_defined += 1

        # Find device ID
        device_id = find_device_by_hostname(client, hostname)
        if device_id is None:
            summary.unresolved_devices.append(hostname)
            logger.warning(f"Skipping device {hostname} - not found in LM")
            continue

        summary.devices_resolved += 1

        # Find interface datasource for this device
        ds_result = find_device_datasource(
            client, device_id, config.interface_datasource
        )
        if ds_result is None:
            logger.warning(
                f"Interface datasource not found for {hostname}, "
                f"skipping interfaces"
            )
            continue

        device_datasource_id, datasource_id, ds_name, ds_display_name = ds_result

        # Resolve each interface
        for iface in device.get('interfaces', []):
            summary.interfaces_defined += 1
            iface_name = iface['name']
            alias = iface.get('alias', '')

            instance_result = find_datasource_instance(
                client, device_id, device_datasource_id,
                iface_name, alias
            )

            if instance_result is None:
                summary.unresolved_interfaces.append(f"{hostname}:{iface_name}")
                logger.warning(f"Skipping interface {hostname}:{iface_name} - not found")
                continue

            instance_id, instance_name = instance_result
            summary.interfaces_resolved += 1

            resolved.append(ResolvedInterface(
                device_id=device_id,
                hostname=hostname,
                instance_id=instance_id,
                instance_name=instance_name,
                interface_name=iface_name,
                alias=alias,
                role=device_role,  # Use device role (router, leaf) for interface type detection
                include_in_traffic_graphs=iface.get('include_in_traffic_graphs', True),
                include_in_table=iface.get('include_in_table', True),
                dom=iface.get('dom', False),
                datasource_id=datasource_id,
                device_datasource_id=device_datasource_id,
                datasource_name=ds_name,
                datasource_display_name=ds_display_name
            ))

    return resolved


def resolve_dom_interfaces(
    client: LMClient,
    config: CustomerConfig,
    interfaces: list[ResolvedInterface]
) -> list:
    """
    Resolve DOM datasource instances for interfaces marked with dom: true.

    Args:
        client: LMClient instance
        config: Customer configuration
        interfaces: List of resolved interfaces

    Returns:
        List of (interface, dom_instance_id, dom_instance_name, dom_datasource_id) tuples
    """
    dom_interfaces = []

    # Cache device datasource lookups
    device_dom_ds = {}

    for iface in interfaces:
        if not iface.dom:
            continue

        # Get DOM datasource for this device
        if iface.device_id not in device_dom_ds:
            ds_result = find_device_datasource(
                client, iface.device_id, config.dom_datasource
            )
            device_dom_ds[iface.device_id] = ds_result

        ds_result = device_dom_ds[iface.device_id]
        if ds_result is None:
            logger.warning(
                f"DOM datasource not found for {iface.hostname}, "
                f"skipping DOM for {iface.interface_name}"
            )
            continue

        device_datasource_id, datasource_id, dom_ds_name, dom_ds_display = ds_result

        # Find DOM instance
        dom_result = find_dom_instance(
            client, iface.device_id, device_datasource_id, iface.interface_name
        )
        if dom_result is None:
            logger.warning(
                f"DOM instance not found for {iface.hostname}:{iface.interface_name}"
            )
            continue

        dom_instance_id, dom_instance_name = dom_result
        # Build dataSourceFullName in format "DisplayName (internal_name)"
        dom_ds_full_name = f"{dom_ds_display} ({dom_ds_name})"
        dom_interfaces.append((iface, dom_instance_id, dom_instance_name, datasource_id, dom_ds_full_name))

    return dom_interfaces


def resolve_bgp_peers(
    client: LMClient,
    config: CustomerConfig,
    summary: ResolutionSummary
) -> list[ResolvedBGPPeer]:
    """
    Resolve BGP peers from config to LM IDs.

    Args:
        client: LMClient instance
        config: Customer configuration
        summary: Resolution summary to update

    Returns:
        List of ResolvedBGPPeer objects
    """
    if not config.bgp_peers:
        return []

    resolved = []

    # Cache device lookups and datasource lookups
    device_cache = {}
    ds_cache = {}

    for peer in config.bgp_peers:
        summary.bgp_peers_defined += 1
        hostname = peer['device']
        neighbor_ip = peer['neighbor_ip']
        description = peer.get('description', '')

        # Get device ID
        if hostname not in device_cache:
            device_cache[hostname] = find_device_by_hostname(client, hostname)

        device_id = device_cache[hostname]
        if device_id is None:
            summary.unresolved_bgp_peers.append(f"{hostname}:{neighbor_ip}")
            continue

        # Get BGP datasource for this device
        if device_id not in ds_cache:
            ds_cache[device_id] = find_device_datasource(
                client, device_id, config.bgp_datasource
            )

        ds_result = ds_cache[device_id]
        if ds_result is None:
            summary.unresolved_bgp_peers.append(f"{hostname}:{neighbor_ip}")
            continue

        device_datasource_id, datasource_id, _, _ = ds_result

        # Find BGP instance
        bgp_result = find_bgp_instance(
            client, device_id, device_datasource_id, neighbor_ip
        )
        if bgp_result is None:
            summary.unresolved_bgp_peers.append(f"{hostname}:{neighbor_ip}")
            continue

        instance_id, instance_name = bgp_result
        summary.bgp_peers_resolved += 1

        resolved.append(ResolvedBGPPeer(
            device_id=device_id,
            hostname=hostname,
            instance_id=instance_id,
            neighbor_ip=neighbor_ip,
            description=description,
            datasource_id=datasource_id,
            device_datasource_id=device_datasource_id
        ))

    return resolved


def print_dry_run_summary(
    config: CustomerConfig,
    interfaces: list[ResolvedInterface],
    dom_interfaces: list,
    bgp_peers: list[ResolvedBGPPeer],
    summary: ResolutionSummary
):
    """Print validation results in dry-run mode."""
    print("\n" + "=" * 70)
    print("DRY RUN - Validation Results (no changes made)")
    print("=" * 70)

    print(f"\nCustomer: {config.name}")
    print(f"BAN: {config.ban}")
    print(f"Dashboard Group: {config.dashboard_group}")
    print(f"Dashboard Name: Customer – {config.name} – BAN {config.ban}")

    # Devices section
    print(f"\n{'─' * 70}")
    print("DEVICES")
    print(f"{'─' * 70}")
    print(f"Defined: {summary.devices_defined}  |  Resolved: {summary.devices_resolved}")

    if summary.unresolved_devices:
        print(f"\n  ✗ UNRESOLVED DEVICES:")
        for dev in summary.unresolved_devices:
            print(f"    - {dev}")

    # Show resolved devices with their IDs
    resolved_device_ids = {}
    for iface in interfaces:
        if iface.hostname not in resolved_device_ids:
            resolved_device_ids[iface.hostname] = iface.device_id

    if resolved_device_ids:
        print(f"\n  ✓ RESOLVED DEVICES:")
        for hostname, device_id in resolved_device_ids.items():
            print(f"    - {hostname} -> deviceId: {device_id}")

    # Interfaces section
    print(f"\n{'─' * 70}")
    print("INTERFACES")
    print(f"{'─' * 70}")
    print(f"Defined: {summary.interfaces_defined}  |  Resolved: {summary.interfaces_resolved}")

    if summary.unresolved_interfaces:
        print(f"\n  ✗ UNRESOLVED INTERFACES:")
        for iface in summary.unresolved_interfaces:
            print(f"    - {iface}")

    if interfaces:
        print(f"\n  ✓ RESOLVED INTERFACES:")
        for iface in interfaces:
            flags = []
            if iface.include_in_table:
                flags.append("table")
            if iface.include_in_traffic_graphs:
                flags.append("graph")
            if iface.dom:
                flags.append("DOM")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            # Show both interface_name (from config) and instance_name (resolved from LM)
            instance_info = f"instanceId: {iface.instance_id}, instanceName: '{iface.instance_name}'"
            print(f"    - {iface.hostname}:{iface.interface_name} -> {instance_info}{flag_str}")

    # DOM section
    if any(d.get('interfaces', []) for d in config.devices):
        dom_defined = sum(1 for d in config.devices for i in d.get('interfaces', []) if i.get('dom', False))
        if dom_defined > 0:
            print(f"\n{'─' * 70}")
            print("DOM OPTICS")
            print(f"{'─' * 70}")
            print(f"Defined: {dom_defined}  |  Resolved: {len(dom_interfaces)}")

            if dom_interfaces:
                print(f"\n  ✓ RESOLVED DOM INSTANCES:")
                for iface, dom_id, dom_name, ds_id, ds_full_name in dom_interfaces:
                    # Show the physical port name (dom_name) not the logical subinterface
                    print(f"    - {iface.hostname}:{dom_name} -> DOM instanceId: {dom_id}")

    # BGP section
    if config.bgp_peers:
        print(f"\n{'─' * 70}")
        print("BGP PEERS")
        print(f"{'─' * 70}")
        print(f"Defined: {summary.bgp_peers_defined}  |  Resolved: {summary.bgp_peers_resolved}")

        if summary.unresolved_bgp_peers:
            print(f"\n  ✗ UNRESOLVED BGP PEERS:")
            for peer in summary.unresolved_bgp_peers:
                print(f"    - {peer}")

        if bgp_peers:
            print(f"\n  ✓ RESOLVED BGP PEERS:")
            for peer in bgp_peers:
                print(f"    - {peer.hostname}:{peer.neighbor_ip} -> instanceId: {peer.instance_id}")

    # Widget summary
    print(f"\n{'─' * 70}")
    print("WIDGETS TO CREATE")
    print(f"{'─' * 70}")

    widget_count = 1  # Header
    widget_count += 1 if interfaces else 0  # Table

    # Count interfaces by type for traffic graphs
    traffic_interfaces = [i for i in interfaces if i.include_in_traffic_graphs]
    internet_count = sum(1 for i in traffic_interfaces if get_interface_type(i.role, i.interface_name, i.alias) == 'internet')
    cloudconnect_count = sum(1 for i in traffic_interfaces if get_interface_type(i.role, i.interface_name, i.alias) == 'cloudconnect')
    access_count = sum(1 for i in traffic_interfaces if get_interface_type(i.role, i.interface_name, i.alias) == 'access')

    # Traffic graphs: each type gets 1 section header + 2 graphs (bandwidth + packets)
    traffic_widget_count = 0
    if internet_count > 0:
        traffic_widget_count += 3  # header + 2 graphs
    if cloudconnect_count > 0:
        traffic_widget_count += 3
    if access_count > 0:
        traffic_widget_count += 3
    widget_count += traffic_widget_count

    dom_graph_count = len(dom_interfaces) * 3  # 3 graphs per interface: Laser Bias, Module Temp, Optical Power (combined Rx+Tx)
    widget_count += dom_graph_count  # DOM graphs (3 per interface)
    if dom_interfaces:
        widget_count += 1  # DOM section header
    widget_count += 1 if bgp_peers else 0  # BGP statistics table

    print(f"Total widgets: {widget_count}")
    print(f"  - 1 header widget")
    print(f"  - 1 interface table ({sum(1 for i in interfaces if i.include_in_table)} rows)")
    if internet_count > 0:
        print(f"  - 1 section + 2 Internet traffic graphs ({internet_count} interfaces)")
    if cloudconnect_count > 0:
        print(f"  - 1 section + 2 CloudConnect traffic graphs ({cloudconnect_count} interfaces)")
    if access_count > 0:
        print(f"  - 1 section + 2 Access Port traffic graphs ({access_count} interfaces)")
    if dom_interfaces:
        print(f"  - 1 DOM section + {dom_graph_count} DOM graphs ({len(dom_interfaces)} ports × 3 metrics)")
    if bgp_peers:
        print(f"  - 1 BGP statistics table ({len(bgp_peers)} peers)")

    print("\n" + "=" * 70)


def build_dashboard(
    client: LMClient,
    config: CustomerConfig,
    interfaces: list[ResolvedInterface],
    dom_interfaces: list,
    bgp_peers: list[ResolvedBGPPeer]
) -> dict:
    """
    Build the complete customer dashboard with all widgets.

    Args:
        client: LMClient instance
        config: Customer configuration
        interfaces: Resolved interfaces
        dom_interfaces: DOM interface info
        bgp_peers: Resolved BGP peers

    Returns:
        Dictionary with build results
    """
    results = {
        'dashboard_id': None,
        'widgets_created': 0,
        'errors': []
    }

    # Step 1: Ensure dashboard group exists
    logger.info(f"Ensuring dashboard group exists: {config.dashboard_group}")
    group_id = ensure_dashboard_group(client, config.dashboard_group)
    if group_id is None:
        results['errors'].append("Failed to create/find dashboard group")
        return results

    # Step 2: Create or update dashboard
    dashboard_name = f"Customer – {config.name} – BAN {config.ban}"
    tokens = {
        'BAN': config.ban,
        'CUSTOMER_NAME': config.name
    }

    description = (
        f"Network overview dashboard for {config.name} (BAN: {config.ban}). "
        f"Auto-generated by LM Dashboard Builder."
    )

    logger.info(f"Creating/updating dashboard: {dashboard_name}")
    dashboard_id = ensure_dashboard(client, group_id, dashboard_name, tokens, description)
    if dashboard_id is None:
        results['errors'].append("Failed to create/find dashboard")
        return results

    results['dashboard_id'] = dashboard_id

    # Step 3: Delete existing widgets (idempotent rebuild)
    logger.info("Removing existing widgets for clean rebuild")
    delete_dashboard_widgets(client, dashboard_id)

    # Step 4: Create widgets
    position = WidgetPosition()

    # Header widget
    logger.info("Creating header widget")
    if create_header_widget(client, dashboard_id, config.name, config.ban, position):
        results['widgets_created'] += 1

    # Interface statistics table
    table_interfaces = [i for i in interfaces if i.include_in_table]
    if table_interfaces:
        logger.info(f"Creating interface table with {len(table_interfaces)} interfaces")
        if create_interface_table_widget(
            client, dashboard_id, table_interfaces,
            config.interface_datasource, position
        ):
            results['widgets_created'] += 1

    # Traffic graphs split by interface type (Internet, CloudConnect, Access)
    traffic_interfaces = [i for i in interfaces if i.include_in_traffic_graphs]
    if traffic_interfaces:
        logger.info(f"Creating traffic graphs for {len(traffic_interfaces)} interfaces (split by type)")
        count = build_traffic_graphs_by_type(client, dashboard_id, interfaces, position)
        results['widgets_created'] += count

    # DOM optics graphs
    if dom_interfaces:
        logger.info(f"Creating DOM graphs for {len(dom_interfaces)} interfaces")
        count = build_dom_graphs(client, dashboard_id, dom_interfaces, position)
        results['widgets_created'] += count

    # BGP Statistics table (dynamicTable with detailed metrics)
    if bgp_peers:
        logger.info(f"Creating BGP statistics table with {len(bgp_peers)} peers")
        if create_bgp_statistics_widget(client, dashboard_id, bgp_peers, position):
            results['widgets_created'] += 1

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Build LogicMonitor customer dashboards from YAML config',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--config', '-c',
        required=True,
        help='Path to YAML configuration file'
    )
    parser.add_argument(
        '--company',
        default=os.environ.get('LM_COMPANY'),
        help='LogicMonitor company name (or set LM_COMPANY env var)'
    )
    parser.add_argument(
        '--access-id',
        default=os.environ.get('LM_ACCESS_ID'),
        help='LogicMonitor API access ID (or set LM_ACCESS_ID env var)'
    )
    parser.add_argument(
        '--access-key',
        default=os.environ.get('LM_ACCESS_KEY'),
        help='LogicMonitor API access key (or set LM_ACCESS_KEY env var)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate config against LM API (resolves devices/instances) without creating dashboard'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate credentials (required for both dry-run and real execution)
    if not args.company:
        print("Error: --company required (or set LM_COMPANY env var)")
        sys.exit(1)
    if not args.access_id:
        print("Error: --access-id required (or set LM_ACCESS_ID env var)")
        sys.exit(1)
    if not args.access_key:
        print("Error: --access-key required (or set LM_ACCESS_KEY env var)")
        sys.exit(1)

    # Load configuration
    try:
        config = load_config(args.config)
        logger.info(f"Loaded config for {config.name} (BAN: {config.ban})")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

    # Initialize summary
    summary = ResolutionSummary()

    # Initialize LM client
    try:
        client = LMClient(
            company=args.company,
            access_id=args.access_id,
            access_key=args.access_key
        )
        logger.info(f"Connected to LogicMonitor ({args.company})")
    except LMClientError as e:
        print(f"Error connecting to LogicMonitor: {e}")
        sys.exit(1)

    # Resolve all interfaces
    logger.info("Resolving interfaces...")
    interfaces = resolve_interfaces(client, config, summary)

    # Resolve DOM interfaces
    logger.info("Resolving DOM interfaces...")
    dom_interfaces = resolve_dom_interfaces(client, config, interfaces)

    # Resolve BGP peers
    bgp_peers = []
    if config.bgp_peers:
        logger.info("Resolving BGP peers...")
        bgp_peers = resolve_bgp_peers(client, config, summary)

    # In dry-run mode, print validation results and exit
    if args.dry_run:
        print_dry_run_summary(config, interfaces, dom_interfaces, bgp_peers, summary)

        # Exit with error if nothing could be resolved
        if summary.devices_resolved == 0:
            print("\nERROR: No devices could be resolved. Check hostnames match LM.")
            sys.exit(1)

        # Exit with warning code if some items unresolved
        if summary.unresolved_devices or summary.unresolved_interfaces or summary.unresolved_bgp_peers:
            print("\nWARNING: Some items could not be resolved. Review above.")
            sys.exit(2)

        print("\nValidation PASSED. Run without --dry-run to create dashboard.")
        sys.exit(0)

    # Build the dashboard
    logger.info("Building dashboard...")
    results = build_dashboard(client, config, interfaces, dom_interfaces, bgp_peers)

    # Print summary
    print("\n" + "=" * 60)
    print("DASHBOARD BUILD COMPLETE")
    print("=" * 60)
    print(f"\nCustomer: {config.name}")
    print(f"BAN: {config.ban}")

    if results['dashboard_id']:
        print(f"\nDashboard ID: {results['dashboard_id']}")
        print(f"Dashboard URL: https://{args.company}.logicmonitor.com/santaba/uiv4/dashboard/{results['dashboard_id']}")

    print(f"\nWidgets created: {results['widgets_created']}")

    print(f"\n--- Resolution Summary ---")
    print(f"Devices: {summary.devices_resolved}/{summary.devices_defined} resolved")
    print(f"Interfaces: {summary.interfaces_resolved}/{summary.interfaces_defined} resolved")
    if config.bgp_peers:
        print(f"BGP Peers: {summary.bgp_peers_resolved}/{summary.bgp_peers_defined} resolved")

    if summary.unresolved_devices:
        print(f"\nUnresolved devices: {', '.join(summary.unresolved_devices)}")
    if summary.unresolved_interfaces:
        print(f"Unresolved interfaces ({len(summary.unresolved_interfaces)}):")
        for iface in summary.unresolved_interfaces[:5]:
            print(f"  - {iface}")
        if len(summary.unresolved_interfaces) > 5:
            print(f"  ... and {len(summary.unresolved_interfaces) - 5} more")

    if results['errors']:
        print(f"\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")
        sys.exit(1)

    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
