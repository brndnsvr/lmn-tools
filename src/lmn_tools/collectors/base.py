"""
Abstract base class for device data collectors.

Provides a common interface for protocol-specific collectors
(NETCONF, SNMP, REST) with connection management and
standard discovery/collection operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from lmn_tools.models.discovery import DiscoveredInstance
from lmn_tools.models.metrics import MetricValue

# Type variable for credential types
CredentialT = TypeVar("CredentialT")


class BaseCollector(ABC, Generic[CredentialT]):
    """
    Abstract base class for device data collectors.

    Implements the context manager protocol for automatic
    connection management and defines the interface for
    discovery and collection operations.

    Type Parameters:
        CredentialT: The credential type used by this collector
                    (e.g., NetconfCredentials, SNMPv3Credentials)

    Attributes:
        hostname: Target device hostname or IP address
        credentials: Protocol-specific credentials
        debug: Enable debug output
    """

    def __init__(
        self,
        hostname: str,
        credentials: CredentialT,
        debug: bool = False,
    ):
        """
        Initialize the collector.

        Args:
            hostname: Target device hostname or IP address
            credentials: Protocol-specific credentials
            debug: Enable debug output
        """
        self.hostname = hostname
        self.credentials = credentials
        self.debug = debug
        self._connected: bool = False

    @property
    def connected(self) -> bool:
        """Return True if currently connected to the device."""
        return self._connected

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to the device.

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the device."""
        pass

    @abstractmethod
    def discover(self, config: dict[str, Any]) -> list[DiscoveredInstance]:
        """
        Run Active Discovery to find instances.

        Args:
            config: Discovery configuration dictionary containing:
                - Filters/queries for the specific protocol
                - Instance ID patterns
                - Property extraction rules

        Returns:
            List of DiscoveredInstance objects
        """
        pass

    @abstractmethod
    def collect(self, config: dict[str, Any]) -> list[MetricValue]:
        """
        Collect metrics from the device.

        Args:
            config: Collection configuration dictionary containing:
                - Filters/queries for the specific protocol
                - Metric extraction rules
                - String maps for value conversion

        Returns:
            List of MetricValue objects
        """
        pass

    def __enter__(self) -> BaseCollector[CredentialT]:
        """Enter context manager - connect to device."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        """Exit context manager - disconnect from device."""
        self.disconnect()
        # Don't suppress exceptions
        return False

    def _debug_print(self, message: str) -> None:
        """Print debug message if debug mode is enabled."""
        if self.debug:
            import sys

            print(f"DEBUG [{self.__class__.__name__}]: {message}", file=sys.stderr)
