#!/usr/bin/env python3
"""
Routing Table Baseline Collector for Juniper Devices

Collects route table statistics from Juniper devices via SNMP to establish
baselines for LogicMonitor alerting thresholds. Supports SNMPv2c and SNMPv3.

The output can be used to set device properties in LogicMonitor:
  - routing.baseline.total
  - routing.baseline.bgp
  - routing.baseline.ospf
  - routing.baseline.static
  - routing.fib.limit (platform-specific)

Usage:
    python baseline-routes.py --host 192.168.1.1 --version 3 --user lm-monitor \
                              --auth-pass <pass> --priv-pass <pass>
    python baseline-routes.py --hosts-file routers.txt --output baselines.csv

Requirements:
    pip install pysnmp

Author: Network Automation Team
"""

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
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
        nextCmd,
        usmAesCfb128Protocol,
        usmHMACSHAAuthProtocol,
    )
except ImportError:
    print("Error: pysnmp not installed. Run: pip install pysnmp")
    sys.exit(1)


# SNMP OIDs for route table metrics
ROUTE_OIDS = {
    # Standard MIB OIDs
    "ipCidrRouteNumber": "1.3.6.1.2.1.4.24.6.0",  # Total IPv4 routes (IP-FORWARD-MIB)
    # Juniper-specific route table OIDs (jnxRtmTable)
    "jnxRtmTableRouteCount": "1.3.6.1.4.1.2636.3.48.1.1.1.2",  # Per-table route count
    "jnxRtmTableActiveRouteCount": "1.3.6.1.4.1.2636.3.48.1.1.1.3",
    "jnxRtmTableHiddenRouteCount": "1.3.6.1.4.1.2636.3.48.1.1.1.4",
    "jnxRtmTableName": "1.3.6.1.4.1.2636.3.48.1.1.1.1",
}

# Platform FIB limits (routes)
PLATFORM_FIB_LIMITS = {
    # MX Series (Memory dependent, Memory Type = Memoria)
    "MX80": 1000000,
    "MX104": 1000000,
    "MX204": 2000000,
    "MX240": 2000000,
    "MX480": 2000000,
    "MX960": 4000000,
    "MX10003": 4000000,
    "MX10008": 8000000,
    "MX10016": 16000000,
    # SRX Series
    "SRX300": 16000,
    "SRX320": 16000,
    "SRX340": 32000,
    "SRX345": 32000,
    "SRX380": 64000,
    "SRX550": 256000,
    "SRX1500": 512000,
    "SRX4100": 1000000,
    "SRX4200": 1000000,
    "SRX4600": 2000000,
    "SRX5400": 2000000,
    "SRX5600": 4000000,
    "SRX5800": 8000000,
    # QFX Series (not typically routing-heavy)
    "QFX5100": 128000,
    "QFX5110": 128000,
    "QFX5120": 256000,
    "QFX5200": 256000,
    "QFX10002": 512000,
    "QFX10008": 1000000,
    "QFX10016": 2000000,
    # EX Series
    "EX2300": 8000,
    "EX3400": 16000,
    "EX4300": 32000,
    "EX4400": 64000,
    "EX4600": 128000,
    "EX4650": 256000,
    "EX9200": 1000000,
    # Default for unknown platforms
    "default": 500000,
}


@dataclass
class RouteBaseline:
    """Route table baseline data for a device."""

    hostname: str
    ip_address: str
    platform: str = ""
    total_routes: int = 0
    active_routes: int = 0
    hidden_routes: int = 0
    bgp_routes: int = 0
    ospf_routes: int = 0
    isis_routes: int = 0
    static_routes: int = 0
    direct_routes: int = 0
    fib_limit: int = 0
    fib_utilization: float = 0.0
    routing_tables: dict[str, dict[str, int]] = field(default_factory=dict)
    timestamp: str = ""
    error: str | None = None


def get_snmp_auth(args: argparse.Namespace) -> CommunityData | UsmUserData:
    """Build SNMP authentication object based on version."""
    if args.version == "2c":
        return CommunityData(args.community)
    else:
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
) -> Any | None:
    """Perform SNMP GET and return value or None."""
    engine = SnmpEngine()

    error_indication, error_status, _, var_binds = next(
        getCmd(
            engine,
            auth,
            UdpTransportTarget((host, port), timeout=timeout, retries=2),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )
    )

    if error_indication or error_status:
        return None

    for var_bind in var_binds:
        _, value = var_bind
        value_str = value.prettyPrint()
        if "noSuch" in value_str:
            return None
        try:
            return int(value_str)
        except ValueError:
            return value_str

    return None


def snmp_walk(
    host: str,
    port: int,
    auth: CommunityData | UsmUserData,
    oid: str,
    timeout: int = 5,
) -> dict[str, Any]:
    """Perform SNMP WALK and return dict of OID suffix to value."""
    engine = SnmpEngine()
    results = {}

    for error_indication, error_status, _, var_binds in nextCmd(
        engine,
        auth,
        UdpTransportTarget((host, port), timeout=timeout, retries=2),
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
        lexicographicMode=False,
    ):
        if error_indication or error_status:
            break

        for var_bind in var_binds:
            oid_str, value = var_bind
            # Extract index from OID
            oid_parts = str(oid_str).split(".")
            index = oid_parts[-1] if oid_parts else "0"
            try:
                results[index] = int(value.prettyPrint())
            except ValueError:
                results[index] = value.prettyPrint()

    return results


def detect_platform(sys_descr: str) -> tuple[str, int]:
    """
    Detect platform type and FIB limit from sysDescr.

    Returns:
        Tuple of (platform_name, fib_limit)
    """
    sys_descr_upper = sys_descr.upper()

    # Check for specific models
    for model, limit in PLATFORM_FIB_LIMITS.items():
        if model.upper() in sys_descr_upper:
            return model, limit

    # Generic platform detection
    if "MX" in sys_descr_upper:
        return "MX-Unknown", PLATFORM_FIB_LIMITS["MX240"]
    elif "SRX" in sys_descr_upper:
        return "SRX-Unknown", PLATFORM_FIB_LIMITS["SRX1500"]
    elif "QFX" in sys_descr_upper:
        return "QFX-Unknown", PLATFORM_FIB_LIMITS["QFX5120"]
    elif "EX" in sys_descr_upper:
        return "EX-Unknown", PLATFORM_FIB_LIMITS["EX4300"]

    return "Unknown", PLATFORM_FIB_LIMITS["default"]


def collect_baseline(
    host: str,
    port: int,
    auth: CommunityData | UsmUserData,
    timeout: int,
) -> RouteBaseline:
    """
    Collect route table baseline from a device.

    Returns:
        RouteBaseline object with collected data.
    """
    baseline = RouteBaseline(
        hostname="",
        ip_address=host,
        timestamp=datetime.now().isoformat(),
    )

    # Get system info
    sys_descr = snmp_get(host, port, auth, "1.3.6.1.2.1.1.1.0", timeout)
    sys_name = snmp_get(host, port, auth, "1.3.6.1.2.1.1.5.0", timeout)

    if sys_descr is None:
        baseline.error = "SNMP not accessible"
        return baseline

    baseline.hostname = str(sys_name) if sys_name else host
    baseline.platform, baseline.fib_limit = detect_platform(str(sys_descr))

    # Get total route count from standard MIB
    total_routes = snmp_get(host, port, auth, ROUTE_OIDS["ipCidrRouteNumber"], timeout)
    if total_routes:
        baseline.total_routes = int(total_routes)

    # Walk Juniper route table for per-table stats
    table_names = snmp_walk(host, port, auth, ROUTE_OIDS["jnxRtmTableName"], timeout)
    table_counts = snmp_walk(host, port, auth, ROUTE_OIDS["jnxRtmTableRouteCount"], timeout)
    table_active = snmp_walk(host, port, auth, ROUTE_OIDS["jnxRtmTableActiveRouteCount"], timeout)
    table_hidden = snmp_walk(host, port, auth, ROUTE_OIDS["jnxRtmTableHiddenRouteCount"], timeout)

    # Process per-table data
    for index, name in table_names.items():
        table_data = {
            "total": table_counts.get(index, 0),
            "active": table_active.get(index, 0),
            "hidden": table_hidden.get(index, 0),
        }
        baseline.routing_tables[str(name)] = table_data

        # Aggregate counts
        baseline.active_routes += table_data["active"]
        baseline.hidden_routes += table_data["hidden"]

    # Use total from walk if standard MIB didn't work
    if baseline.total_routes == 0:
        baseline.total_routes = sum(t.get("total", 0) for t in baseline.routing_tables.values())

    # Calculate FIB utilization
    if baseline.fib_limit > 0:
        baseline.fib_utilization = round(
            (baseline.total_routes / baseline.fib_limit) * 100, 2
        )

    return baseline


def print_baseline(baseline: RouteBaseline, verbose: bool = False) -> None:
    """Print baseline data in human-readable format."""
    print(f"\n{'=' * 60}")
    print(f"Device: {baseline.hostname} ({baseline.ip_address})")
    print("=" * 60)

    if baseline.error:
        print(f"ERROR: {baseline.error}")
        return

    print(f"Platform:        {baseline.platform}")
    print(f"FIB Limit:       {baseline.fib_limit:,} routes")
    print(f"Timestamp:       {baseline.timestamp}")

    print(f"\n[Route Counts]")
    print(f"  Total Routes:  {baseline.total_routes:,}")
    print(f"  Active Routes: {baseline.active_routes:,}")
    print(f"  Hidden Routes: {baseline.hidden_routes:,}")
    print(f"  FIB Util:      {baseline.fib_utilization}%")

    if verbose and baseline.routing_tables:
        print(f"\n[Per-Table Breakdown]")
        for table_name, data in sorted(baseline.routing_tables.items()):
            print(f"  {table_name}:")
            print(f"    Total:  {data.get('total', 0):,}")
            print(f"    Active: {data.get('active', 0):,}")
            print(f"    Hidden: {data.get('hidden', 0):,}")

    print(f"\n[LogicMonitor Device Properties]")
    print(f"  routing.baseline.total = {baseline.total_routes}")
    print(f"  routing.baseline.active = {baseline.active_routes}")
    print(f"  routing.fib.limit = {baseline.fib_limit}")


def export_csv(baselines: list[RouteBaseline], output_file: Path) -> None:
    """Export baselines to CSV file."""
    fieldnames = [
        "hostname",
        "ip_address",
        "platform",
        "total_routes",
        "active_routes",
        "hidden_routes",
        "fib_limit",
        "fib_utilization",
        "timestamp",
        "error",
    ]

    with output_file.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for baseline in baselines:
            writer.writerow(
                {
                    "hostname": baseline.hostname,
                    "ip_address": baseline.ip_address,
                    "platform": baseline.platform,
                    "total_routes": baseline.total_routes,
                    "active_routes": baseline.active_routes,
                    "hidden_routes": baseline.hidden_routes,
                    "fib_limit": baseline.fib_limit,
                    "fib_utilization": baseline.fib_utilization,
                    "timestamp": baseline.timestamp,
                    "error": baseline.error or "",
                }
            )

    print(f"\nExported {len(baselines)} baselines to {output_file}")


def export_json(baselines: list[RouteBaseline], output_file: Path) -> None:
    """Export baselines to JSON file."""
    data = []
    for baseline in baselines:
        data.append(
            {
                "hostname": baseline.hostname,
                "ip_address": baseline.ip_address,
                "platform": baseline.platform,
                "total_routes": baseline.total_routes,
                "active_routes": baseline.active_routes,
                "hidden_routes": baseline.hidden_routes,
                "fib_limit": baseline.fib_limit,
                "fib_utilization": baseline.fib_utilization,
                "routing_tables": baseline.routing_tables,
                "timestamp": baseline.timestamp,
                "error": baseline.error,
                "lm_properties": {
                    "routing.baseline.total": baseline.total_routes,
                    "routing.baseline.active": baseline.active_routes,
                    "routing.fib.limit": baseline.fib_limit,
                },
            }
        )

    with output_file.open("w") as f:
        json.dump(data, f, indent=2)

    print(f"\nExported {len(baselines)} baselines to {output_file}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect routing table baselines from Juniper devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single device with SNMPv3
  %(prog)s --host 192.168.1.1 --version 3 --user lm-monitor \\
           --auth-pass myAuthPass --priv-pass myPrivPass

  # Multiple devices with CSV output
  %(prog)s --hosts-file routers.txt --version 3 --user lm-monitor \\
           --auth-pass myAuthPass --priv-pass myPrivPass \\
           --output baselines.csv

  # JSON output for automation
  %(prog)s --hosts-file routers.txt --version 2c --community public \\
           --output baselines.json --format json

Output can be used to set LogicMonitor device properties:
  - routing.baseline.total: Total route count baseline
  - routing.baseline.active: Active route count baseline
  - routing.fib.limit: Platform-specific FIB limit
        """,
    )

    # Host options
    host_group = parser.add_mutually_exclusive_group(required=True)
    host_group.add_argument("--host", help="Single host IP or hostname")
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
        help="SNMP community string for v2c",
    )

    # SNMPv3 options
    parser.add_argument("--user", help="SNMPv3 username")
    parser.add_argument("--auth-pass", help="SNMPv3 auth password")
    parser.add_argument("--priv-pass", help="SNMPv3 priv password")

    # Connection options
    parser.add_argument("--port", type=int, default=161, help="SNMP port")
    parser.add_argument("--timeout", type=int, default=10, help="SNMP timeout")

    # Output options
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for baselines (CSV or JSON)",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show per-table breakdown",
    )

    args = parser.parse_args()

    # Validate SNMPv3
    if args.version == "3":
        if not all([args.user, args.auth_pass, args.priv_pass]):
            parser.error("SNMPv3 requires --user, --auth-pass, and --priv-pass")

    auth = get_snmp_auth(args)

    # Get hosts
    hosts: list[str] = []
    if args.host:
        hosts = [args.host]
    else:
        if not args.hosts_file.exists():
            print(f"Error: File not found: {args.hosts_file}")
            return 1
        hosts = [
            line.strip()
            for line in args.hosts_file.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]

    print(f"Routing Table Baseline Collector")
    print(f"Collecting from {len(hosts)} device(s)...")

    # Collect baselines
    baselines: list[RouteBaseline] = []
    for host in hosts:
        try:
            baseline = collect_baseline(host, args.port, auth, args.timeout)
            baselines.append(baseline)
            print_baseline(baseline, args.verbose)
        except Exception as e:
            print(f"\nError collecting from {host}: {e}")
            baselines.append(
                RouteBaseline(
                    hostname="",
                    ip_address=host,
                    timestamp=datetime.now().isoformat(),
                    error=str(e),
                )
            )

    # Export if output specified
    if args.output:
        if args.format == "json":
            export_json(baselines, args.output)
        else:
            export_csv(baselines, args.output)

    # Summary
    success_count = sum(1 for b in baselines if not b.error)
    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {success_count}/{len(hosts)} devices collected successfully")
    print("=" * 60)

    return 0 if success_count == len(hosts) else 1


if __name__ == "__main__":
    sys.exit(main())
