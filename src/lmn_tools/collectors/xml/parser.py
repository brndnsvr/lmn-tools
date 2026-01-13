"""
XML parser for NETCONF response data.

Provides XPath-based extraction of instances and metrics
from XML data retrieved via NETCONF.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

from lmn_tools.constants import Patterns, StringMaps
from lmn_tools.models.discovery import DiscoveredInstance
from lmn_tools.models.metrics import MetricValue

if TYPE_CHECKING:
    from lxml import etree

logger = logging.getLogger(__name__)


class XmlParser:
    """
    Parser for extracting data from XML using XPath.

    Handles namespace-aware XPath queries and provides
    convenience methods for discovery and collection operations.

    Attributes:
        namespaces: Namespace prefix to URI mappings
        debug: Enable debug output
    """

    def __init__(
        self,
        namespaces: dict[str, str] | None = None,
        debug: bool = False,
    ):
        """
        Initialize XML parser.

        Args:
            namespaces: Namespace prefix to URI mappings for XPath
            debug: Enable debug output
        """
        self.namespaces = namespaces or {}
        self.debug = debug

    def _debug_print(self, message: str) -> None:
        """Print debug message if debug mode enabled."""
        if self.debug:
            print(f"DEBUG [XmlParser]: {message}", file=sys.stderr)

    def xpath(
        self,
        element: etree._Element,
        expression: str,
        single: bool = False,
    ) -> list[Any] | Any | None:
        """
        Execute XPath query with namespace support.

        Args:
            element: XML element to query
            expression: XPath expression
            single: If True, return first result or None

        Returns:
            List of results, or single result if single=True
        """
        try:
            results = element.xpath(expression, namespaces=self.namespaces)
            if single:
                return results[0] if results else None
            return results
        except Exception as e:
            self._debug_print(f"XPath error for '{expression}': {e}")
            return None if single else []

    def get_text(
        self,
        element: etree._Element,
        xpath_expr: str,
        default: str = "",
    ) -> str:
        """
        Get text content from XPath result.

        Args:
            element: XML element to query
            xpath_expr: XPath expression
            default: Default value if not found

        Returns:
            Text content or default
        """
        result = self.xpath(element, xpath_expr, single=True)
        if result is None:
            return default

        # Handle both Element and text results
        if hasattr(result, "text"):
            return result.text or default
        return str(result) if result else default

    def get_float(
        self,
        element: etree._Element,
        xpath_expr: str,
        default: float | None = None,
    ) -> float | None:
        """
        Get float value from XPath result.

        Args:
            element: XML element to query
            xpath_expr: XPath expression
            default: Default value if not found or invalid

        Returns:
            Float value or default
        """
        text = self.get_text(element, xpath_expr)
        if not text:
            return default
        try:
            return float(text)
        except (ValueError, TypeError):
            return default

    def get_int(
        self,
        element: etree._Element,
        xpath_expr: str,
        default: int | None = None,
    ) -> int | None:
        """
        Get integer value from XPath result.

        Args:
            element: XML element to query
            xpath_expr: XPath expression
            default: Default value if not found or invalid

        Returns:
            Integer value or default
        """
        value = self.get_float(element, xpath_expr)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def strip_namespaces(self, text: str) -> str:
        """
        Remove XML namespace prefixes and URIs from text.

        Args:
            text: Text that may contain namespace prefixes

        Returns:
            Text with namespaces removed
        """
        # Remove {namespace} URIs
        text = Patterns.XML_NAMESPACE_URI.sub("", text)
        # Remove prefix: prefixes
        text = Patterns.XML_NAMESPACE_PREFIX.sub("", text)
        return text

    def sanitize_instance_id(self, value: str) -> str:
        """
        Sanitize value for use as LogicMonitor instance ID.

        Removes characters that are invalid in LM instance IDs:
        - Colons (:)
        - Hashes (#)
        - Backslashes (\\)
        - Whitespace

        Args:
            value: Raw instance ID value

        Returns:
            Sanitized instance ID
        """
        import re

        if not value:
            return ""
        # Replace invalid characters with underscore
        sanitized = Patterns.INVALID_INSTANCE_ID_CHARS.sub("_", str(value))
        # Collapse multiple underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Strip leading/trailing underscores
        return sanitized.strip("_")

    def discover_instances(
        self,
        data: etree._Element,
        config: dict[str, Any],
    ) -> list[DiscoveredInstance]:
        """
        Discover instances from XML data.

        Args:
            data: XML data element
            config: Discovery configuration containing:
                - instance_xpath: XPath to instance elements
                - id_xpath: XPath to ID within instance element
                - name_xpath: XPath to name within instance (optional)
                - description_xpath: XPath to description (optional)
                - properties: Dict of property_name -> xpath mappings

        Returns:
            List of DiscoveredInstance objects
        """
        instance_xpath = config.get("instance_xpath", "")
        if not instance_xpath:
            self._debug_print("No instance_xpath specified")
            return []

        id_xpath = config.get("id_xpath", ".")
        name_xpath = config.get("name_xpath", "")
        desc_xpath = config.get("description_xpath", "")
        property_xpaths = config.get("properties", {})

        instances: list[DiscoveredInstance] = []
        elements = self.xpath(data, instance_xpath)
        if elements is None:
            elements = []

        self._debug_print(f"Found {len(elements)} elements at {instance_xpath}")

        for elem in elements:
            # Get instance ID
            raw_id = self.get_text(elem, id_xpath)
            if not raw_id:
                continue

            instance_id = self.sanitize_instance_id(raw_id)
            if not instance_id:
                continue

            # Get instance name (defaults to ID)
            if name_xpath:
                instance_name = self.get_text(elem, name_xpath) or instance_id
            else:
                instance_name = instance_id

            # Get description
            description = ""
            if desc_xpath:
                description = self.get_text(elem, desc_xpath)

            # Extract properties
            properties: dict[str, str] = {}
            for prop_name, prop_xpath in property_xpaths.items():
                prop_value = self.get_text(elem, prop_xpath)
                if prop_value:
                    properties[prop_name] = prop_value

            instances.append(
                DiscoveredInstance(
                    instance_id=instance_id,
                    instance_name=instance_name,
                    description=description,
                    properties=properties,
                )
            )

        return instances

    def collect_metrics(
        self,
        data: etree._Element,
        config: dict[str, Any],
    ) -> list[MetricValue]:
        """
        Collect metrics from XML data.

        Args:
            data: XML data element
            config: Collection configuration containing:
                - instance_xpath: XPath to instance elements
                - id_xpath: XPath to ID within instance element
                - metrics: List of metric definitions:
                    - name: Metric name
                    - xpath: XPath to value within instance
                    - string_map: Optional string-to-int map name
                    - multiplier: Optional value multiplier

        Returns:
            List of MetricValue objects
        """
        instance_xpath = config.get("instance_xpath", "")
        if not instance_xpath:
            self._debug_print("No instance_xpath specified")
            return []

        id_xpath = config.get("id_xpath", ".")
        metric_defs = config.get("metrics", [])

        if not metric_defs:
            self._debug_print("No metrics defined")
            return []

        metrics: list[MetricValue] = []
        elements = self.xpath(data, instance_xpath)
        if elements is None:
            elements = []

        self._debug_print(f"Found {len(elements)} elements, {len(metric_defs)} metrics defined")

        for elem in elements:
            # Get instance ID
            raw_id = self.get_text(elem, id_xpath)
            if not raw_id:
                continue

            instance_id = self.sanitize_instance_id(raw_id)
            if not instance_id:
                continue

            # Extract each metric
            for metric_def in metric_defs:
                metric_name = metric_def.get("name", "")
                metric_xpath = metric_def.get("xpath", "")

                if not metric_name or not metric_xpath:
                    continue

                raw_value = self.get_text(elem, metric_xpath)
                if not raw_value:
                    continue

                # Apply string map if specified
                string_map_name = metric_def.get("string_map")
                if string_map_name:
                    try:
                        string_map = StringMaps.get_map(string_map_name)
                        if raw_value in string_map:
                            value = float(string_map[raw_value])
                        else:
                            self._debug_print(
                                f"Value '{raw_value}' not in string map '{string_map_name}'"
                            )
                            continue
                    except KeyError:
                        self._debug_print(f"Unknown string map: {string_map_name}")
                        continue
                else:
                    # Try to parse as float
                    try:
                        value = float(raw_value)
                    except (ValueError, TypeError):
                        self._debug_print(
                            f"Cannot convert '{raw_value}' to float for {metric_name}"
                        )
                        continue

                # Apply multiplier if specified
                multiplier = metric_def.get("multiplier")
                if multiplier is not None:
                    value *= float(multiplier)

                metrics.append(
                    MetricValue(
                        name=metric_name,
                        value=value,
                        instance_id=instance_id,
                    )
                )

        return metrics

    def elements_to_dict(
        self,
        element: etree._Element,
        strip_ns: bool = True,
    ) -> dict[str, Any] | str:
        """
        Convert XML element tree to nested dictionary.

        Args:
            element: XML element to convert
            strip_ns: Whether to strip namespace prefixes from keys

        Returns:
            Nested dictionary representation or string for leaf text nodes
        """
        result: dict[str, Any] = {}

        tag = element.tag
        if strip_ns:
            tag = self.strip_namespaces(tag)

        # Handle text content
        if element.text and element.text.strip():
            if len(element) == 0:  # No children
                text: str = element.text.strip()
                return text
            result["_text"] = element.text.strip()

        # Handle attributes
        for attr, value in element.attrib.items():
            attr_name = self.strip_namespaces(attr) if strip_ns else attr
            result[f"@{attr_name}"] = value

        # Handle children
        for child in element:
            child_tag = child.tag
            if strip_ns:
                child_tag = self.strip_namespaces(child_tag)

            child_value = self.elements_to_dict(child, strip_ns)

            if child_tag in result:
                # Convert to list if multiple children with same tag
                if not isinstance(result[child_tag], list):
                    result[child_tag] = [result[child_tag]]
                result[child_tag].append(child_value)
            else:
                result[child_tag] = child_value

        return result if result else {}
