"""
Debug helper module for enhanced --debug output.

Provides structured debug output for troubleshooting NETCONF operations
and metric collection.
"""

import logging
import sys
from typing import Any

from lxml import etree

logger = logging.getLogger(__name__)


class DebugHelper:
    """
    Helper class for enhanced debug output.

    Provides methods to output structured debug information for:
    - Connection details
    - NETCONF session info
    - XML filter being sent
    - Raw XML response
    - Parsing steps
    - Instance discovery
    - Metric extraction
    """

    def __init__(self, enabled: bool = False, output: Any = None) -> None:
        """
        Initialize debug helper.

        Args:
            enabled: Whether debug output is enabled
            output: Output stream (default: sys.stderr)
        """
        self.enabled = enabled
        self.output = output or sys.stderr
        self._indent = 0

    def _print(self, message: str, indent: int = 0) -> None:
        """Print message with indentation."""
        if not self.enabled:
            return
        prefix = "  " * (self._indent + indent)
        print(f"DEBUG: {prefix}{message}", file=self.output)

    def _print_separator(self, char: str = "=", length: int = 60) -> None:
        """Print a separator line."""
        if not self.enabled:
            return
        print(f"DEBUG: {char * length}", file=self.output)

    def section(self, title: str) -> None:
        """Print a section header."""
        if not self.enabled:
            return
        self._print_separator()
        self._print(f"[{title}]")
        self._print_separator("-", 60)

    def connection_info(
        self,
        hostname: str,
        port: int,
        username: str,
        device_type: str | None = None,
        timeout: int = 60
    ) -> None:
        """Print connection details."""
        self.section("CONNECTION INFO")
        self._print(f"Host: {hostname}")
        self._print(f"Port: {port}")
        self._print(f"Username: {username}")
        self._print(f"Device Type: {device_type or 'auto-detect'}")
        self._print(f"Timeout: {timeout}s")
        self._print("")

    def session_info(
        self,
        session_id: str | None = None,
        capabilities: list[str] | None = None,
        detected_type: str | None = None
    ) -> None:
        """Print NETCONF session information."""
        self.section("SESSION INFO")
        if session_id:
            self._print(f"Session ID: {session_id}")
        if detected_type:
            self._print(f"Detected Device Type: {detected_type}")
        if capabilities:
            self._print(f"Capabilities ({len(capabilities)} total):")
            # Show first 5 capabilities
            for cap in capabilities[:5]:
                self._print(f"  - {cap}")
            if len(capabilities) > 5:
                self._print(f"  ... and {len(capabilities) - 5} more")
        self._print("")

    def filter_xml(self, filter_elem: etree._Element) -> None:
        """Print the XML filter being sent."""
        self.section("NETCONF FILTER")
        try:
            xml_str = etree.tostring(
                filter_elem,
                pretty_print=True,
                encoding='unicode'
            )
            # Limit to first 50 lines
            lines = xml_str.split('\n')
            for line in lines[:50]:
                self._print(line)
            if len(lines) > 50:
                self._print(f"... ({len(lines) - 50} more lines)")
        except Exception as e:
            self._print(f"Error formatting filter: {e}")
        self._print("")

    def response_xml(self, data: etree._Element, max_lines: int = 100) -> None:
        """Print the raw XML response."""
        self.section("NETCONF RESPONSE")
        try:
            xml_str = etree.tostring(
                data,
                pretty_print=True,
                encoding='unicode'
            )
            lines = xml_str.split('\n')
            self._print(f"Response size: {len(xml_str)} bytes, {len(lines)} lines")
            self._print("")
            for line in lines[:max_lines]:
                self._print(line)
            if len(lines) > max_lines:
                self._print(f"... ({len(lines) - max_lines} more lines)")
        except Exception as e:
            self._print(f"Error formatting response: {e}")
        self._print("")

    def parsing_start(self, config: dict[str, Any]) -> None:
        """Print parsing start info."""
        self.section("PARSING CONFIG")
        interfaces = config.get('interfaces', {})
        self._print(f"Interface types configured: {list(interfaces.keys())}")
        for iface_type, iface_config in interfaces.items():
            xpath = iface_config.get('xpath', '')
            metrics = iface_config.get('metrics', [])
            self._print(f"  {iface_type}:")
            self._print(f"    XPath: {xpath}")
            self._print(f"    Metrics: {len(metrics)}")
        self._print("")

    def interface_search(
        self,
        iface_type: str,
        xpath: str,
        found_count: int
    ) -> None:
        """Print interface search results."""
        if not self.enabled:
            return
        self._print(f"Searching for {iface_type} interfaces...")
        self._print(f"  XPath: {xpath}", indent=1)
        self._print(f"  Found: {found_count} elements", indent=1)

    def instance_found(
        self,
        instance_id: str,
        instance_name: str,
        iface_type: str,
        properties: dict[str, str] | None = None
    ) -> None:
        """Print discovered instance details."""
        if not self.enabled:
            return
        self._print(f"Instance: {instance_id}")
        self._print(f"  Name: {instance_name}", indent=1)
        self._print(f"  Type: {iface_type}", indent=1)
        if properties:
            self._print(f"  Properties: {len(properties)}", indent=1)
            for key, val in list(properties.items())[:5]:
                self._print(f"    {key}: {val}", indent=2)

    def metric_extracted(
        self,
        metric_name: str,
        raw_value: str | None,
        converted_value: float | None,
        instance_id: str | None = None
    ) -> None:
        """Print metric extraction details."""
        if not self.enabled:
            return
        status = "OK" if converted_value is not None else "FAILED"
        instance_str = f" [{instance_id}]" if instance_id else ""
        self._print(
            f"Metric{instance_str}: {metric_name} = "
            f"{raw_value} -> {converted_value} ({status})"
        )

    def discovery_summary(
        self,
        instances: list[Any],
        by_type: dict[str, int] | None = None
    ) -> None:
        """Print discovery summary."""
        self.section("DISCOVERY SUMMARY")
        self._print(f"Total instances discovered: {len(instances)}")
        if by_type:
            for iface_type, count in by_type.items():
                self._print(f"  {iface_type}: {count}")
        self._print("")

    def collection_summary(
        self,
        metrics: list[Any],
        by_instance: dict[str, int] | None = None
    ) -> None:
        """Print collection summary."""
        self.section("COLLECTION SUMMARY")
        self._print(f"Total metrics collected: {len(metrics)}")
        if by_instance:
            self._print(f"Instances with metrics: {len(by_instance)}")
            for instance_id, count in list(by_instance.items())[:10]:
                self._print(f"  {instance_id}: {count} metrics")
            if len(by_instance) > 10:
                self._print(f"  ... and {len(by_instance) - 10} more instances")
        self._print("")

    def error(self, message: str, exception: Exception | None = None) -> None:
        """Print error information."""
        self.section("ERROR")
        self._print(f"Message: {message}")
        if exception:
            self._print(f"Exception: {type(exception).__name__}")
            self._print(f"Details: {exception}")
        self._print("")


# Global debug helper instance
_debug_helper: DebugHelper | None = None


def get_debug_helper(enabled: bool = False) -> DebugHelper:
    """
    Get or create the global debug helper.

    Args:
        enabled: Whether debug is enabled

    Returns:
        DebugHelper instance
    """
    global _debug_helper
    if _debug_helper is None or _debug_helper.enabled != enabled:
        _debug_helper = DebugHelper(enabled=enabled)
    return _debug_helper
