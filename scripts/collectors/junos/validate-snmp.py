#!/usr/bin/env python3
"""
SNMP Connectivity Validator for Juniper Devices

Tests SNMP connectivity and validates that key OIDs are accessible
for LogicMonitor monitoring. Supports SNMPv2c and SNMPv3.

Usage:
    python validate-snmp.py --host 192.168.1.1 --version 2c --community public
    python validate-snmp.py --host 192.168.1.1 --version 3 --user lm-monitor \
                            --auth-pass <pass> --priv-pass <pass>
    python validate-snmp.py --hosts-file hosts.txt --version 3 ...

Requirements:
    pip install pysnmp

Author: Network Automation Team
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from pysnmp.hlapi import (
        CommunityData,
        ContextData,
        ObjectIdentity,
        ObjectType,
        SnmpEngine,
        UdpTransportTarget,
        UsmUserData,
        getCmd,
        usmAesCfb128Protocol,
        usmHMACSHAAuthProtocol,
    )
except ImportError:
    print("Error: pysnmp not installed. Run: pip install pysnmp")
    sys.exit(1)


# Key OIDs to validate for Juniper devices
VALIDATION_OIDS = {
    "sysDescr": "1.3.6.1.2.1.1.1.0",
    "sysName": "1.3.6.1.2.1.1.5.0",
    "sysUpTime": "1.3.6.1.2.1.1.3.0",
    # Juniper-specific OIDs
    "jnxBoxDescr": "1.3.6.1.4.1.2636.3.1.2.0",
    "jnxBoxSerialNo": "1.3.6.1.4.1.2636.3.1.3.0",
}

# Platform-specific OIDs to test based on device type
PLATFORM_OIDS = {
    "SRX": {
        "jnxJsChassisClusterSwitchoverCount": "1.3.6.1.4.1.2636.3.39.1.13.1.1.1.8.0",
        "jnxSPUMonitoringCurrentFlowSession": "1.3.6.1.4.1.2636.3.39.1.12.1.1.1.6.0",
    },
    "QFX": {
        "jnxVirtualChassisMemberRole": "1.3.6.1.4.1.2636.3.40.1.4.1.1.1.3.0",
    },
    "MX": {
        "jnxOperatingTemp": "1.3.6.1.4.1.2636.3.1.13.1.7.9.1.0.0",
        "ipCidrRouteNumber": "1.3.6.1.2.1.4.24.6.0",
    },
    "EX": {
        "jnxVirtualChassisMemberRole": "1.3.6.1.4.1.2636.3.40.1.4.1.1.1.3.0",
    },
}


@dataclass
class SNMPResult:
    """Result of an SNMP query."""

    oid_name: str
    oid: str
    value: Any
    success: bool
    error: str | None = None


def get_snmp_auth(args: argparse.Namespace) -> CommunityData | UsmUserData:
    """Build SNMP authentication object based on version."""
    if args.version == "2c":
        return CommunityData(args.community)
    else:
        # SNMPv3 with SHA/AES
        return UsmUserData(
            args.user,
            args.auth_pass,
            args.priv_pass,
            authProtocol=usmHMACSHAAuthProtocol,
            privProtocol=usmAesCfb128Protocol,
        )


def snmp_get(
    host: str,
    port: int,
    auth: CommunityData | UsmUserData,
    oid: str,
    timeout: int = 5,
    retries: int = 2,
) -> tuple[Any, str | None]:
    """
    Perform SNMP GET request.

    Returns:
        Tuple of (value, error_message). Value is None if error occurred.
    """
    engine = SnmpEngine()

    error_indication, error_status, error_index, var_binds = next(
        getCmd(
            engine,
            auth,
            UdpTransportTarget((host, port), timeout=timeout, retries=retries),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )
    )

    if error_indication:
        return None, str(error_indication)
    elif error_status:
        return None, f"{error_status.prettyPrint()} at {error_index}"
    else:
        for var_bind in var_binds:
            _, value = var_bind
            # Check for noSuchInstance or noSuchObject
            value_str = str(value)
            if "noSuch" in value_str:
                return None, value_str
            return value.prettyPrint(), None

    return None, "Unknown error"


def validate_host(
    host: str,
    port: int,
    auth: CommunityData | UsmUserData,
    timeout: int,
    verbose: bool = False,
) -> dict[str, SNMPResult]:
    """
    Validate SNMP connectivity to a host.

    Returns:
        Dictionary of OID name to SNMPResult.
    """
    results: dict[str, SNMPResult] = {}

    # Test basic OIDs first
    print(f"\n{'=' * 60}")
    print(f"Testing host: {host}")
    print("=" * 60)

    print("\n[Basic System OIDs]")
    device_type = None

    for oid_name, oid in VALIDATION_OIDS.items():
        value, error = snmp_get(host, port, auth, oid, timeout)
        success = value is not None

        results[oid_name] = SNMPResult(
            oid_name=oid_name,
            oid=oid,
            value=value,
            success=success,
            error=error,
        )

        status = "✓" if success else "✗"
        if success:
            # Detect device type from sysDescr
            if oid_name == "sysDescr" and value:
                for platform in ["SRX", "QFX", "MX", "EX"]:
                    if platform in str(value):
                        device_type = platform
                        break

            if verbose:
                print(f"  {status} {oid_name}: {value}")
            else:
                # Truncate long values
                display_value = str(value)[:50] + "..." if len(str(value)) > 50 else value
                print(f"  {status} {oid_name}: {display_value}")
        else:
            print(f"  {status} {oid_name}: FAILED - {error}")

    # Test platform-specific OIDs if device type detected
    if device_type and device_type in PLATFORM_OIDS:
        print(f"\n[{device_type}-Specific OIDs]")
        for oid_name, oid in PLATFORM_OIDS[device_type].items():
            value, error = snmp_get(host, port, auth, oid, timeout)
            success = value is not None and "noSuch" not in str(error or "")

            results[oid_name] = SNMPResult(
                oid_name=oid_name,
                oid=oid,
                value=value,
                success=success,
                error=error,
            )

            status = "✓" if success else "○"  # Use ○ for optional OIDs
            if success:
                print(f"  {status} {oid_name}: {value}")
            else:
                print(f"  {status} {oid_name}: Not available ({error})")

    # Summary
    basic_success = sum(1 for r in results.values() if r.success and r.oid_name in VALIDATION_OIDS)
    basic_total = len(VALIDATION_OIDS)

    print(f"\nSummary: {basic_success}/{basic_total} basic OIDs accessible")

    if device_type:
        print(f"Detected platform: {device_type}")

    return results


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate SNMP connectivity to Juniper devices for LogicMonitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test single host with SNMPv2c
  %(prog)s --host 192.168.1.1 --version 2c --community public

  # Test single host with SNMPv3
  %(prog)s --host 192.168.1.1 --version 3 --user lm-monitor \\
           --auth-pass myAuthPass --priv-pass myPrivPass

  # Test multiple hosts from file
  %(prog)s --hosts-file hosts.txt --version 3 --user lm-monitor \\
           --auth-pass myAuthPass --priv-pass myPrivPass

  # Verbose output with custom timeout
  %(prog)s --host 192.168.1.1 --version 2c --community public -v --timeout 10
        """,
    )

    # Host options (mutually exclusive)
    host_group = parser.add_mutually_exclusive_group(required=True)
    host_group.add_argument("--host", help="Single host IP or hostname to test")
    host_group.add_argument(
        "--hosts-file",
        type=Path,
        help="File containing list of hosts (one per line)",
    )

    # SNMP version
    parser.add_argument(
        "--version",
        choices=["2c", "3"],
        default="3",
        help="SNMP version (default: 3)",
    )

    # SNMPv2c options
    parser.add_argument(
        "--community",
        default="public",
        help="SNMP community string for v2c (default: public)",
    )

    # SNMPv3 options
    parser.add_argument("--user", help="SNMPv3 username (security name)")
    parser.add_argument("--auth-pass", help="SNMPv3 authentication password")
    parser.add_argument("--priv-pass", help="SNMPv3 privacy password")

    # Connection options
    parser.add_argument(
        "--port",
        type=int,
        default=161,
        help="SNMP port (default: 161)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="SNMP timeout in seconds (default: 5)",
    )

    # Output options
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output (show full OID values)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Validate SNMPv3 arguments
    if args.version == "3":
        if not all([args.user, args.auth_pass, args.priv_pass]):
            parser.error("SNMPv3 requires --user, --auth-pass, and --priv-pass")

    # Get authentication
    auth = get_snmp_auth(args)

    # Get list of hosts
    hosts: list[str] = []
    if args.host:
        hosts = [args.host]
    else:
        if not args.hosts_file.exists():
            print(f"Error: Hosts file not found: {args.hosts_file}")
            return 1
        hosts = [
            line.strip()
            for line in args.hosts_file.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]

    if not hosts:
        print("Error: No hosts to test")
        return 1

    print(f"SNMP Connectivity Validator")
    print(f"Testing {len(hosts)} host(s) with SNMP{args.version}")

    # Test each host
    all_results: dict[str, dict[str, SNMPResult]] = {}
    success_count = 0

    for host in hosts:
        try:
            results = validate_host(host, args.port, auth, args.timeout, args.verbose)
            all_results[host] = results

            # Count as success if at least sysDescr is accessible
            if results.get("sysDescr", SNMPResult("", "", None, False)).success:
                success_count += 1
        except Exception as e:
            print(f"\nError testing {host}: {e}")
            all_results[host] = {}

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"FINAL SUMMARY: {success_count}/{len(hosts)} hosts accessible via SNMP")
    print("=" * 60)

    # JSON output if requested
    if args.json:
        import json

        json_output = {
            host: {
                name: {
                    "oid": r.oid,
                    "value": r.value,
                    "success": r.success,
                    "error": r.error,
                }
                for name, r in results.items()
            }
            for host, results in all_results.items()
        }
        print("\nJSON Output:")
        print(json.dumps(json_output, indent=2))

    return 0 if success_count == len(hosts) else 1


if __name__ == "__main__":
    sys.exit(main())
