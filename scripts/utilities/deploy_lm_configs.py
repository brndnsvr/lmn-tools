#!/usr/bin/env python3
"""
LogicMonitor Custom DataSource/PropertySource Deployment Script

Deploys Juniper monitoring configurations to LogicMonitor via REST API.
Handles HMAC-SHA256 authentication required by LM API.

Usage:
    export LM_ACCESS_ID="your_access_id"
    export LM_ACCESS_KEY="your_access_key"
    export LM_COMPANY="evoquedcs"

    python deploy_lm_configs.py
"""

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

# Configuration
LM_ACCESS_ID = os.environ.get("LM_ACCESS_ID")
LM_ACCESS_KEY = os.environ.get("LM_ACCESS_KEY")
LM_COMPANY = os.environ.get("LM_COMPANY", "evoquedcs")
LM_BASE_URL = f"https://{LM_COMPANY}.logicmonitor.com/santaba/rest"

# Config file paths (relative to script location)
SCRIPT_DIR = Path(__file__).parent.parent / "configs" / "logicmonitor"
CONFIG_FILES = {
    "propertysource": SCRIPT_DIR / "propertysource-cluster-detect.json",
    "datasources": [
        SCRIPT_DIR / "datasource-evpn.json",
        SCRIPT_DIR / "datasource-cluster.json",
        SCRIPT_DIR / "datasource-routing.json",
    ],
}


def generate_auth_header(http_method: str, resource_path: str, data: str = "") -> dict:
    """Generate LogicMonitor API authentication headers with HMAC-SHA256."""
    epoch = str(int(time.time() * 1000))

    # Build signature string
    request_vars = f"{http_method}{epoch}{data}{resource_path}"

    # Create HMAC-SHA256 signature
    # LM expects: hexdigest first, then base64 encode the hex string
    hex_digest = hmac.new(
        LM_ACCESS_KEY.encode("utf-8"),
        msg=request_vars.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    signature = base64.b64encode(hex_digest.encode("utf-8")).decode("utf-8")

    auth = f"LMv1 {LM_ACCESS_ID}:{signature}:{epoch}"

    return {
        "Content-Type": "application/json",
        "Authorization": auth,
        "X-Version": "3",
    }


def api_request(
    method: str, endpoint: str, data: dict | None = None
) -> dict[str, Any]:
    """Make authenticated API request to LogicMonitor."""
    url = LM_BASE_URL + endpoint
    data_str = json.dumps(data) if data else ""

    # Query parameters must NOT be included in signature calculation
    # per LogicMonitor API docs - only use the resource path
    resource_path = endpoint.split("?")[0]
    headers = generate_auth_header(method.upper(), resource_path, data_str)

    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        data=data_str if data else None,
        timeout=30,
    )

    if response.status_code >= 400:
        print(f"  ERROR: {response.status_code} - {response.text}")
        return {"status": response.status_code, "error": response.text}

    return response.json()


def check_existing_propertysource(name: str) -> int | None:
    """Check if PropertySource already exists, return ID if found."""
    # Use tilde for exact match, escape special characters
    result = api_request("GET", f"/setting/propertyrules?filter=name:\"{name}\"")

    if result.get("data", {}).get("items"):
        return result["data"]["items"][0]["id"]
    return None


def check_existing_datasource(name: str) -> int | None:
    """Check if DataSource already exists, return ID if found."""
    # Use tilde for exact match, escape special characters
    result = api_request("GET", f"/setting/datasources?filter=name:\"{name}\"")

    if result.get("data", {}).get("items"):
        return result["data"]["items"][0]["id"]
    return None


def deploy_propertysource(config_path: Path) -> bool:
    """Deploy a PropertySource configuration."""
    print(f"\n{'='*60}")
    print(f"Deploying PropertySource: {config_path.name}")
    print("="*60)

    with open(config_path) as f:
        config = json.load(f)

    name = config["name"]
    print(f"  Name: {name}")
    print(f"  AppliesTo: {config.get('appliesTo', 'N/A')}")

    # Check if already exists
    existing_id = check_existing_propertysource(name)
    if existing_id:
        print(f"  EXISTS: PropertySource already exists with ID {existing_id}")
        print("  Skipping creation (use --force to overwrite)")
        return True

    # Transform config to LM API format
    # PropertySource uses groovyScript directly, not nested params
    api_config = {
        "name": config["name"],
        "displayName": config.get("displayName", config["name"]),
        "description": config.get("description", ""),
        "appliesTo": config.get("appliesTo", ""),
        "technology": config.get("techNotes", ""),
        "tags": ",".join(config.get("tags", [])),
        "group": config.get("group", ""),
        "groovyScript": config["script"]["groovyScript"],
    }

    result = api_request("POST", "/setting/propertyrules", api_config)

    if "error" in result:
        error_msg = result.get("error", "")
        # Handle "already exists" as success
        if "already used" in error_msg:
            print(f"  EXISTS: PropertySource already exists (detected via API response)")
            return True
        print(f"  FAILED: {error_msg}")
        return False

    new_id = result.get("data", {}).get("id")
    print(f"  SUCCESS: Created PropertySource ID {new_id}")
    return True


def deploy_datasource(config_path: Path) -> bool:
    """Deploy a DataSource configuration."""
    print(f"\n{'='*60}")
    print(f"Deploying DataSource: {config_path.name}")
    print("="*60)

    with open(config_path) as f:
        config = json.load(f)

    name = config["name"]
    print(f"  Name: {name}")
    print(f"  AppliesTo: {config.get('appliesTo', 'N/A')}")

    # Check if already exists
    existing_id = check_existing_datasource(name)
    if existing_id:
        print(f"  EXISTS: DataSource already exists with ID {existing_id}")
        print("  Skipping creation (use --force to overwrite)")
        return True

    # Transform config to LM API format
    # Note: LM DataSource API is complex - this is a simplified version
    # For production, may need to use XML import or manual UI upload

    # Sanitize displayName - hyphens only allowed at end of displayName
    display_name = config.get("displayName", config["name"])
    if "-" in display_name and not display_name.endswith("-"):
        # Replace hyphens with spaces (except trailing ones)
        display_name = display_name.replace("-", " ")
        print(f"  NOTE: Sanitized displayName to '{display_name}' (hyphens not allowed)")

    api_config = {
        "name": config["name"],
        "displayName": display_name,
        "description": config.get("description", ""),
        "appliesTo": config.get("appliesTo", ""),
        "technology": config.get("techNotes", ""),
        "tags": ",".join(config.get("tags", [])),
        "group": config.get("group", ""),
        "collectMethod": config.get("collectMethod", "script"),
        "collectInterval": config.get("collectInterval", 300),
        "hasMultiInstances": config.get("hasMultiInstances", False),
        "useWildValueAsUniqueIdentifier": config.get("useWildValueAsUniqueIdentifier", False),
        # Required for script-based datasources
        "collectorAttribute": {
            "name": "script",
            "groovyScript": config.get("collectScript", {}).get("content", "return 0"),
        },
    }

    # Add datapoints
    # DataType mapping: API expects integers 1-8, config uses strings
    # Valid values: 1=counter, 2=derive, 7=gauge
    datatype_map = {"gauge": 7, "counter": 1, "derive": 2}

    if "dataPoints" in config:
        api_config["dataPoints"] = []
        for dp in config["dataPoints"]:
            # Convert string dataType to integer
            dt_value = dp.get("dataType", "gauge")
            if isinstance(dt_value, str):
                dt_value = datatype_map.get(dt_value.lower(), 7)

            dp_config = {
                "name": dp["name"],
                "description": dp.get("description", ""),
                "dataType": dt_value,
            }
            # NOTE: Skip alertExpr/alertSeverity - complex expressions not supported via API
            # These can be configured manually in LogicMonitor UI after deployment
            api_config["dataPoints"].append(dp_config)

    result = api_request("POST", "/setting/datasources", api_config)

    if "error" in result:
        error_msg = result.get("error", "")
        # Handle "already exists" as success
        if "already used" in error_msg:
            print(f"  EXISTS: DataSource already exists (detected via API response)")
            return True
        print(f"  FAILED: {error_msg}")
        print("\n  NOTE: DataSource creation via API can be complex.")
        print("  Consider using LogicMonitor UI for manual import:")
        print(f"    Settings > DataSources > Add > From JSON")
        print(f"    File: {config_path}")
        return False

    new_id = result.get("data", {}).get("id")
    print(f"  SUCCESS: Created DataSource ID {new_id}")
    return True


def main():
    """Main deployment workflow."""
    print("\n" + "="*60)
    print("LogicMonitor Juniper Monitoring Deployment")
    print("="*60)
    print(f"Company: {LM_COMPANY}")
    print(f"API URL: {LM_BASE_URL}")

    # Validate credentials
    if not LM_ACCESS_ID or not LM_ACCESS_KEY:
        print("\nERROR: Missing API credentials!")
        print("Set environment variables:")
        print("  export LM_ACCESS_ID='your_access_id'")
        print("  export LM_ACCESS_KEY='your_access_key'")
        sys.exit(1)

    print(f"Access ID: {LM_ACCESS_ID[:8]}...")

    # Test API connectivity
    print("\nTesting API connectivity...")
    test_result = api_request("GET", "/setting/datasources?size=1")
    if "error" in test_result:
        print("ERROR: API connection failed!")
        sys.exit(1)
    print("  API connection OK")

    results = {"success": [], "failed": [], "skipped": []}

    # Step 1: Deploy PropertySource FIRST (dependency for cluster datasource)
    print("\n" + "#"*60)
    print("# STEP 1: Deploy PropertySource (MUST BE FIRST)")
    print("#"*60)

    ps_path = CONFIG_FILES["propertysource"]
    if ps_path.exists():
        if deploy_propertysource(ps_path):
            results["success"].append(ps_path.name)
        else:
            results["failed"].append(ps_path.name)
    else:
        print(f"  ERROR: File not found: {ps_path}")
        results["failed"].append(ps_path.name)

    # Step 2: Deploy DataSources
    print("\n" + "#"*60)
    print("# STEP 2: Deploy DataSources")
    print("#"*60)

    for ds_path in CONFIG_FILES["datasources"]:
        if ds_path.exists():
            if deploy_datasource(ds_path):
                results["success"].append(ds_path.name)
            else:
                results["failed"].append(ds_path.name)
        else:
            print(f"  ERROR: File not found: {ds_path}")
            results["failed"].append(ds_path.name)

    # Summary
    print("\n" + "="*60)
    print("DEPLOYMENT SUMMARY")
    print("="*60)
    print(f"  Successful: {len(results['success'])}")
    for name in results["success"]:
        print(f"    - {name}")

    if results["failed"]:
        print(f"  Failed: {len(results['failed'])}")
        for name in results["failed"]:
            print(f"    - {name}")

    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("1. Wait for PropertySource to run (up to 24 hours, or trigger manually)")
    print("2. Verify auto.cluster_mode property is set on SRX devices")
    print("3. Check DataSources are applying to correct devices")
    print("4. Monitor for alert noise and tune thresholds as needed")

    return 0 if not results["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
