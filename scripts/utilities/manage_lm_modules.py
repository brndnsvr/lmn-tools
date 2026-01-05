#!/usr/bin/env python3
"""
LogicMonitor Module Management Script

Manages DataSources and PropertySources via LogicMonitor REST API.
Supports list, delete, and create operations with LMv1 authentication.

Usage:
    export LM_ACCESS_ID="your_access_id"
    export LM_ACCESS_KEY="your_access_key"
    export LM_COMPANY="evoquedcs"

    python manage_lm_modules.py list datasources --filter "Juniper"
    python manage_lm_modules.py list propertysources --filter "SRX"
    python manage_lm_modules.py delete datasource 12345
    python manage_lm_modules.py create datasource configs/logicmonitor/datasource-evpn.json
    python manage_lm_modules.py create propertysource configs/logicmonitor/propertysource-cluster-detect.json
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

# Load .env file if it exists
ENV_FILE = Path(__file__).parent.parent / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                value = value.strip('"').strip("'")
                os.environ.setdefault(key.strip(), value)

LM_COMPANY = os.environ.get("LM_COMPANY", "evoquedcs")
LM_ACCESS_ID = os.environ.get("LM_ACCESS_ID")
LM_ACCESS_KEY = os.environ.get("LM_ACCESS_KEY")
LM_BASE_URL = f"https://{LM_COMPANY}.logicmonitor.com/santaba/rest"


def generate_auth_header(
    http_method: str, resource_path: str, data: str = ""
) -> dict[str, str]:
    """Generate LMv1 authentication header (hexdigest -> base64 method)."""
    epoch = str(int(time.time() * 1000))
    request_vars = f"{http_method}{epoch}{data}{resource_path}"

    hex_digest = hmac.new(
        LM_ACCESS_KEY.encode("utf-8"),
        msg=request_vars.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    signature = base64.b64encode(hex_digest.encode("utf-8")).decode("utf-8")

    return {
        "Content-Type": "application/json",
        "Authorization": f"LMv1 {LM_ACCESS_ID}:{signature}:{epoch}",
        "X-Version": "3",
    }


def api_request(
    method: str, endpoint: str, data: dict | None = None
) -> dict[str, Any]:
    """Make authenticated API request to LogicMonitor."""
    url = LM_BASE_URL + endpoint
    data_str = json.dumps(data) if data else ""

    # Resource path for signature excludes query parameters
    resource_path = endpoint.split("?")[0]
    headers = generate_auth_header(method.upper(), resource_path, data_str)

    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        data=data_str if data else None,
        timeout=60,
    )

    result = response.json()

    if response.status_code >= 400:
        error_msg = result.get("errorMessage", result.get("errmsg", str(result)))
        print(f"ERROR [{response.status_code}]: {error_msg}", file=sys.stderr)

    return result


def list_datasources(name_filter: str | None = None, limit: int = 50) -> list[dict]:
    """List DataSources, optionally filtered by name."""
    endpoint = f"/setting/datasources?size={limit}&fields=id,name,displayName,group,version"
    if name_filter:
        endpoint += f'&filter=name~"{name_filter}"'

    result = api_request("GET", endpoint)
    return result.get("items", result.get("data", {}).get("items", []))


def list_propertysources(
    name_filter: str | None = None, limit: int = 100
) -> list[dict]:
    """List PropertySources, optionally filtered by name."""
    endpoint = f"/setting/propertyrules?size={limit}&fields=id,name,displayName,group"
    if name_filter:
        endpoint += f'&filter=name~"{name_filter}"'

    result = api_request("GET", endpoint)
    return result.get("items", result.get("data", {}).get("items", []))


def delete_datasource(ds_id: int) -> bool:
    """Delete a DataSource by ID."""
    result = api_request("DELETE", f"/setting/datasources/{ds_id}")
    if result.get("errorMessage") or result.get("errmsg"):
        print(f"  FAILED: {result.get('errorMessage', result.get('errmsg'))}")
        return False
    print(f"Deleted DataSource ID {ds_id}")
    return True


def delete_propertysource(ps_id: int) -> bool:
    """Delete a PropertySource by ID."""
    result = api_request("DELETE", f"/setting/propertyrules/{ps_id}")
    if result.get("errorMessage") or result.get("errmsg"):
        print(f"  FAILED: {result.get('errorMessage', result.get('errmsg'))}")
        return False
    print(f"Deleted PropertySource ID {ps_id}")
    return True


def strip_local_fields(config: dict) -> dict:
    """Remove local-only fields (prefixed with _) before API calls."""
    return {k: v for k, v in config.items() if not k.startswith("_")}


def create_datasource(config_path: Path) -> int | None:
    """Create a DataSource from JSON config file. Returns ID if successful."""
    with open(config_path) as f:
        config = strip_local_fields(json.load(f))

    print(f"Creating DataSource: {config.get('name')}")
    print(f"  AppliesTo: {config.get('appliesTo', 'N/A')[:60]}...")

    result = api_request("POST", "/setting/datasources", config)

    # Check for actual error response (has errorMessage or errmsg field)
    if result.get("errorMessage") or result.get("errmsg"):
        print(f"  FAILED: {result.get('errorMessage', result.get('errmsg'))}")
        return None

    new_id = result.get("id", result.get("data", {}).get("id"))
    print(f"  SUCCESS: Created ID {new_id}")
    return new_id


def create_propertysource(config_path: Path) -> int | None:
    """Create a PropertySource from JSON config file. Returns ID if successful."""
    with open(config_path) as f:
        config = json.load(f)

    print(f"Creating PropertySource: {config.get('name')}")
    print(f"  AppliesTo: {config.get('appliesTo', 'N/A')[:60]}...")

    result = api_request("POST", "/setting/propertyrules", config)

    # Check for actual error response (has errorMessage or errmsg field)
    if result.get("errorMessage") or result.get("errmsg"):
        print(f"  FAILED: {result.get('errorMessage', result.get('errmsg'))}")
        return None

    new_id = result.get("id", result.get("data", {}).get("id"))
    print(f"  SUCCESS: Created ID {new_id}")
    return new_id


def update_datasource(ds_id: int, config_path: Path) -> bool:
    """Update an existing DataSource via PATCH. Preserves version history."""
    with open(config_path) as f:
        raw_config = json.load(f)

    # Get local version info before stripping
    local_version = raw_config.get("_version", "unknown")
    config = strip_local_fields(raw_config)

    print(f"Updating DataSource ID {ds_id}: {config.get('name')}")
    print(f"  Local version: {local_version}")

    result = api_request("PATCH", f"/setting/datasources/{ds_id}", config)

    if result.get("errorMessage") or result.get("errmsg"):
        print(f"  FAILED: {result.get('errorMessage', result.get('errmsg'))}")
        return False

    print(f"  SUCCESS: Updated DataSource {ds_id}")
    return True


def schedule_discovery(device_id: int) -> bool:
    """Schedule Active Discovery for a device."""
    result = api_request("POST", f"/device/devices/{device_id}/scheduleAutoDiscovery")
    if result.get("errorMessage") or result.get("errmsg"):
        print(f"  FAILED: {result.get('errorMessage', result.get('errmsg'))}")
        return False
    print(f"Scheduled Active Discovery for device {device_id}")
    return True


def get_device_instances(device_id: int, datasource_id: int) -> list[dict]:
    """Get instances for a device/datasource combination."""
    endpoint = f"/device/devices/{device_id}/devicedatasources/{datasource_id}/instances"
    result = api_request("GET", endpoint)
    return result.get("items", result.get("data", {}).get("items", []))


def get_device_datasource(device_id: int, datasource_name: str) -> dict | None:
    """Get device datasource by name."""
    endpoint = f"/device/devices/{device_id}/devicedatasources?filter=dataSourceName:\"{datasource_name}\""
    result = api_request("GET", endpoint)
    items = result.get("items", result.get("data", {}).get("items", []))
    return items[0] if items else None


def get_device_datasource_details(device_id: int, dd_id: int) -> dict:
    """Get detailed info about a device datasource."""
    endpoint = f"/device/devices/{device_id}/devicedatasources/{dd_id}"
    return api_request("GET", endpoint)


def test_script(device_id: int, datasource_id: int, script_type: str = "ad_script") -> dict:
    """Run test script via API and get output.

    script_type: 'ad_script' for discovery, 'collect_script' for collection
    """
    endpoint = f"/debug?hostId={device_id}&cmdline=!{script_type},{datasource_id}"
    return api_request("GET", endpoint)


def get_collector_debug(collector_id: int, cmd: str) -> dict:
    """Run debug command on a collector."""
    endpoint = f"/debug?collectorId={collector_id}&cmdline={cmd}"
    return api_request("GET", endpoint)


def run_groovy_on_collector(collector_id: int, device_id: int, groovy_code: str) -> dict:
    """Execute Groovy script on collector for a device."""
    import urllib.parse
    encoded = urllib.parse.quote(groovy_code)
    endpoint = f"/debug?collectorId={collector_id}&hostId={device_id}&cmdline=!groovy%20{encoded}"
    return api_request("GET", endpoint)


def get_device_properties(device_id: int, filter_prefix: str | None = None) -> list[dict]:
    """Get device properties, optionally filtered by prefix."""
    endpoint = f"/device/devices/{device_id}/properties?size=200"
    if filter_prefix:
        endpoint += f'&filter=name~"{filter_prefix}"'
    result = api_request("GET", endpoint)
    return result.get("items", result.get("data", {}).get("items", []))


def set_device_property(device_id: int, name: str, value: str) -> bool:
    """Set or update a device property."""
    # First check if property exists
    props = get_device_properties(device_id)
    existing = next((p for p in props if p.get("name") == name), None)

    if existing:
        # Update existing property
        prop_id = existing.get("id")
        endpoint = f"/device/devices/{device_id}/properties/{prop_id}"
        data = {"name": name, "value": value}
        result = api_request("PATCH", endpoint, data)
    else:
        # Create new property
        endpoint = f"/device/devices/{device_id}/properties"
        data = {"name": name, "value": value}
        result = api_request("POST", endpoint, data)

    if result.get("errorMessage") or result.get("errmsg"):
        print(f"  FAILED: {result.get('errorMessage', result.get('errmsg'))}")
        return False
    return True


def get_device_info(device_id: int) -> dict:
    """Get basic device info."""
    endpoint = f"/device/devices/{device_id}"
    return api_request("GET", endpoint)


# =============================================================================
# Dashboard API Functions
# =============================================================================


def list_dashboards(name_filter: str | None = None, limit: int = 50) -> list[dict]:
    """List dashboards, optionally filtered by name."""
    endpoint = f"/dashboard/dashboards?size={limit}"
    if name_filter:
        endpoint += f'&filter=name~"{name_filter}"'
    result = api_request("GET", endpoint)
    return result.get("items", result.get("data", {}).get("items", []))


def get_dashboard(dashboard_id: int) -> dict:
    """Get dashboard by ID."""
    endpoint = f"/dashboard/dashboards/{dashboard_id}"
    return api_request("GET", endpoint)


def create_dashboard(
    name: str,
    group_id: int = 1,
    description: str = "",
    widget_tokens: list[dict] | None = None,
) -> int | None:
    """Create a new dashboard. Returns dashboard ID if successful."""
    data = {
        "name": name,
        "groupId": group_id,
        "description": description,
        "sharable": True,
        "widgetTokens": widget_tokens or [],
    }
    result = api_request("POST", "/dashboard/dashboards", data)
    if result.get("errorMessage") or result.get("errmsg"):
        print(f"  FAILED: {result.get('errorMessage', result.get('errmsg'))}")
        return None
    return result.get("id", result.get("data", {}).get("id"))


def update_dashboard(dashboard_id: int, data: dict) -> bool:
    """Update an existing dashboard."""
    result = api_request("PATCH", f"/dashboard/dashboards/{dashboard_id}", data)
    if result.get("errorMessage") or result.get("errmsg"):
        print(f"  FAILED: {result.get('errorMessage', result.get('errmsg'))}")
        return False
    return True


def delete_dashboard(dashboard_id: int) -> bool:
    """Delete a dashboard by ID."""
    result = api_request("DELETE", f"/dashboard/dashboards/{dashboard_id}")
    if result.get("errorMessage") or result.get("errmsg"):
        print(f"  FAILED: {result.get('errorMessage', result.get('errmsg'))}")
        return False
    return True


def list_dashboard_groups(name_filter: str | None = None, limit: int = 50) -> list[dict]:
    """List dashboard groups."""
    endpoint = f"/dashboard/groups?size={limit}"
    result = api_request("GET", endpoint)
    return result.get("items", result.get("data", {}).get("items", []))


def create_dashboard_group(name: str, parent_id: int = 1) -> int | None:
    """Create a dashboard group. Returns group ID if successful."""
    data = {"name": name, "parentId": parent_id}
    result = api_request("POST", "/dashboard/groups", data)
    if result.get("errorMessage") or result.get("errmsg"):
        print(f"  FAILED: {result.get('errorMessage', result.get('errmsg'))}")
        return None
    return result.get("id", result.get("data", {}).get("id"))


def get_dashboard_widgets(dashboard_id: int) -> list[dict]:
    """Get all widgets for a dashboard."""
    endpoint = f"/dashboard/widgets?dashboardId={dashboard_id}&size=100"
    result = api_request("GET", endpoint)
    return result.get("items", result.get("data", {}).get("items", []))


def create_widget(dashboard_id: int, widget_config: dict) -> int | None:
    """Create a widget on a dashboard. Returns widget ID if successful."""
    widget_config["dashboardId"] = dashboard_id
    result = api_request("POST", "/dashboard/widgets", widget_config)
    if result.get("errorMessage") or result.get("errmsg"):
        print(f"  FAILED: {result.get('errorMessage', result.get('errmsg'))}")
        return None
    return result.get("id", result.get("data", {}).get("id"))


def delete_widget(widget_id: int) -> bool:
    """Delete a widget by ID."""
    result = api_request("DELETE", f"/dashboard/widgets/{widget_id}")
    if result.get("errorMessage") or result.get("errmsg"):
        return False
    return True


def update_dashboard_widgets_config(dashboard_id: int, widgets_config: dict) -> bool:
    """Update widget positions/sizes on a dashboard."""
    return update_dashboard(dashboard_id, {"widgetsConfig": widgets_config})


def cmd_list(args):
    """Handle 'list' command."""
    if args.type == "datasources":
        items = list_datasources(args.filter, args.limit)
        print(f"\nDataSources ({len(items)} found):")
        print("-" * 70)
        for item in items:
            print(f"  ID: {item['id']:<10} Name: {item['name']}")
    elif args.type == "propertysources":
        items = list_propertysources(args.filter, args.limit)
        print(f"\nPropertySources ({len(items)} found):")
        print("-" * 70)
        for item in items:
            print(f"  ID: {item['id']:<10} Name: {item['name']}")


def cmd_delete(args):
    """Handle 'delete' command."""
    if args.type == "datasource":
        delete_datasource(args.id)
    elif args.type == "propertysource":
        delete_propertysource(args.id)


def cmd_create(args):
    """Handle 'create' command."""
    config_path = Path(args.file)
    if not config_path.exists():
        print(f"ERROR: File not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    if args.type == "datasource":
        create_datasource(config_path)
    elif args.type == "propertysource":
        create_propertysource(config_path)


def cmd_update(args):
    """Handle 'update' command."""
    config_path = Path(args.file)
    if not config_path.exists():
        print(f"ERROR: File not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    if args.type == "datasource":
        update_datasource(args.id, config_path)
    else:
        print(f"ERROR: Update not supported for {args.type}", file=sys.stderr)
        sys.exit(1)


def cmd_device(args):
    """Get device info and properties."""
    device_id = args.device_id

    print(f"\n=== Device Info ===")
    info = get_device_info(device_id)
    print(f"ID: {info.get('id')}")
    print(f"Name: {info.get('displayName', info.get('name'))}")
    print(f"Collector: {info.get('preferredCollectorId')}")

    # Get SSH-related properties
    print(f"\n=== SSH Properties ===")
    ssh_props = get_device_properties(device_id, "ssh")
    if ssh_props:
        for prop in ssh_props:
            name = prop.get("name")
            value = prop.get("value", "")
            # Mask passwords
            if "pass" in name.lower() or "key" in name.lower():
                display = "****" if value else "(not set)"
            else:
                display = value or "(not set)"
            print(f"  {name}: {display}")
    else:
        print("  No SSH properties found!")

    # Check for system.ips
    print(f"\n=== System Properties ===")
    sys_props = get_device_properties(device_id, "system")
    for prop in sys_props[:10]:
        name = prop.get("name")
        if name in ["system.ips", "system.hostname", "system.sysinfo", "system.deviceId"]:
            print(f"  {name}: {prop.get('value', 'N/A')[:60]}")


def cmd_status(args):
    """Get detailed status of a device datasource."""
    device_id = args.device_id
    datasource_name = args.datasource_name

    print(f"\n=== Device DataSource Status ===")
    print(f"Device ID: {device_id}")
    print(f"DataSource: {datasource_name}")

    dd = get_device_datasource(device_id, datasource_name)
    if not dd:
        print(f"\nDataSource '{datasource_name}' not found on device {device_id}")
        return

    dd_id = dd.get("id")
    print(f"\nDeviceDataSource ID: {dd_id}")

    # Get detailed info
    details = get_device_datasource_details(device_id, dd_id)
    print(f"\nStatus Info:")
    for key in ["status", "alertStatus", "alertDisableStatus", "monitorStatus",
                "nextAutoDiscoveryOn", "autoDiscoveryStatus", "autoDiscoveryInstance"]:
        if key in details:
            print(f"  {key}: {details.get(key)}")

    # Show any errors
    for key in ["alertStatusPriority", "stopMonitoring", "stopMonitoringReason"]:
        if details.get(key):
            print(f"  {key}: {details.get(key)}")

    # Get instances
    instances = get_device_instances(device_id, dd_id)
    print(f"\nInstances: {len(instances)}")
    for inst in instances[:5]:
        print(f"  - {inst.get('displayName', inst.get('name'))} (ID: {inst.get('id')})")
    if len(instances) > 5:
        print(f"  ... and {len(instances) - 5} more")


def cmd_discover(args):
    """Trigger Active Discovery and check instances."""
    device_id = args.device_id
    datasource_name = args.datasource_name

    print(f"\n=== Active Discovery Test ===")
    print(f"Device ID: {device_id}")
    print(f"DataSource: {datasource_name}")

    # Get device datasource
    dd = get_device_datasource(device_id, datasource_name)
    if not dd:
        print(f"\nDataSource '{datasource_name}' not found on device {device_id}")
        return

    dd_id = dd.get("id")
    print(f"\nDeviceDataSource ID: {dd_id}")

    # Get current instances before discovery
    instances_before = get_device_instances(device_id, dd_id)
    print(f"Instances before discovery: {len(instances_before)}")
    for inst in instances_before[:5]:
        print(f"  - {inst.get('displayName', inst.get('name'))}")
    if len(instances_before) > 5:
        print(f"  ... and {len(instances_before) - 5} more")

    # Schedule discovery
    print("\nScheduling Active Discovery...")
    schedule_discovery(device_id)

    # Wait and poll for new instances
    print(f"\nWaiting {args.wait}s for discovery to complete...")
    import time
    time.sleep(args.wait)

    # Get instances after discovery
    instances_after = get_device_instances(device_id, dd_id)
    print(f"Instances after discovery: {len(instances_after)}")
    for inst in instances_after[:10]:
        print(f"  - {inst.get('displayName', inst.get('name'))}")
    if len(instances_after) > 10:
        print(f"  ... and {len(instances_after) - 10} more")

    # Summary
    new_count = len(instances_after) - len(instances_before)
    if new_count > 0:
        print(f"\n✓ Discovery found {new_count} new instances!")
    elif len(instances_after) > 0:
        print(f"\n• {len(instances_after)} instances (no new instances found)")
    else:
        print(f"\n✗ No instances discovered - check script for errors")


def cmd_deploy_all(args):
    """Deploy all Juniper modules in correct order."""
    config_dir = Path(__file__).parent.parent / "configs" / "logicmonitor"

    print("=" * 60)
    print("Deploying Juniper LogicModules")
    print("=" * 60)

    # Step 1: PropertySource first (sets properties for DataSources)
    ps_path = config_dir / "propertysource-cluster-detect.json"
    if ps_path.exists():
        print("\n[1/4] PropertySource...")
        create_propertysource(ps_path)
    else:
        print(f"\n[1/4] SKIP: {ps_path} not found")

    # Step 2: DataSources
    datasources = [
        ("datasource-routing.json", "[2/4] Routing Table"),
        ("datasource-evpn.json", "[3/4] EVPN-VXLAN"),
        ("datasource-cluster.json", "[4/4] Chassis Cluster"),
    ]

    for filename, label in datasources:
        ds_path = config_dir / filename
        if ds_path.exists():
            print(f"\n{label}...")
            create_datasource(ds_path)
        else:
            print(f"\n{label} SKIP: {ds_path} not found")

    print("\n" + "=" * 60)
    print("Deployment complete. Verify in LogicMonitor UI.")
    print("=" * 60)


def main():
    if not LM_ACCESS_ID or not LM_ACCESS_KEY:
        print("ERROR: Set LM_ACCESS_ID and LM_ACCESS_KEY environment variables")
        print("  Or create a .env file in the project root")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Manage LogicMonitor DataSources and PropertySources"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List modules")
    list_parser.add_argument(
        "type", choices=["datasources", "propertysources"], help="Module type"
    )
    list_parser.add_argument("--filter", "-f", help="Filter by name (contains)")
    list_parser.add_argument(
        "--limit", "-n", type=int, default=50, help="Max results"
    )
    list_parser.set_defaults(func=cmd_list)

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a module by ID")
    delete_parser.add_argument(
        "type", choices=["datasource", "propertysource"], help="Module type"
    )
    delete_parser.add_argument("id", type=int, help="Module ID to delete")
    delete_parser.set_defaults(func=cmd_delete)

    # Create command
    create_parser = subparsers.add_parser("create", help="Create module from JSON")
    create_parser.add_argument(
        "type", choices=["datasource", "propertysource"], help="Module type"
    )
    create_parser.add_argument("file", help="JSON config file path")
    create_parser.set_defaults(func=cmd_create)

    # Update command
    update_parser = subparsers.add_parser("update", help="Update existing module via PATCH")
    update_parser.add_argument(
        "type", choices=["datasource"], help="Module type (only datasource supported)"
    )
    update_parser.add_argument("id", type=int, help="Module ID to update")
    update_parser.add_argument("file", help="JSON config file path")
    update_parser.set_defaults(func=cmd_update)

    # Deploy all command
    deploy_parser = subparsers.add_parser(
        "deploy", help="Deploy all Juniper modules"
    )
    deploy_parser.set_defaults(func=cmd_deploy_all)

    # Discover command - trigger Active Discovery and check instances
    discover_parser = subparsers.add_parser(
        "discover", help="Trigger Active Discovery and check instances"
    )
    discover_parser.add_argument("device_id", type=int, help="Device ID")
    discover_parser.add_argument("datasource_name", help="DataSource name")
    discover_parser.add_argument(
        "--wait", "-w", type=int, default=60, help="Seconds to wait for discovery"
    )
    discover_parser.set_defaults(func=cmd_discover)

    # Status command - get device datasource status
    status_parser = subparsers.add_parser(
        "status", help="Get device datasource status and details"
    )
    status_parser.add_argument("device_id", type=int, help="Device ID")
    status_parser.add_argument("datasource_name", help="DataSource name")
    status_parser.set_defaults(func=cmd_status)

    # Device command - show device info and properties
    device_parser = subparsers.add_parser(
        "device", help="Get device info and SSH properties"
    )
    device_parser.add_argument("device_id", type=int, help="Device ID")
    device_parser.set_defaults(func=cmd_device)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
