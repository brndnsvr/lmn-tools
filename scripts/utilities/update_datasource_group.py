#!/usr/bin/env python3
"""
Update LogicMonitor DataSource group field via REST API.
Bypasses UI validation by sending only the fields we want to change.

Usage:
    python update_datasource_group.py

Requires environment variables:
    LM_ACCOUNT   - Your LogicMonitor account name (e.g., 'evoquedcs')
    LM_ACCESS_ID - API Access ID
    LM_ACCESS_KEY - API Access Key
"""

import hashlib
import base64
import hmac
import time
import requests
import os
import json

# Configuration
ACCOUNT = os.environ.get("LM_ACCOUNT", "evoquedcs")
ACCESS_ID = os.environ.get("LM_ACCESS_ID")
ACCESS_KEY = os.environ.get("LM_ACCESS_KEY")

# DataSources to update
DATASOURCES = [
    {"id": 21328171, "name": "Infinera_Port_Status", "displayName": "Client Port Health"},
    {"id": 21328172, "name": "Infinera_Line_Port_Health", "displayName": "Line Port Health"},
    {"id": 21328173, "name": "Infinera_Chassis_Health", "displayName": "Chassis Health"},
]

NEW_GROUP = "SNMP"


def generate_auth_header(http_method: str, resource_path: str, data: str = "") -> str:
    """Generate LMv1 authentication header."""
    timestamp = str(int(time.time() * 1000))

    # Build signature string
    signature_string = f"{http_method}{timestamp}{data}{resource_path}"

    # Create HMAC-SHA256 signature
    signature = base64.b64encode(
        hmac.new(
            ACCESS_KEY.encode("utf-8"),
            signature_string.encode("utf-8"),
            hashlib.sha256
        ).digest()
    ).decode("utf-8")

    return f"LMv1 {ACCESS_ID}:{signature}:{timestamp}"


def update_datasource_group(datasource_id: int, new_group: str) -> dict:
    """Update the group field of a DataSource."""
    resource_path = f"/setting/datasources/{datasource_id}"
    url = f"https://{ACCOUNT}.logicmonitor.com/santaba/rest{resource_path}"

    # Only send the field we want to update
    data = json.dumps({"group": new_group})

    auth_header = generate_auth_header("PATCH", resource_path, data)

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "X-Version": "3",
    }

    response = requests.patch(url, headers=headers, data=data)
    return response.json()


def main():
    if not ACCESS_ID or not ACCESS_KEY:
        print("Error: Set LM_ACCESS_ID and LM_ACCESS_KEY environment variables")
        print("\nExample:")
        print("  export LM_ACCESS_ID='your_access_id'")
        print("  export LM_ACCESS_KEY='your_access_key'")
        print("  python update_datasource_group.py")
        return 1

    print(f"Updating DataSource groups to '{NEW_GROUP}'...")
    print(f"Account: {ACCOUNT}")
    print("-" * 60)

    for ds in DATASOURCES:
        print(f"\nUpdating {ds['displayName']} (ID: {ds['id']})...")

        try:
            result = update_datasource_group(ds["id"], NEW_GROUP)

            if "errmsg" in result and result["errmsg"]:
                print(f"  ❌ Error: {result['errmsg']}")
            elif "data" in result:
                new_group = result["data"].get("group", "unknown")
                print(f"  ✓ Success! Group is now: {new_group}")
            else:
                print(f"  Response: {json.dumps(result, indent=2)}")

        except Exception as e:
            print(f"  ❌ Exception: {e}")

    print("\n" + "-" * 60)
    print("Done!")
    return 0


if __name__ == "__main__":
    exit(main())
