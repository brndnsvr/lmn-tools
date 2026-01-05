#!/usr/bin/env python3
"""
Coriant Device Metric Collection Script for LogicMonitor (BATCHSCRIPT)

This script collects metrics from optical interfaces (OTS, OMS, OSC, GOPT)
on Coriant optical transport devices via NETCONF and outputs them in
LogicMonitor's BATCHSCRIPT format.

Usage:
    coriant_collect.py <hostname> <username> <password> [--port PORT] [--debug] [--json]

Output Format (Line-based):
    instance_id.datapoint_name=numeric_value

Output Format (JSON):
    {
        "data": {
            "instance_id": {
                "values": {
                    "datapoint": value
                }
            }
        }
    }

Exit Codes:
    0 = Success (metrics collected)
    1 = Error (connection failure, authentication error, etc.)

LogicMonitor DataSource Configuration:
    Collection Method: BATCHSCRIPT
    Script: Upload this file
    Parameters: ##system.hostname## ##netconf.user## ##netconf.pass## ##netconf.port##
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from lxml import etree

from lmn_tools.collectors.optical import NetconfClient, NetconfClientError
from lmn_tools.collectors.optical import XmlParser
from lmn_tools.collectors.optical import OutputFormatter

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = None) -> dict:
    """
    Load the Coriant configuration YAML file.

    Args:
        config_path: Optional path to config file. If not provided,
                    uses default location relative to script.

    Returns:
        Configuration dictionary
    """
    if config_path is None:
        config_path = project_root / "configs" / "coriant.yaml"

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


def collect_metrics(
    hostname: str,
    username: str,
    password: str,
    port: int = 830,
    debug: bool = False,
    use_json: bool = False,
    config: dict = None
) -> int:
    """
    Collect metrics from a Coriant device and output in LogicMonitor format.

    Args:
        hostname: Device hostname or IP
        username: NETCONF username
        password: NETCONF password
        port: NETCONF port (default: 830)
        debug: Enable debug output
        use_json: Use JSON output format instead of line-based
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

    # Create formatter for output
    formatter = OutputFormatter(use_json=use_json, debug=debug)

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

            # Parse response to collect metrics
            logger.debug("Parsing NETCONF response")
            parser = XmlParser(
                namespaces=config.get('namespaces', {}),
                debug=debug
            )

            metrics = parser.collect_metrics(data, config)

            logger.debug(f"Collected {len(metrics)} metrics")

            # Output in LogicMonitor format
            if metrics:
                formatter.write_collection(metrics)
            else:
                # No metrics is not necessarily an error
                # Could be a device with no optical interfaces
                logger.warning("No metrics collected from device")

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
        description='Collect metrics from Coriant devices via NETCONF (BATCHSCRIPT)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic collection (line-based output)
    %(prog)s device.example.com admin password123

    # With JSON output format
    %(prog)s device.example.com admin password123 --json

    # With custom port
    %(prog)s device.example.com admin password123 --port 22830

    # With debug output
    %(prog)s device.example.com admin password123 --debug

Output Format (line-based):
    instance_id.datapoint_name=value

Output Format (JSON):
    {"data": {"instance_id": {"values": {"datapoint": value}}}}

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
        '--json', '-j',
        action='store_true',
        help='Output in JSON format instead of line-based'
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

    exit_code = collect_metrics(
        hostname=args.hostname,
        username=args.username,
        password=args.password,
        port=args.port,
        debug=args.debug,
        use_json=args.json,
        config=config
    )

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
