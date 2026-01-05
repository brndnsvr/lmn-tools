"""
NETCONF client for connecting to optical transport devices.

Provides a context manager-based interface for establishing NETCONF sessions
and executing RPC operations against Coriant and Ciena devices.
"""

import logging
import socket
import sys
from typing import Optional, List, Union
from lxml import etree

from .debug import get_debug_helper

logger = logging.getLogger(__name__)


class NetconfClientError(Exception):
    """Base exception for NETCONF client errors."""
    pass


class NetconfConnectionError(NetconfClientError):
    """Raised when connection to device fails."""
    pass


class NetconfRPCError(NetconfClientError):
    """Raised when an RPC operation fails."""
    pass


class NetconfClient:
    """
    NETCONF client for optical transport devices.

    Provides context manager interface for clean session lifecycle management.

    Usage:
        with NetconfClient(hostname, username, password) as client:
            response = client.get(filter_xml)
            # Process response...

    Or for manual control:
        client = NetconfClient(hostname, username, password)
        client.connect()
        try:
            response = client.get(filter_xml)
        finally:
            client.disconnect()
    """

    # Default NETCONF port
    DEFAULT_PORT = 830

    # Default timeout in seconds
    DEFAULT_TIMEOUT = 60

    # Known device types and their capabilities
    DEVICE_TYPES = {
        "coriant": {
            "device_params": {"name": "default"},
            "namespaces": {
                "ne": "http://coriant.com/yang/os/ne",
            }
        },
        "ciena": {
            "device_params": {"name": "default"},
            "namespaces": {
                "ws-ptps": "urn:ciena:params:xml:ns:yang:ciena-ws-ptps",
                "ws-ptp": "urn:ciena:params:xml:ns:yang:ciena-ws-ptp",
            }
        }
    }

    def __init__(
        self,
        hostname: str,
        username: str,
        password: str,
        port: int = DEFAULT_PORT,
        timeout: int = DEFAULT_TIMEOUT,
        hostkey_verify: bool = False,
        device_type: Optional[str] = None,
        debug: bool = False
    ):
        """
        Initialize the NETCONF client.

        Args:
            hostname: Device hostname or IP address
            username: NETCONF username
            password: NETCONF password
            port: NETCONF port (default: 830)
            timeout: Operation timeout in seconds (default: 60)
            hostkey_verify: Verify SSH host keys (default: False for lab environments)
            device_type: Optional device type hint ("coriant" or "ciena")
            debug: Enable debug logging
        """
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.hostkey_verify = hostkey_verify
        self.device_type = device_type
        self.debug = debug

        self._manager = None
        self._connected = False
        self._capabilities = []
        self._debug_helper = get_debug_helper(enabled=debug)

        if debug:
            logging.getLogger("ncclient").setLevel(logging.DEBUG)

    def __enter__(self):
        """Context manager entry - establish connection."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection."""
        self.disconnect()
        return False  # Don't suppress exceptions

    @property
    def connected(self) -> bool:
        """Check if currently connected to device."""
        return self._connected and self._manager is not None

    @property
    def capabilities(self) -> List[str]:
        """Get device NETCONF capabilities (after connection)."""
        return self._capabilities

    def connect(self) -> None:
        """
        Establish NETCONF connection to device.

        Raises:
            NetconfConnectionError: If connection fails
        """
        if self._connected:
            logger.debug(f"Already connected to {self.hostname}")
            return

        # Output connection info in debug mode
        self._debug_helper.connection_info(
            hostname=self.hostname,
            port=self.port,
            username=self.username,
            device_type=self.device_type,
            timeout=self.timeout
        )

        try:
            from ncclient import manager
            from ncclient.transport.errors import AuthenticationError, SSHError
        except ImportError as e:
            raise NetconfClientError(
                f"ncclient library not installed or import failed. "
                f"Run: pip install ncclient lxml\n"
                f"Import error: {e}"
            )

        # Get device-specific parameters if known
        device_params = {"name": "default"}
        if self.device_type and self.device_type in self.DEVICE_TYPES:
            device_params = self.DEVICE_TYPES[self.device_type].get(
                "device_params", device_params
            )

        logger.info(f"Connecting to {self.hostname}:{self.port}")

        try:
            self._manager = manager.connect(
                host=self.hostname,
                port=self.port,
                username=self.username,
                password=self.password,
                hostkey_verify=self.hostkey_verify,
                timeout=self.timeout,
                device_params=device_params,
                allow_agent=False,
                look_for_keys=False,
            )
            self._connected = True
            self._capabilities = list(self._manager.server_capabilities)

            logger.info(
                f"Connected to {self.hostname} - "
                f"{len(self._capabilities)} capabilities"
            )

            # Output session info in debug mode
            session_id = None
            if hasattr(self._manager, 'session_id'):
                session_id = str(self._manager.session_id)
            detected_type = self.detect_device_type()

            self._debug_helper.session_info(
                session_id=session_id,
                capabilities=self._capabilities,
                detected_type=detected_type
            )

        except AuthenticationError as e:
            raise NetconfConnectionError(
                f"Authentication failed for {self.username}@{self.hostname}. "
                f"Please verify:\n"
                f"  - Username and password are correct\n"
                f"  - User has NETCONF access permissions\n"
                f"  - NETCONF is enabled on the device\n"
                f"Error: {e}"
            )
        except SSHError as e:
            error_str = str(e).lower()
            if "connection refused" in error_str:
                raise NetconfConnectionError(
                    f"Connection refused to {self.hostname}:{self.port}. "
                    f"Please verify:\n"
                    f"  - Device is reachable (ping {self.hostname})\n"
                    f"  - NETCONF/SSH is enabled on port {self.port}\n"
                    f"  - No firewall blocking the connection\n"
                    f"  - Correct port (default NETCONF: 830, SSH: 22)\n"
                    f"Error: {e}"
                )
            elif "timed out" in error_str or "timeout" in error_str:
                raise NetconfConnectionError(
                    f"Connection timed out to {self.hostname}:{self.port}. "
                    f"Please verify:\n"
                    f"  - Device is reachable (ping {self.hostname})\n"
                    f"  - Network path is available\n"
                    f"  - Try increasing timeout (current: {self.timeout}s)\n"
                    f"Error: {e}"
                )
            elif "host key" in error_str:
                raise NetconfConnectionError(
                    f"SSH host key verification failed for {self.hostname}. "
                    f"Set hostkey_verify=False or add host key to known_hosts.\n"
                    f"Error: {e}"
                )
            else:
                raise NetconfConnectionError(
                    f"SSH connection failed to {self.hostname}:{self.port}. "
                    f"Please verify device is reachable and NETCONF is enabled.\n"
                    f"Error: {e}"
                )
        except socket.gaierror as e:
            raise NetconfConnectionError(
                f"DNS resolution failed for hostname '{self.hostname}'. "
                f"Please verify:\n"
                f"  - Hostname is spelled correctly\n"
                f"  - DNS is working (try IP address instead)\n"
                f"Error: {e}"
            )
        except socket.timeout as e:
            raise NetconfConnectionError(
                f"Socket timeout connecting to {self.hostname}:{self.port}. "
                f"The device may be unreachable or overloaded.\n"
                f"Error: {e}"
            )
        except Exception as e:
            # Catch-all for unexpected errors
            error_type = type(e).__name__
            raise NetconfConnectionError(
                f"Failed to connect to {self.hostname}:{self.port}. "
                f"Unexpected error ({error_type}): {e}"
            )

    def disconnect(self) -> None:
        """Close NETCONF connection."""
        if self._manager:
            try:
                self._manager.close_session()
                logger.info(f"Disconnected from {self.hostname}")
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
            finally:
                self._manager = None
                self._connected = False
                self._capabilities = []

    def get(
        self,
        filter_xml: Union[str, etree._Element, None] = None
    ) -> etree._Element:
        """
        Execute NETCONF <get> RPC operation.

        Args:
            filter_xml: Optional subtree filter as XML string or lxml Element.
                       If None, retrieves all operational data (not recommended).

        Returns:
            lxml Element containing the <data> response

        Raises:
            NetconfRPCError: If the RPC operation fails
        """
        if not self._connected:
            raise NetconfClientError("Not connected to device")

        try:
            # Convert string filter to tuple format for ncclient
            if filter_xml is not None:
                if isinstance(filter_xml, str):
                    filter_elem = etree.fromstring(filter_xml.encode())
                else:
                    filter_elem = filter_xml

                # Output filter in debug mode
                self._debug_helper.filter_xml(filter_elem)

                # ncclient wants ("subtree", element)
                filter_spec = ("subtree", filter_elem)
            else:
                filter_spec = None

            logger.debug(f"Executing get RPC on {self.hostname}")

            response = self._manager.get(filter=filter_spec)

            # Response is an GetReply object, get the data element
            if hasattr(response, "data_ele"):
                data = response.data_ele
            elif hasattr(response, "data"):
                # Some versions return data as string
                if isinstance(response.data, str):
                    data = etree.fromstring(response.data.encode())
                else:
                    data = response.data
            else:
                # Try to parse from xml attribute
                data = etree.fromstring(str(response).encode())

            # Output response in debug mode
            self._debug_helper.response_xml(data)

            return data

        except Exception as e:
            self._debug_helper.error("Get RPC failed", exception=e)
            raise NetconfRPCError(f"Get RPC failed: {e}")

    def get_config(
        self,
        source: str = "running",
        filter_xml: Union[str, etree._Element, None] = None
    ) -> etree._Element:
        """
        Execute NETCONF <get-config> RPC operation.

        Args:
            source: Configuration datastore ("running", "candidate", "startup")
            filter_xml: Optional subtree filter

        Returns:
            lxml Element containing the configuration data

        Raises:
            NetconfRPCError: If the RPC operation fails
        """
        if not self._connected:
            raise NetconfClientError("Not connected to device")

        try:
            if filter_xml is not None:
                if isinstance(filter_xml, str):
                    filter_elem = etree.fromstring(filter_xml.encode())
                else:
                    filter_elem = filter_xml
                filter_spec = ("subtree", filter_elem)
            else:
                filter_spec = None

            logger.debug(f"Executing get-config RPC on {self.hostname}")

            response = self._manager.get_config(source=source, filter=filter_spec)

            if hasattr(response, "data_ele"):
                return response.data_ele
            elif hasattr(response, "data"):
                if isinstance(response.data, str):
                    return etree.fromstring(response.data.encode())
                return response.data
            else:
                return etree.fromstring(str(response).encode())

        except Exception as e:
            raise NetconfRPCError(f"Get-config RPC failed: {e}")

    def build_filter(self, config_xml: Union[str, etree._Element]) -> etree._Element:
        """
        Build a subtree filter from a configuration template.

        Removes non-xmlns attributes to create a proper subtree filter
        that can be sent to the device.

        Args:
            config_xml: XML string or Element with metric/label attributes

        Returns:
            Clean Element suitable for use as subtree filter
        """
        if isinstance(config_xml, str):
            element = etree.fromstring(config_xml.encode())
        else:
            element = etree.fromstring(etree.tostring(config_xml))  # Deep copy

        self._clean_filter_attributes(element)
        return element

    def _clean_filter_attributes(self, element: etree._Element) -> None:
        """
        Recursively remove non-xmlns attributes from filter elements.

        Removes attributes like class, type, help, string_map etc. that
        are used for metric definition but shouldn't be sent to device.
        """
        # Attributes to keep (namespace declarations)
        keep_patterns = ["xmlns", "{"]

        # Remove non-namespace attributes
        attribs_to_remove = []
        for attrib in element.attrib:
            keep = False
            for pattern in keep_patterns:
                if pattern in attrib:
                    keep = True
                    break
            if not keep:
                attribs_to_remove.append(attrib)

        for attrib in attribs_to_remove:
            del element.attrib[attrib]

        # Recurse to children
        for child in element:
            self._clean_filter_attributes(child)

    def detect_device_type(self) -> Optional[str]:
        """
        Attempt to detect device type from capabilities.

        Returns:
            "coriant", "ciena", or None if unknown
        """
        if not self._capabilities:
            return None

        caps_lower = [c.lower() for c in self._capabilities]
        caps_str = " ".join(caps_lower)

        if "coriant" in caps_str:
            return "coriant"
        elif "ciena" in caps_str or "waveserver" in caps_str:
            return "ciena"

        return None


def create_client_from_args(args) -> NetconfClient:
    """
    Create a NetconfClient from parsed command-line arguments.

    Args:
        args: Parsed argparse namespace with hostname, username, password, port, debug

    Returns:
        Configured NetconfClient instance
    """
    return NetconfClient(
        hostname=args.hostname,
        username=args.username,
        password=args.password,
        port=getattr(args, 'port', NetconfClient.DEFAULT_PORT),
        timeout=getattr(args, 'timeout', NetconfClient.DEFAULT_TIMEOUT),
        debug=getattr(args, 'debug', False),
    )
