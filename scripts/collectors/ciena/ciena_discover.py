#!/usr/bin/env python3
"""
Ciena WaveServer Active Discovery Script for LogicMonitor

This script discovers optical interfaces (PTPs and Ports) on Ciena WaveServer
optical transport devices via NETCONF and outputs them in LogicMonitor's
Active Discovery format.

Usage:
    ciena_discover.py <hostname> <username> <password> [--port PORT] [--debug]

Output Format:
    instance_id##instance_name##description####auto.prop1=val1&auto.prop2=val2

Exit Codes:
    0 = Success (instances found or legitimately empty)
    1 = Error (connection failure, authentication error, etc.)

LogicMonitor DataSource Configuration:
    Active Discovery Method: Script
    Script: Upload this file
    Parameters: ##system.hostname## ##netconf.user## ##netconf.pass## ##netconf.port##
"""

import argparse
import logging
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
    Load the Ciena configuration YAML file.

    Args:
        config_path: Optional path to config file. If not provided,
                    uses default location relative to script.

    Returns:
        Configuration dictionary
    """
    if config_path is None:
        config_path = project_root / "configs" / "ciena.yaml"

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


def discover_interfaces(
    hostname: str,
    username: str,
    password: str,
    port: int = 830,
    debug: bool = False,
    config: dict = None
) -> int:
    """
    Discover interfaces on a Ciena WaveServer device and output in LogicMonitor format.

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

    # Create formatter for output
    formatter = OutputFormatter(debug=debug)

    try:
        # Connect to device
        logger.debug(f"Connecting to {hostname}:{port}")

        with NetconfClient(
            hostname=hostname,
            username=username,
            password=password,
            port=port,
            device_type="ciena",
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

            # Parse response to discover instances
            logger.debug("Parsing NETCONF response")
            parser = XmlParser(
                namespaces=config.get('namespaces', {}),
                debug=debug
            )

            instances = parser.discover_instances(data, config)

            logger.debug(f"Discovered {len(instances)} instances")

            # Output in LogicMonitor format
            if instances:
                formatter.write_discovery(instances)
            else:
                # Empty output with exit 0 is valid (no interfaces)
                # LogicMonitor will clear all instances
                logger.warning("No interfaces discovered on device")

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
        description='Discover optical interfaces on Ciena WaveServer devices via NETCONF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic discovery
    %(prog)s device.example.com admin password123

    # With custom port
    %(prog)s device.example.com admin password123 --port 22830

    # With debug output
    %(prog)s device.example.com admin password123 --debug

Exit Codes:
    0 = Success (instances output to stdout)
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

    exit_code = discover_interfaces(
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
