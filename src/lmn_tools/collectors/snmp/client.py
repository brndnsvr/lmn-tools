"""
SNMP collector for network devices.

Provides SNMP v2c/v3 connectivity and data collection.
"""

from __future__ import annotations

import logging
from typing import Any, Union

from lmn_tools.collectors.base import BaseCollector
from lmn_tools.core.config import SNMPv2cCredentials, SNMPv3Credentials
from lmn_tools.core.exceptions import SNMPAuthenticationError, SNMPConnectionError, SNMPTimeoutError
from lmn_tools.models.discovery import DiscoveredInstance
from lmn_tools.models.metrics import MetricValue

logger = logging.getLogger(__name__)

# Union type for SNMP credentials
SNMPCredentials = Union[SNMPv2cCredentials, SNMPv3Credentials]


class SNMPCollector(BaseCollector[SNMPCredentials]):
    """
    SNMP collector for network devices.

    Supports SNMPv2c (community string) and SNMPv3 (USM) authentication.

    Attributes:
        hostname: Device hostname or IP
        credentials: SNMP credentials (v2c or v3)
    """

    def __init__(
        self,
        hostname: str,
        credentials: SNMPCredentials,
        debug: bool = False,
    ):
        """
        Initialize SNMP collector.

        Args:
            hostname: Device hostname or IP address
            credentials: SNMPv2c or SNMPv3 credentials
            debug: Enable debug output
        """
        super().__init__(hostname, credentials, debug)
        self._engine: Any = None
        self._auth: Any = None

    def _get_auth(self) -> Any:
        """
        Build pysnmp authentication object.

        Returns:
            CommunityData for v2c or UsmUserData for v3
        """
        try:
            from pysnmp.hlapi import (
                CommunityData,
                UsmUserData,
                usmAesCfb128Protocol,
                usmDESPrivProtocol,
                usmHMACMD5AuthProtocol,
                usmHMACSHAAuthProtocol,
            )
        except ImportError:
            raise SNMPConnectionError(
                self.hostname,
                self.credentials.port,
                "pysnmp not installed. Install with: pip install lmn-tools[snmp]",
            )

        if isinstance(self.credentials, SNMPv2cCredentials):
            return CommunityData(self.credentials.community.get_secret_value())

        # SNMPv3
        # Map auth protocol names to pysnmp constants
        auth_protocols = {
            "MD5": usmHMACMD5AuthProtocol,
            "SHA": usmHMACSHAAuthProtocol,
        }
        priv_protocols = {
            "DES": usmDESPrivProtocol,
            "AES128": usmAesCfb128Protocol,
        }

        auth_proto = auth_protocols.get(
            self.credentials.auth_protocol, usmHMACSHAAuthProtocol
        )
        priv_proto = priv_protocols.get(
            self.credentials.priv_protocol, usmAesCfb128Protocol
        )

        return UsmUserData(
            self.credentials.username,
            self.credentials.auth_password.get_secret_value(),
            self.credentials.priv_password.get_secret_value(),
            authProtocol=auth_proto,
            privProtocol=priv_proto,
        )

    def connect(self) -> None:
        """
        Initialize SNMP engine.

        Note: SNMP is connectionless, so this just initializes
        the engine and auth objects.
        """
        try:
            from pysnmp.hlapi import SnmpEngine
        except ImportError:
            raise SNMPConnectionError(
                self.hostname,
                self.credentials.port,
                "pysnmp not installed. Install with: pip install lmn-tools[snmp]",
            )

        self._engine = SnmpEngine()
        self._auth = self._get_auth()
        self._connected = True
        self._debug_print("SNMP engine initialized")

    def disconnect(self) -> None:
        """Clean up SNMP engine."""
        self._engine = None
        self._auth = None
        self._connected = False

    def get(self, oid: str) -> str | None:
        """
        Get single OID value via SNMP GET.

        Args:
            oid: OID to query (e.g., "1.3.6.1.2.1.1.1.0")

        Returns:
            String value or None if not found

        Raises:
            SNMPTimeoutError: If request times out
            SNMPError: If SNMP error occurs
        """
        if not self._connected:
            self.connect()

        try:
            from pysnmp.hlapi import (
                ContextData,
                ObjectIdentity,
                ObjectType,
                UdpTransportTarget,
                getCmd,
            )
        except ImportError:
            raise SNMPConnectionError(
                self.hostname, self.credentials.port, "pysnmp not installed"
            )

        iterator = getCmd(
            self._engine,
            self._auth,
            UdpTransportTarget(
                (self.hostname, self.credentials.port),
                timeout=self.credentials.timeout,
                retries=self.credentials.retries,
            ),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )

        error_indication, error_status, error_index, var_binds = next(iterator)

        if error_indication:
            if "timeout" in str(error_indication).lower():
                raise SNMPTimeoutError(self.hostname, oid)
            raise SNMPConnectionError(
                self.hostname, self.credentials.port, str(error_indication)
            )

        if error_status:
            self._debug_print(f"SNMP error: {error_status.prettyPrint()}")
            return None

        for var_bind in var_binds:
            _, value = var_bind
            value_str = value.prettyPrint()
            if "noSuch" in value_str:
                return None
            return value_str

        return None

    def walk(self, oid: str) -> dict[str, str]:
        """
        Walk OID subtree via SNMP GETNEXT.

        Args:
            oid: Base OID to walk

        Returns:
            Dictionary mapping index to value

        Raises:
            SNMPTimeoutError: If request times out
        """
        if not self._connected:
            self.connect()

        try:
            from pysnmp.hlapi import (
                ContextData,
                ObjectIdentity,
                ObjectType,
                UdpTransportTarget,
                nextCmd,
            )
        except ImportError:
            raise SNMPConnectionError(
                self.hostname, self.credentials.port, "pysnmp not installed"
            )

        results: dict[str, str] = {}

        for error_indication, error_status, error_index, var_binds in nextCmd(
            self._engine,
            self._auth,
            UdpTransportTarget(
                (self.hostname, self.credentials.port),
                timeout=self.credentials.timeout,
                retries=self.credentials.retries,
            ),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False,
        ):
            if error_indication:
                if "timeout" in str(error_indication).lower():
                    raise SNMPTimeoutError(self.hostname, oid)
                break

            if error_status:
                break

            for var_bind in var_binds:
                oid_str, value = var_bind
                # Extract index (last component of OID)
                index = str(oid_str).split(".")[-1]
                results[index] = value.prettyPrint()

        return results

    def get_bulk(self, oid: str, max_repetitions: int = 25) -> dict[str, str]:
        """
        Bulk get OID subtree via SNMP GETBULK.

        More efficient than walk for large tables.

        Args:
            oid: Base OID
            max_repetitions: Max rows per request

        Returns:
            Dictionary mapping index to value
        """
        if not self._connected:
            self.connect()

        try:
            from pysnmp.hlapi import (
                ContextData,
                ObjectIdentity,
                ObjectType,
                UdpTransportTarget,
                bulkCmd,
            )
        except ImportError:
            raise SNMPConnectionError(
                self.hostname, self.credentials.port, "pysnmp not installed"
            )

        results: dict[str, str] = {}

        for error_indication, error_status, error_index, var_binds in bulkCmd(
            self._engine,
            self._auth,
            UdpTransportTarget(
                (self.hostname, self.credentials.port),
                timeout=self.credentials.timeout,
                retries=self.credentials.retries,
            ),
            ContextData(),
            0,  # nonRepeaters
            max_repetitions,
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False,
        ):
            if error_indication or error_status:
                break

            for var_bind in var_binds:
                oid_str, value = var_bind
                index = str(oid_str).split(".")[-1]
                results[index] = value.prettyPrint()

        return results

    def discover(self, config: dict[str, Any]) -> list[DiscoveredInstance]:
        """
        Discover instances via SNMP.

        Args:
            config: Discovery configuration containing:
                - walk_oid: OID to walk for instance discovery
                - id_oid_suffix: OID suffix for instance ID
                - name_oid_suffix: OID suffix for instance name (optional)

        Returns:
            List of DiscoveredInstance objects
        """
        walk_oid = config.get("walk_oid", "")
        if not walk_oid:
            self._debug_print("No walk_oid specified")
            return []

        results = self.walk(walk_oid)
        instances: list[DiscoveredInstance] = []

        for index, value in results.items():
            instance_id = self._sanitize_id(index)
            if instance_id:
                instances.append(
                    DiscoveredInstance(
                        instance_id=instance_id,
                        instance_name=value or instance_id,
                    )
                )

        self._debug_print(f"Discovered {len(instances)} instances")
        return instances

    def collect(self, config: dict[str, Any]) -> list[MetricValue]:
        """
        Collect metrics via SNMP.

        Args:
            config: Collection configuration containing:
                - metrics: List of metric definitions with:
                    - name: Metric name
                    - oid: OID to query
                    - walk: Whether to walk the OID (for tables)

        Returns:
            List of MetricValue objects
        """
        metric_defs = config.get("metrics", [])
        if not metric_defs:
            self._debug_print("No metrics defined")
            return []

        metrics: list[MetricValue] = []

        for metric_def in metric_defs:
            name = metric_def.get("name", "")
            oid = metric_def.get("oid", "")

            if not name or not oid:
                continue

            if metric_def.get("walk", False):
                # Walk OID for table values
                results = self.walk(oid)
                for index, value in results.items():
                    try:
                        float_value = float(value)
                        instance_id = self._sanitize_id(index)
                        metrics.append(
                            MetricValue(
                                name=name,
                                value=float_value,
                                instance_id=instance_id,
                            )
                        )
                    except (ValueError, TypeError):
                        continue
            else:
                # Single OID get
                value = self.get(oid)
                if value:
                    try:
                        float_value = float(value)
                        metrics.append(MetricValue(name=name, value=float_value))
                    except (ValueError, TypeError):
                        continue

        self._debug_print(f"Collected {len(metrics)} metrics")
        return metrics

    def _sanitize_id(self, value: str) -> str:
        """Sanitize value for use as instance ID."""
        import re
        from lmn_tools.constants import Patterns

        if not value:
            return ""
        sanitized = Patterns.INVALID_INSTANCE_ID_CHARS.sub("_", str(value))
        sanitized = re.sub(r"_+", "_", sanitized)
        return sanitized.strip("_")
