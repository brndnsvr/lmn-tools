"""
NETCONF collector for optical transport devices.

Provides NETCONF connectivity and data collection for devices
such as Coriant/Infinera and Ciena WaveServer.
"""

from __future__ import annotations

import logging
import socket
from typing import TYPE_CHECKING, Any

from lmn_tools.collectors.base import BaseCollector
from lmn_tools.core.config import NetconfCredentials
from lmn_tools.core.exceptions import (
    NetconfAuthenticationError,
    NetconfConnectionError,
    NetconfRPCError,
    NetconfTimeoutError,
)
from lmn_tools.models.discovery import DiscoveredInstance
from lmn_tools.models.metrics import MetricValue

if TYPE_CHECKING:
    from lxml import etree

logger = logging.getLogger(__name__)

# Device-specific connection parameters
DEVICE_CONFIGS: dict[str, dict[str, Any]] = {
    "coriant": {
        "device_params": {"name": "default"},
        "namespaces": {
            "ne": "http://coriant.com/yang/os/ne",
        },
    },
    "ciena": {
        "device_params": {"name": "default"},
        "namespaces": {
            "ws-ptps": "urn:ciena:params:xml:ns:yang:ciena-ws-ptps",
            "ws-ptp": "urn:ciena:params:xml:ns:yang:ciena-ws-ptp",
            "ws-port": "urn:ciena:params:xml:ns:yang:ciena-ws-port",
            "ws-xcvr": "urn:ciena:params:xml:ns:yang:ciena-ws-xcvr",
        },
    },
    "juniper": {
        "device_params": {"name": "junos"},
        "namespaces": {
            "junos": "http://xml.juniper.net/junos/*/junos",
        },
    },
}


class NetconfCollector(BaseCollector[NetconfCredentials]):
    """
    NETCONF collector for optical transport devices.

    Provides NETCONF get operations with automatic connection
    management and XML parsing support.

    Attributes:
        hostname: Device hostname or IP
        credentials: NETCONF credentials
        device_type: Optional device type hint (coriant, ciena, juniper)
        capabilities: Server NETCONF capabilities (after connect)
    """

    def __init__(
        self,
        hostname: str,
        credentials: NetconfCredentials,
        device_type: str | None = None,
        debug: bool = False,
    ):
        """
        Initialize NETCONF collector.

        Args:
            hostname: Device hostname or IP address
            credentials: NETCONF credentials
            device_type: Optional device type hint for connection params
            debug: Enable debug output
        """
        super().__init__(hostname, credentials, debug)
        self.device_type = device_type
        self._manager: Any = None  # ncclient Manager
        self._capabilities: list[str] = []

    @property
    def capabilities(self) -> list[str]:
        """Return server NETCONF capabilities."""
        return self._capabilities.copy()

    def connect(self) -> None:
        """
        Establish NETCONF connection to the device.

        Raises:
            NetconfConnectionError: If connection fails
            NetconfAuthenticationError: If authentication fails
        """
        if self._connected:
            return

        # Import ncclient lazily to allow optional dependency
        try:
            from ncclient import manager
            from ncclient.transport.errors import AuthenticationError, SSHError
        except ImportError as e:
            raise NetconfConnectionError(
                self.hostname,
                self.credentials.port,
                f"ncclient not installed. Install with: pip install lmn-tools[netconf]. Error: {e}",
            ) from e

        # Get device-specific connection parameters
        device_params = {"name": "default"}
        if self.device_type and self.device_type in DEVICE_CONFIGS:
            device_params = DEVICE_CONFIGS[self.device_type].get(
                "device_params", device_params
            )

        logger.info(f"Connecting to {self.hostname}:{self.credentials.port}")
        self._debug_print(f"Device type: {self.device_type or 'auto-detect'}")

        try:
            self._manager = manager.connect(
                host=self.hostname,
                port=self.credentials.port,
                username=self.credentials.username,
                password=self.credentials.password.get_secret_value(),
                hostkey_verify=self.credentials.hostkey_verify,
                timeout=self.credentials.timeout,
                device_params=device_params,
                allow_agent=False,
                look_for_keys=False,
            )
            self._connected = True
            self._capabilities = list(self._manager.server_capabilities)
            logger.info(f"Connected - {len(self._capabilities)} capabilities")
            self._debug_print(f"Capabilities: {len(self._capabilities)}")

        except AuthenticationError as e:
            raise NetconfAuthenticationError(self.hostname, self.credentials.username) from e
        except SSHError as e:
            raise NetconfConnectionError(
                self.hostname, self.credentials.port, f"SSH error: {e}"
            ) from e
        except socket.gaierror as e:
            raise NetconfConnectionError(
                self.hostname, self.credentials.port, f"DNS resolution failed: {e}"
            ) from e
        except TimeoutError as e:
            raise NetconfConnectionError(
                self.hostname, self.credentials.port, "Connection timed out"
            ) from e
        except Exception as e:
            raise NetconfConnectionError(
                self.hostname, self.credentials.port, str(e)
            ) from e

    def disconnect(self) -> None:
        """Close NETCONF session."""
        if self._manager:
            try:
                self._manager.close_session()
                logger.debug(f"Disconnected from {self.hostname}")
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
            finally:
                self._manager = None
                self._connected = False
                self._capabilities = []

    def get(
        self,
        filter_xml: str | etree._Element | None = None,
        timeout: int | None = None,
    ) -> etree._Element:
        """
        Execute NETCONF <get> operation.

        Args:
            filter_xml: Optional subtree filter (XML string or Element)
            timeout: Optional operation timeout

        Returns:
            XML Element containing response data

        Raises:
            NetconfRPCError: If RPC operation fails
            NetconfTimeoutError: If operation times out
        """
        if not self._connected:
            raise NetconfRPCError("get", "Not connected")

        try:
            from lxml import etree
        except ImportError as e:
            raise NetconfRPCError("get", "lxml not installed") from e

        try:
            # Build filter specification
            filter_spec = None
            if filter_xml is not None:
                if isinstance(filter_xml, str):
                    filter_elem = etree.fromstring(filter_xml.encode())
                else:
                    filter_elem = filter_xml
                filter_spec = ("subtree", filter_elem)

            # Execute get operation
            response = self._manager.get(filter=filter_spec)

            # Extract data element from response
            if hasattr(response, "data_ele"):
                return response.data_ele
            elif hasattr(response, "data"):
                if isinstance(response.data, str):
                    return etree.fromstring(response.data.encode())
                return response.data
            else:
                # Fall back to parsing string representation
                return etree.fromstring(str(response).encode())

        except TimeoutError as e:
            raise NetconfTimeoutError(f"get operation timed out: {e}") from e
        except Exception as e:
            raise NetconfRPCError("get", str(e)) from e

    def get_config(
        self,
        source: str = "running",
        filter_xml: str | etree._Element | None = None,
    ) -> etree._Element:
        """
        Execute NETCONF <get-config> operation.

        Args:
            source: Configuration datastore (running, candidate, startup)
            filter_xml: Optional subtree filter

        Returns:
            XML Element containing configuration data

        Raises:
            NetconfRPCError: If RPC operation fails
        """
        if not self._connected:
            raise NetconfRPCError("get-config", "Not connected")

        try:
            from lxml import etree
        except ImportError as e:
            raise NetconfRPCError("get-config", "lxml not installed") from e

        try:
            filter_spec = None
            if filter_xml is not None:
                if isinstance(filter_xml, str):
                    filter_elem = etree.fromstring(filter_xml.encode())
                else:
                    filter_elem = filter_xml
                filter_spec = ("subtree", filter_elem)

            response = self._manager.get_config(source=source, filter=filter_spec)

            if hasattr(response, "data_ele"):
                return response.data_ele
            elif hasattr(response, "data"):
                if isinstance(response.data, str):
                    return etree.fromstring(response.data.encode())
                return response.data
            return etree.fromstring(str(response).encode())

        except Exception as e:
            raise NetconfRPCError("get-config", str(e)) from e

    def detect_device_type(self) -> str | None:
        """
        Detect device type from NETCONF capabilities.

        Returns:
            Device type string or None if unrecognized
        """
        if not self._capabilities:
            return None

        caps_str = " ".join(self._capabilities).lower()

        if "coriant" in caps_str or "infinera" in caps_str:
            return "coriant"
        elif "ciena" in caps_str or "waveserver" in caps_str:
            return "ciena"
        elif "juniper" in caps_str or "junos" in caps_str:
            return "juniper"

        return None

    def get_namespaces(self) -> dict[str, str]:
        """
        Get namespace mappings for the device type.

        Returns:
            Dictionary mapping prefixes to namespace URIs
        """
        if self.device_type and self.device_type in DEVICE_CONFIGS:
            ns: dict[str, str] = DEVICE_CONFIGS[self.device_type].get("namespaces", {}).copy()
            return ns
        return {}

    def discover(self, config: dict[str, Any]) -> list[DiscoveredInstance]:
        """
        Run Active Discovery using NETCONF.

        Args:
            config: Discovery configuration containing:
                - netconf_filter: XML filter for get operation
                - namespaces: XML namespace mappings
                - instance_xpath: XPath to instance elements
                - id_xpath: XPath to instance ID within element
                - name_xpath: XPath to instance name
                - properties: Dict of property_name -> xpath mappings

        Returns:
            List of DiscoveredInstance objects
        """
        from lmn_tools.collectors.xml.parser import XmlParser

        filter_xml = config.get("netconf_filter", "")
        if not filter_xml:
            self._debug_print("No NETCONF filter specified")
            return []

        self._debug_print(f"Executing discovery with filter length: {len(filter_xml)}")

        # Merge device namespaces with config namespaces
        namespaces = self.get_namespaces()
        namespaces.update(config.get("namespaces", {}))

        # Get data from device
        data = self.get(filter_xml)

        # Parse instances using XmlParser
        parser = XmlParser(namespaces=namespaces, debug=self.debug)
        instances = parser.discover_instances(data, config)

        self._debug_print(f"Discovered {len(instances)} instances")
        return instances

    def collect(self, config: dict[str, Any]) -> list[MetricValue]:
        """
        Collect metrics using NETCONF.

        Args:
            config: Collection configuration containing:
                - netconf_filter: XML filter for get operation
                - namespaces: XML namespace mappings
                - instance_xpath: XPath to instance elements
                - id_xpath: XPath to instance ID within element
                - metrics: List of metric definitions with:
                    - name: Metric name
                    - xpath: XPath to metric value
                    - string_map: Optional string-to-int mapping

        Returns:
            List of MetricValue objects
        """
        from lmn_tools.collectors.xml.parser import XmlParser

        filter_xml = config.get("netconf_filter", "")
        if not filter_xml:
            self._debug_print("No NETCONF filter specified")
            return []

        self._debug_print(f"Executing collection with filter length: {len(filter_xml)}")

        # Merge device namespaces with config namespaces
        namespaces = self.get_namespaces()
        namespaces.update(config.get("namespaces", {}))

        # Get data from device
        data = self.get(filter_xml)

        # Parse metrics using XmlParser
        parser = XmlParser(namespaces=namespaces, debug=self.debug)
        metrics = parser.collect_metrics(data, config)

        self._debug_print(f"Collected {len(metrics)} metrics")
        return metrics
