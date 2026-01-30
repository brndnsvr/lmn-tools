"""
Constants, string maps, default values, and API endpoints for lmn-tools.

This module provides centralized configuration for:
- LogicMonitor API endpoints and defaults
- String-to-numeric conversion maps
- NETCONF defaults and namespaces
- Common regex patterns
- Output format constants
"""

from __future__ import annotations

import re
from typing import Final

# =============================================================================
# LogicMonitor API Configuration
# =============================================================================


class LMAPIConfig:
    """LogicMonitor REST API configuration constants."""

    BASE_PATH: Final[str] = "/santaba/rest"
    API_VERSION: Final[str] = "3"

    DEFAULT_TIMEOUT: Final[int] = 30
    DEFAULT_PAGE_SIZE: Final[int] = 250
    MAX_PAGE_SIZE: Final[int] = 1000

    # Rate limiting
    RATE_LIMIT_HEADER: Final[str] = "X-Rate-Limit-Remaining"
    RATE_LIMIT_WINDOW_HEADER: Final[str] = "X-Rate-Limit-Window"


class LMEndpoints:
    """LogicMonitor API endpoint paths."""

    # =========================================================================
    # Devices
    # =========================================================================
    DEVICES: Final[str] = "/device/devices"
    DEVICE_BY_ID: Final[str] = "/device/devices/{device_id}"
    DEVICE_PROPERTIES: Final[str] = "/device/devices/{device_id}/properties"
    DEVICE_DATASOURCES: Final[str] = "/device/devices/{device_id}/devicedatasources"
    DEVICE_DATASOURCE_BY_ID: Final[str] = (
        "/device/devices/{device_id}/devicedatasources/{device_datasource_id}"
    )
    DEVICE_DATASOURCE_INSTANCES: Final[str] = (
        "/device/devices/{device_id}/devicedatasources/{device_datasource_id}/instances"
    )

    # Device Groups
    DEVICE_GROUPS: Final[str] = "/device/groups"
    DEVICE_GROUP_BY_ID: Final[str] = "/device/groups/{group_id}"
    DEVICE_GROUP_DEVICES: Final[str] = "/device/groups/{group_id}/devices"
    DEVICE_GROUP_PROPERTIES: Final[str] = "/device/groups/{group_id}/properties"

    # =========================================================================
    # LogicModules
    # =========================================================================

    # DataSources
    DATASOURCES: Final[str] = "/setting/datasources"
    DATASOURCE_BY_ID: Final[str] = "/setting/datasources/{datasource_id}"
    DATASOURCE_DATAPOINTS: Final[str] = "/setting/datasources/{datasource_id}/datapoints"
    DATASOURCE_GRAPHS: Final[str] = "/setting/datasources/{datasource_id}/graphs"
    DATASOURCE_OGRAPHS: Final[str] = "/setting/datasources/{datasource_id}/ographs"

    # PropertySources
    PROPERTYSOURCES: Final[str] = "/setting/propertyrules"
    PROPERTYSOURCE_BY_ID: Final[str] = "/setting/propertyrules/{propertysource_id}"

    # EventSources
    EVENTSOURCES: Final[str] = "/setting/eventsources"
    EVENTSOURCE_BY_ID: Final[str] = "/setting/eventsources/{eventsource_id}"

    # ConfigSources
    CONFIGSOURCES: Final[str] = "/setting/configsources"
    CONFIGSOURCE_BY_ID: Final[str] = "/setting/configsources/{configsource_id}"

    # TopologySources
    TOPOLOGYSOURCES: Final[str] = "/setting/topologysources"
    TOPOLOGYSOURCE_BY_ID: Final[str] = "/setting/topologysources/{topologysource_id}"

    # =========================================================================
    # Alerts
    # =========================================================================
    ALERTS: Final[str] = "/alert/alerts"
    ALERT_BY_ID: Final[str] = "/alert/alerts/{alert_id}"

    # Escalation Chains
    ESCALATION_CHAINS: Final[str] = "/setting/alert/chains"
    ESCALATION_CHAIN_BY_ID: Final[str] = "/setting/alert/chains/{chain_id}"

    # Alert Rules
    ALERT_RULES: Final[str] = "/setting/alert/rules"
    ALERT_RULE_BY_ID: Final[str] = "/setting/alert/rules/{rule_id}"

    # Integrations
    INTEGRATIONS: Final[str] = "/setting/integrations"
    INTEGRATION_BY_ID: Final[str] = "/setting/integrations/{integration_id}"

    # =========================================================================
    # Dashboards
    # =========================================================================
    DASHBOARDS: Final[str] = "/dashboard/dashboards"
    DASHBOARD_BY_ID: Final[str] = "/dashboard/dashboards/{dashboard_id}"
    DASHBOARD_WIDGETS: Final[str] = "/dashboard/dashboards/{dashboard_id}/widgets"
    DASHBOARD_GROUPS: Final[str] = "/dashboard/groups"
    DASHBOARD_GROUP_BY_ID: Final[str] = "/dashboard/groups/{group_id}"

    # Widgets
    WIDGETS: Final[str] = "/dashboard/widgets"
    WIDGET_BY_ID: Final[str] = "/dashboard/widgets/{widget_id}"

    # =========================================================================
    # SDT (Scheduled Downtime)
    # =========================================================================
    SDTS: Final[str] = "/sdt/sdts"
    SDT_BY_ID: Final[str] = "/sdt/sdts/{sdt_id}"

    # =========================================================================
    # Collectors
    # =========================================================================
    COLLECTORS: Final[str] = "/setting/collector/collectors"
    COLLECTOR_BY_ID: Final[str] = "/setting/collector/collectors/{collector_id}"
    COLLECTOR_GROUPS: Final[str] = "/setting/collector/groups"

    # =========================================================================
    # Users and Roles
    # =========================================================================
    USERS: Final[str] = "/setting/admins"
    USER_BY_ID: Final[str] = "/setting/admins/{admin_id}"
    ROLES: Final[str] = "/setting/roles"
    ROLE_BY_ID: Final[str] = "/setting/roles/{role_id}"

    # =========================================================================
    # Reports
    # =========================================================================
    REPORTS: Final[str] = "/report/reports"
    REPORT_BY_ID: Final[str] = "/report/reports/{report_id}"

    # =========================================================================
    # OpsNotes
    # =========================================================================
    OPSNOTES: Final[str] = "/setting/opsnotes"
    OPSNOTE_BY_ID: Final[str] = "/setting/opsnotes/{note_id}"

    # =========================================================================
    # Netscans (Device Discovery)
    # =========================================================================
    NETSCANS: Final[str] = "/setting/netscans"
    NETSCAN_BY_ID: Final[str] = "/setting/netscans/{netscan_id}"

    # =========================================================================
    # Batch Jobs
    # =========================================================================
    BATCHJOBS: Final[str] = "/setting/batchjobs"
    BATCHJOB_BY_ID: Final[str] = "/setting/batchjobs/{job_id}"

    # =========================================================================
    # Recipient Groups
    # =========================================================================
    RECIPIENT_GROUPS: Final[str] = "/setting/recipientgroups"
    RECIPIENT_GROUP_BY_ID: Final[str] = "/setting/recipientgroups/{group_id}"

    # =========================================================================
    # API Tokens
    # =========================================================================
    API_TOKENS: Final[str] = "/setting/admins/{admin_id}/apitokens"
    API_TOKEN_BY_ID: Final[str] = "/setting/admins/{admin_id}/apitokens/{token_id}"
    API_TOKENS_ALL: Final[str] = "/setting/apitokens"

    # =========================================================================
    # Access Groups (RBAC)
    # =========================================================================
    ACCESS_GROUPS: Final[str] = "/setting/accessgroup"
    ACCESS_GROUP_BY_ID: Final[str] = "/setting/accessgroup/{group_id}"

    # =========================================================================
    # Audit Logs
    # =========================================================================
    ACCESS_LOGS: Final[str] = "/setting/accesslogs"
    ACCESS_LOG_BY_ID: Final[str] = "/setting/accesslogs/{log_id}"

    # =========================================================================
    # Topology Maps (Resource Maps)
    # =========================================================================
    TOPOLOGY_MAPS: Final[str] = "/topology/topologies"
    TOPOLOGY_MAP_BY_ID: Final[str] = "/topology/topologies/{map_id}"
    TOPOLOGY_MAP_DATA: Final[str] = "/topology/topologies/{map_id}/data"

    # =========================================================================
    # Services (Service Insight)
    # =========================================================================
    SERVICES: Final[str] = "/service/services"
    SERVICE_BY_ID: Final[str] = "/service/services/{service_id}"
    SERVICE_GROUPS: Final[str] = "/service/groups"
    SERVICE_GROUP_BY_ID: Final[str] = "/service/groups/{group_id}"

    # =========================================================================
    # Websites (Synthetic Monitoring)
    # =========================================================================
    WEBSITES: Final[str] = "/website/websites"
    WEBSITE_BY_ID: Final[str] = "/website/websites/{website_id}"
    WEBSITE_GROUPS: Final[str] = "/website/groups"

    # =========================================================================
    # Metrics/Data
    # =========================================================================
    DEVICE_DATA: Final[str] = "/device/devices/{device_id}/devicedatasources/{device_datasource_id}/instances/{instance_id}/data"
    DEVICE_INSTANCE_DATA: Final[str] = "/device/devices/{device_id}/instances/{instance_id}/data"


# =============================================================================
# String Maps for Status/Enum Conversions
# =============================================================================


class StringMaps:
    """
    Predefined string-to-numeric conversion maps.

    These maps are used to convert string status values from devices
    into numeric values for LogicMonitor datapoints.
    """

    # Generic status (up/down)
    STATUS: Final[dict[str, int]] = {
        "down": 0,
        "up": 1,
    }

    # Admin/operational state
    ADMIN_STATE: Final[dict[str, int]] = {
        "down": 0,
        "up": 1,
        "testing": 2,
    }

    OPER_STATE: Final[dict[str, int]] = {
        "down": 0,
        "up": 1,
        "unknown": -1,
        "testing": 2,
        "dormant": 3,
        "notPresent": 4,
        "lowerLayerDown": 5,
    }

    # Enable/disable
    ENABLED: Final[dict[str, int]] = {
        "disabled": 0,
        "enabled": 1,
    }

    # Active/inactive
    ACTIVE: Final[dict[str, int]] = {
        "Inactive": 0,
        "inactive": 0,
        "Active": 1,
        "active": 1,
    }

    # Boolean representations
    BOOLEAN: Final[dict[str, int]] = {
        "false": 0,
        "False": 0,
        "true": 1,
        "True": 1,
        "no": 0,
        "No": 0,
        "yes": 1,
        "Yes": 1,
        "0": 0,
        "1": 1,
    }

    # Alarm severity levels
    ALARM_SEVERITY: Final[dict[str, int]] = {
        "cleared": 0,
        "indeterminate": 1,
        "warning": 2,
        "minor": 3,
        "major": 4,
        "critical": 5,
    }

    # Software/service state
    SOFTWARE_STATE: Final[dict[str, int]] = {
        "Inactive": 0,
        "Active": 1,
        "Standby": 2,
        "Failed": 3,
    }

    # Fiber type mapping
    FIBER_TYPE: Final[dict[str, int]] = {
        "SMF-28": 1,
        "SMF-28e": 2,
        "G.652": 3,
        "G.655": 4,
        "unknown": 0,
    }

    @classmethod
    def get_map(cls, name: str) -> dict[str, int]:
        """
        Get a string map by name.

        Args:
            name: Map name (case-insensitive, hyphens/spaces converted to underscores)

        Returns:
            The string map dictionary

        Raises:
            KeyError: If map name not found
        """
        name_upper = name.upper().replace("-", "_").replace(" ", "_")
        if hasattr(cls, name_upper):
            attr = getattr(cls, name_upper)
            if isinstance(attr, dict):
                return attr
        raise KeyError(f"Unknown string map: {name}")

    @classmethod
    def all_maps(cls) -> dict[str, dict[str, int]]:
        """Return all available string maps."""
        return {
            "status": cls.STATUS,
            "admin_state": cls.ADMIN_STATE,
            "oper_state": cls.OPER_STATE,
            "enabled": cls.ENABLED,
            "active": cls.ACTIVE,
            "boolean": cls.BOOLEAN,
            "alarm_severity": cls.ALARM_SEVERITY,
            "software_state": cls.SOFTWARE_STATE,
            "fiber_type": cls.FIBER_TYPE,
        }


# =============================================================================
# NETCONF Configuration
# =============================================================================


class NetconfDefaults:
    """Default values for NETCONF connections."""

    PORT: Final[int] = 830
    TIMEOUT: Final[int] = 60

    # SSH options
    HOSTKEY_VERIFY: Final[bool] = False
    ALLOW_AGENT: Final[bool] = False
    LOOK_FOR_KEYS: Final[bool] = False


class NetconfNamespaces:
    """Common NETCONF namespace URIs."""

    # Standard NETCONF
    NETCONF_BASE_1_0: Final[str] = "urn:ietf:params:xml:ns:netconf:base:1.0"
    NETCONF_BASE_1_1: Final[str] = "urn:ietf:params:xml:ns:netconf:base:1.1"

    # Coriant/Infinera
    CORIANT_NE: Final[str] = "http://coriant.com/yang/os/ne"

    # Ciena WaveServer
    CIENA_WS_PTPS: Final[str] = "urn:ciena:params:xml:ns:yang:ciena-ws-ptps"
    CIENA_WS_PTP: Final[str] = "urn:ciena:params:xml:ns:yang:ciena-ws-ptp"
    CIENA_WS_PORT: Final[str] = "urn:ciena:params:xml:ns:yang:ciena-ws-port"
    CIENA_WS_XCVR: Final[str] = "urn:ciena:params:xml:ns:yang:ciena-ws-xcvr"


# =============================================================================
# Regex Patterns
# =============================================================================


class Patterns:
    """Compiled regex patterns for common operations."""

    # Characters not allowed in LogicMonitor instance IDs
    INVALID_INSTANCE_ID_CHARS: Final[re.Pattern[str]] = re.compile(r"[:#\\\s]")

    # XML namespace patterns
    XML_NAMESPACE_URI: Final[re.Pattern[str]] = re.compile(r"\{[^}]+\}")
    XML_NAMESPACE_PREFIX: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*:")

    # Interface subunit (e.g., "ae100.3" -> match ".3")
    INTERFACE_UNIT: Final[re.Pattern[str]] = re.compile(r"\.\d+$")

    # IP address patterns
    IPV4_ADDRESS: Final[re.Pattern[str]] = re.compile(
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )
    IPV6_ADDRESS: Final[re.Pattern[str]] = re.compile(
        r"^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|"
        r"^::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}$|"
        r"^(?:[0-9a-fA-F]{1,4}:){1,7}:$"
    )

    # Metric name validation (lowercase alphanumeric with underscores)
    VALID_METRIC_NAME: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]*$")


# =============================================================================
# LogicMonitor Output Format Constants
# =============================================================================


class LMOutputFormat:
    """Constants for LogicMonitor script output formats."""

    # Discovery output separators
    DISCOVERY_FIELD_SEPARATOR: Final[str] = "##"
    PROPERTY_KEY_VALUE_SEPARATOR: Final[str] = "="
    PROPERTY_SEPARATOR: Final[str] = "&"
    PROPERTY_PREFIX: Final[str] = "auto."

    # Collection output separator
    METRIC_SEPARATOR: Final[str] = "."
    METRIC_VALUE_SEPARATOR: Final[str] = "="


# =============================================================================
# Datasource Name Constants
# =============================================================================


class DatasourceNames:
    """Common LogicMonitor datasource names."""

    # Network interfaces
    SNMP_NETWORK_INTERFACES: Final[str] = "SNMP_Network_Interfaces"
    INTERFACES_DISPLAY: Final[str] = "Interfaces-"

    # Juniper-specific
    JUNIPER_DOM: Final[str] = "Juniper DOM-"
    JUNIPER_BGP: Final[str] = "BGP-"

    @classmethod
    def format_full_name(cls, display_name: str, internal_name: str) -> str:
        """
        Format a datasource full name as used by LM API.

        Args:
            display_name: The display name (e.g., "Network Interfaces")
            internal_name: The internal name (e.g., "SNMP_Network_Interfaces")

        Returns:
            Formatted string like "Network Interfaces (SNMP_Network_Interfaces)"
        """
        return f"{display_name} ({internal_name})"
