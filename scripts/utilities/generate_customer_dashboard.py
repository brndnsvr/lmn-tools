#!/usr/bin/env python3
"""
Customer Dashboard Generator for LogicMonitor

Generates EVPN customer dashboards with VNI status, alerts, and device health widgets.

Usage:
    python generate_customer_dashboard.py 638257
    python generate_customer_dashboard.py 638257 --name "Acme Corp"
    python generate_customer_dashboard.py --list  # List all customers
    python generate_customer_dashboard.py --delete 123  # Delete dashboard by ID
"""

import argparse
import re
import sys
from collections import defaultdict

import manage_lm_modules as lm


def get_customer_data(customer_id: str) -> dict:
    """Gather all data about a customer from VNI instances."""
    # Get all QFX devices in DXDFW group
    group_result = lm.api_request("GET", "/device/groups/37/devices?size=100")
    devices = group_result.get("data", group_result).get("items", [])

    customer_data = {
        "customer_id": customer_id,
        "vnis": [],
        "devices": set(),
        "device_ids": set(),
        "total_vni_count": 0,
    }

    for dev in devices:
        dev_id = dev["id"]
        dev_name = dev.get("displayName", str(dev_id))

        # Get EVPN VXLAN datasource
        dds_result = lm.api_request(
            "GET", f"/device/devices/{dev_id}/devicedatasources?size=100"
        )
        dds_items = dds_result.get("data", dds_result).get("items", [])

        for dds in dds_items:
            if dds.get("dataSourceName") == "Juniper_EVPN_VXLAN":
                dds_id = dds["id"]
                inst_result = lm.api_request(
                    "GET",
                    f"/device/devices/{dev_id}/devicedatasources/{dds_id}/instances?size=500",
                )
                instances = inst_result.get("data", inst_result).get("items", [])

                for inst in instances:
                    desc = inst.get("description", "")
                    match = re.search(r"Customer:\s*(\d+)", desc)
                    if match and match.group(1) == customer_id:
                        customer_data["vnis"].append(
                            {
                                "vni": inst.get("wildValue"),
                                "name": inst.get("displayName"),
                                "description": desc,
                                "device": dev_name,
                                "device_id": dev_id,
                                "instance_id": inst.get("id"),
                                "dds_id": dds_id,
                            }
                        )
                        customer_data["devices"].add(dev_name)
                        customer_data["device_ids"].add(dev_id)
                        customer_data["total_vni_count"] += 1
                break

    customer_data["devices"] = sorted(customer_data["devices"])
    customer_data["device_ids"] = sorted(customer_data["device_ids"])
    return customer_data


def list_all_customers() -> list[dict]:
    """List all customers found in VNI instances."""
    group_result = lm.api_request("GET", "/device/groups/37/devices?size=100")
    devices = group_result.get("data", group_result).get("items", [])

    customers = defaultdict(lambda: {"vni_count": 0, "devices": set()})

    for dev in devices:
        dev_id = dev["id"]
        dev_name = dev.get("displayName", str(dev_id))

        dds_result = lm.api_request(
            "GET", f"/device/devices/{dev_id}/devicedatasources?size=100"
        )
        for dds in dds_result.get("data", dds_result).get("items", []):
            if dds.get("dataSourceName") == "Juniper_EVPN_VXLAN":
                dds_id = dds["id"]
                inst_result = lm.api_request(
                    "GET",
                    f"/device/devices/{dev_id}/devicedatasources/{dds_id}/instances?size=500",
                )
                for inst in inst_result.get("data", inst_result).get("items", []):
                    desc = inst.get("description", "")
                    match = re.search(r"Customer:\s*(\d+)", desc)
                    if match:
                        cust_id = match.group(1)
                        customers[cust_id]["vni_count"] += 1
                        customers[cust_id]["devices"].add(dev_name)
                break

    return [
        {
            "customer_id": cid,
            "vni_count": data["vni_count"],
            "device_count": len(data["devices"]),
        }
        for cid, data in sorted(customers.items(), key=lambda x: -x[1]["vni_count"])
    ]


def create_noc_widget(customer_id: str, customer_name: str) -> dict:
    """Create NOC status widget showing VNI health."""
    return {
        "name": f"VNI Status - {customer_name}",
        "type": "noc",
        "theme": "newSolidDarkBlue",
        "interval": 3,
        "displaySettings": {"showTypeIcon": True, "displayAs": "table"},
        "items": [
            {
                "type": "device",
                "deviceGroupFullPath": "DXDFW",
                "deviceDisplayName": "*",
                "dataSourceDisplayName": "EVPN VXLAN",
                "instanceName": f"{customer_id}-*",
                "dataPointName": "Status",
                "groupBy": "instance",
                "name": "##INSTANCE##",
            }
        ],
        "sortBy": "alertSeverity",
        "displayColumn": 4,
        "displayWarnAlert": True,
        "displayErrorAlert": True,
        "displayCriticalAlert": True,
        "ackChecked": True,
        "sdtChecked": True,
    }


def create_alert_widget(customer_id: str, customer_name: str) -> dict:
    """Create alert list widget for customer."""
    return {
        "name": f"Active Alerts - {customer_name}",
        "type": "alert",
        "theme": "newSolidDarkBlue",
        "interval": 3,
        "displaySettings": {
            "isShowAll": False,
            "showFilter": False,
            "columns": [
                {"visible": True, "columnLabel": "Severity", "columnKey": "alert-severity"},
                {"visible": True, "columnLabel": "Began", "columnKey": "alert-began"},
                {"visible": True, "columnLabel": "Resource", "columnKey": "alert-device"},
                {"visible": True, "columnLabel": "Instance", "columnKey": "alert-datasource-instance"},
                {"visible": True, "columnLabel": "Datapoint", "columnKey": "alert-datapoint"},
                {"visible": True, "columnLabel": "Value", "columnKey": "alert-value"},
            ],
        },
        "filters": {
            "group": "DXDFW",
            "dataSource": "EVPN*",
            "instance": f"{customer_id}-*",
            "severity": "warn,error,critical",
        },
    }


def create_big_number_widget(customer_data: dict, customer_name: str) -> dict:
    """Create big number widget showing key metrics."""
    return {
        "name": f"Summary - {customer_name}",
        "type": "bigNumber",
        "theme": "newSolidDarkBlue",
        "interval": 5,
        "bigNumberInfo": {
            "dataPoints": [],
            "virtualDataPoints": [],
            "counters": [
                {
                    "name": "TotalVNIs",
                    "appliesTo": f'join(system.groups,",") =~ "DXDFW"',
                },
            ],
            "bigNumberItems": [
                {
                    "dataPointName": "TotalVNIs",
                    "bottomLabel": "",
                    "rightLabel": f"VNIs ({customer_data['total_vni_count']})",
                    "position": 1,
                    "rounding": 0,
                    "colorThresholds": None,
                    "useCommaSeparators": False,
                },
            ],
        },
    }


def create_device_noc_widget(customer_data: dict, customer_name: str) -> dict:
    """Create device-level NOC widget showing only devices with customer VNIs."""
    # Create items for each device that has this customer's VNIs
    items = []
    for device_name in sorted(customer_data["devices"])[:15]:  # Limit to 15 devices
        items.append({
            "type": "device",
            "deviceGroupFullPath": "DXDFW",
            "deviceDisplayName": device_name,
            "dataSourceDisplayName": "EVPN VTEPs",
            "instanceName": "*",
            "dataPointName": "Status",
            "groupBy": "device",
            "name": device_name,
        })

    return {
        "name": f"Device Health - {customer_name}",
        "type": "noc",
        "theme": "newSolidDarkBlue",
        "interval": 3,
        "displaySettings": {"showTypeIcon": True, "displayAs": "table"},
        "items": items if items else [{
            "type": "device",
            "deviceGroupFullPath": "DXDFW",
            "deviceDisplayName": "*",
            "dataSourceDisplayName": "EVPN VTEPs",
            "instanceName": "*",
            "dataPointName": "Status",
            "groupBy": "device",
            "name": "##RESOURCENAME##",
        }],
        "sortBy": "alertSeverity",
        "displayColumn": 3,
        "displayWarnAlert": True,
        "displayErrorAlert": True,
        "displayCriticalAlert": True,
        "ackChecked": True,
        "sdtChecked": True,
    }


def create_customer_dashboard(
    customer_id: str, customer_name: str | None = None, group_id: int | None = None
) -> int | None:
    """Create a complete customer dashboard with all widgets."""
    print(f"\n{'='*60}")
    print(f"Creating dashboard for Customer {customer_id}")
    print(f"{'='*60}")

    # Get customer data
    print("\nGathering customer data...")
    customer_data = get_customer_data(customer_id)

    if customer_data["total_vni_count"] == 0:
        print(f"ERROR: No VNIs found for customer {customer_id}")
        return None

    print(f"  VNIs: {customer_data['total_vni_count']}")
    print(f"  Devices: {len(customer_data['devices'])}")

    # Use provided name or generate one
    if not customer_name:
        customer_name = f"Customer {customer_id}"

    # Find or create dashboard group
    if not group_id:
        groups = lm.list_dashboard_groups()
        evpn_group = next(
            (g for g in groups if g.get("name") == "EVPN Customer Dashboards"), None
        )
        if evpn_group:
            group_id = evpn_group["id"]
        else:
            print("\nCreating dashboard group 'EVPN Customer Dashboards'...")
            group_id = lm.create_dashboard_group("EVPN Customer Dashboards", parent_id=1)
            if not group_id:
                print("ERROR: Failed to create dashboard group")
                return None

    # Create dashboard
    dashboard_name = f"EVPN - {customer_name}"
    description = (
        f"EVPN fabric monitoring for Customer {customer_id}. "
        f"{customer_data['total_vni_count']} VNIs across {len(customer_data['devices'])} devices."
    )

    print(f"\nCreating dashboard: {dashboard_name}")
    dashboard_id = lm.create_dashboard(
        name=dashboard_name,
        group_id=group_id,
        description=description,
        widget_tokens=[
            {"type": "owned", "name": "customerID", "value": customer_id, "inheritList": []},
        ],
    )

    if not dashboard_id:
        print("ERROR: Failed to create dashboard")
        return None

    print(f"  Dashboard ID: {dashboard_id}")

    # Create widgets
    widgets_created = []

    # Widget 1: VNI Status NOC (large, top)
    print("\nCreating VNI Status widget...")
    w1_id = lm.create_widget(dashboard_id, create_noc_widget(customer_id, customer_name))
    if w1_id:
        widgets_created.append((w1_id, {"col": 1, "row": 1, "sizex": 8, "sizey": 6}))
        print(f"  Widget ID: {w1_id}")

    # Widget 2: Alert List (right side)
    print("Creating Alert List widget...")
    w2_id = lm.create_widget(dashboard_id, create_alert_widget(customer_id, customer_name))
    if w2_id:
        widgets_created.append((w2_id, {"col": 9, "row": 1, "sizex": 4, "sizey": 6}))
        print(f"  Widget ID: {w2_id}")

    # Widget 3: Device Health NOC (bottom left)
    print("Creating Device Health widget...")
    w3_id = lm.create_widget(dashboard_id, create_device_noc_widget(customer_data, customer_name))
    if w3_id:
        widgets_created.append((w3_id, {"col": 1, "row": 7, "sizex": 6, "sizey": 4}))
        print(f"  Widget ID: {w3_id}")

    # Update widget positions
    if widgets_created:
        widgets_config = {str(wid): pos for wid, pos in widgets_created}
        print("\nUpdating widget positions...")
        lm.update_dashboard_widgets_config(dashboard_id, widgets_config)

    print(f"\n{'='*60}")
    print(f"Dashboard created successfully!")
    print(f"  ID: {dashboard_id}")
    print(f"  Name: {dashboard_name}")
    print(f"  Widgets: {len(widgets_created)}")
    print(f"{'='*60}")

    return dashboard_id


def main():
    parser = argparse.ArgumentParser(
        description="Generate EVPN customer dashboards in LogicMonitor"
    )
    parser.add_argument("customer_id", nargs="?", help="Customer ID to create dashboard for")
    parser.add_argument("--name", "-n", help="Customer name for dashboard title")
    parser.add_argument("--list", "-l", action="store_true", help="List all customers")
    parser.add_argument("--delete", "-d", type=int, help="Delete dashboard by ID")
    parser.add_argument("--group-id", "-g", type=int, help="Dashboard group ID")

    args = parser.parse_args()

    if args.list:
        print("\nFetching customer list...")
        customers = list_all_customers()
        print(f"\n{'Customer':<12} {'VNIs':<8} {'Devices':<10}")
        print("-" * 32)
        for c in customers[:20]:
            print(f"{c['customer_id']:<12} {c['vni_count']:<8} {c['device_count']:<10}")
        if len(customers) > 20:
            print(f"... and {len(customers) - 20} more customers")
        print(f"\nTotal: {len(customers)} customers")
        return

    if args.delete:
        print(f"\nDeleting dashboard {args.delete}...")
        if lm.delete_dashboard(args.delete):
            print("Dashboard deleted successfully")
        else:
            print("Failed to delete dashboard")
            sys.exit(1)
        return

    if not args.customer_id:
        parser.print_help()
        sys.exit(1)

    dashboard_id = create_customer_dashboard(
        args.customer_id, customer_name=args.name, group_id=args.group_id
    )

    if not dashboard_id:
        sys.exit(1)


if __name__ == "__main__":
    main()
