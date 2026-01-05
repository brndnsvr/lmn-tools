#!/usr/bin/env python3
"""
Coriant Chassis/System Metric Collection Script for LogicMonitor

This script collects chassis-level metrics (temperature, altitude, software state)
from Coriant optical transport devices via NETCONF. It outputs in LogicMonitor's
single-instance SCRIPT format (not BATCHSCRIPT).

Usage:
    coriant_chassis_collect.py <hostname> <username> <password> [--port PORT] [--debug]

Output Format (Single-instance - no instance prefix):
    datapoint_name=numeric_value

Example Output:
    ne_temperature=42
    ne_altitude=150
    swload_active=1

Exit Codes:
    0 = Success (metrics collected)
    1 = Error (connection failure, authentication error, etc.)

LogicMonitor DataSource Configuration:
    Collection Method: SCRIPT (single-instance, NOT BATCHSCRIPT)
    Script: Upload this file
    Parameters: ##system.hostname## ##netconf.user## ##netconf.pass## ##netconf.port##
    No Active Discovery needed (single instance per device)
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml
from lxml import etree

from lmn_tools.collectors.optical import NetconfClient, NetconfClientError
from lmn_tools.collectors.optical.utils import (
    safe_float,
    get_local_name,
    extract_element_text,
)

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = None) -> dict:
    """
    Load the Coriant chassis configuration YAML file.

    Args:
        config_path: Optional path to config file. If not provided,
                    uses default location relative to script.

    Returns:
        Configuration dictionary
    """
    if config_path is None:
        config_path = project_root / "configs" / "coriant_chassis.yaml"

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_netconf_filter(config: dict) -> str:
    """
    Extract the NETCONF filter XML from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        XML filter string
    """
    return config.get('netconf_filter', '')


def find_element_text(root: etree._Element, xpath: str) -> str:
    """
    Find element text using XPath with namespace handling.

    Args:
        root: Root XML element
        xpath: XPath expression

    Returns:
        Element text or None
    """
    # Try direct XPath first
    try:
        elements = root.xpath(xpath)
        if elements:
            if isinstance(elements[0], str):
                return elements[0]
            return extract_element_text(elements[0])
    except Exception:
        pass

    # Convert to local-name() based XPath for namespace-agnostic matching
    parts = xpath.replace('.//','').split('/')
    converted_parts = []

    for part in parts:
        if not part or part == '.':
            continue
        # Handle predicates like [swload-state='Active']
        if '[' in part:
            base = part.split('[')[0]
            pred_part = '[' + '['.join(part.split('[')[1:])
            # Convert predicate element names too
            pred_part = pred_part.replace('[', "[*[local-name()='").replace("='", "']/text()='").replace(']', "']")
            # This is getting complex, let's do simple search instead
            pass
        converted_parts.append(f"*[local-name()='{part}']")

    if not converted_parts:
        return None

    # Try the converted XPath
    try:
        local_xpath = './/' + '/'.join(converted_parts)
        elements = root.xpath(local_xpath)
        if elements:
            return extract_element_text(elements[0])
    except Exception:
        pass

    # Fallback: manual tree walking for simple paths
    parts = xpath.replace('.//', '').split('/')
    current = [root]

    for part in parts:
        if not part:
            continue
        # Handle predicate
        predicate = None
        if '[' in part:
            base_part = part.split('[')[0]
            pred_str = part.split('[')[1].rstrip(']')
            # Parse predicate like "swload-state='Active'"
            if '=' in pred_str:
                pred_key, pred_val = pred_str.split('=', 1)
                pred_val = pred_val.strip("'\"")
                predicate = (pred_key, pred_val)
            part = base_part

        next_elements = []
        for elem in current:
            for child in elem.iter():
                local_name = get_local_name(child.tag)
                if local_name == part:
                    # Check predicate if present
                    if predicate:
                        pred_key, pred_val = predicate
                        pred_child = None
                        for sub in child:
                            if get_local_name(sub.tag) == pred_key:
                                pred_child = sub
                                break
                        if pred_child is not None and extract_element_text(pred_child) == pred_val:
                            next_elements.append(child)
                    else:
                        next_elements.append(child)
        current = next_elements

        if not current:
            break

    if current:
        return extract_element_text(current[0])

    return None


def collect_chassis_metrics(
    hostname: str,
    username: str,
    password: str,
    port: int = 830,
    debug: bool = False,
    config: dict = None
) -> int:
    """
    Collect chassis metrics from a Coriant device.

    Args:
        hostname: Device hostname or IP
        username: NETCONF username
        password: NETCONF password
        port: NETCONF port (default: 830)
        debug: Enable debug output
        config: Optional pre-loaded configuration

    Returns:
        Exit code (0 = success, 1 = error)
    """
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Load configuration if not provided
    if config is None:
        try:
            config = load_config()
        except Exception as e:
            print(f"ERROR: Failed to load configuration: {e}", file=sys.stderr)
            return 1

    # Get NETCONF filter
    netconf_filter = get_netconf_filter(config)
    if not netconf_filter:
        print("ERROR: No NETCONF filter defined in configuration", file=sys.stderr)
        return 1

    try:
        # Connect to device
        logger.debug(f"Connecting to {hostname}:{port}")

        with NetconfClient(
            hostname=hostname,
            username=username,
            password=password,
            port=port,
            device_type="coriant",
            debug=debug
        ) as client:

            # Build and send filter
            logger.debug("Building NETCONF filter")
            filter_elem = client.build_filter(netconf_filter)

            # Execute get operation
            logger.debug("Executing NETCONF get operation")
            data = client.get(filter_elem)

            if data is None:
                print("ERROR: No data returned from device", file=sys.stderr)
                return 1

            # Extract metrics
            metrics_collected = 0
            metric_configs = config.get('metrics', [])

            for metric_config in metric_configs:
                name = metric_config.get('name', '')
                xpath = metric_config.get('xpath', '')

                if not name or not xpath:
                    continue

                raw_value = find_element_text(data, xpath)

                if raw_value is not None:
                    # Convert to numeric
                    value = safe_float(raw_value)
                    if value is not None:
                        # Output in single-instance format (no instance prefix)
                        print(f"{name}={value}")
                        metrics_collected += 1
                    else:
                        logger.debug(f"Could not convert {name} value '{raw_value}' to float")
                else:
                    logger.debug(f"No value found for metric {name} at {xpath}")

            # Check for active software load
            # If we can find an Active software load, output swload_active=1
            active_sw = find_element_text(data, ".//softwareload[swload-state='Active']/swload-state")
            if active_sw == 'Active':
                print("swload_active=1")
                metrics_collected += 1
            else:
                print("swload_active=0")
                metrics_collected += 1

            logger.debug(f"Collected {metrics_collected} chassis metrics")

            if metrics_collected == 0:
                logger.warning("No chassis metrics collected from device")

            return 0

    except NetconfClientError as e:
        print(f"ERROR: NETCONF error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        if debug:
            import traceback
            traceback.print_exc(file=sys.stderr)
        return 1


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Collect chassis metrics from Coriant devices via NETCONF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic collection
    %(prog)s device.example.com admin password123

    # With custom port
    %(prog)s device.example.com admin password123 --port 22830

    # With debug output
    %(prog)s device.example.com admin password123 --debug

Output Format (single-instance - no instance prefix):
    datapoint_name=value

Example Output:
    ne_temperature=42
    ne_altitude=150
    swload_active=1

Exit Codes:
    0 = Success (metrics output to stdout)
    1 = Error (message output to stderr)
        """
    )

    parser.add_argument(
        'hostname',
        help='Device hostname or IP address'
    )
    parser.add_argument(
        'username',
        help='NETCONF username'
    )
    parser.add_argument(
        'password',
        help='NETCONF password'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=830,
        help='NETCONF port (default: 830)'
    )
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug output to stderr'
    )
    parser.add_argument(
        '--config', '-c',
        help='Path to configuration YAML file'
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Load config if specified
    config = None
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            print(f"ERROR: Failed to load config file: {e}", file=sys.stderr)
            sys.exit(1)

    exit_code = collect_chassis_metrics(
        hostname=args.hostname,
        username=args.username,
        password=args.password,
        port=args.port,
        debug=args.debug,
        config=config
    )

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
