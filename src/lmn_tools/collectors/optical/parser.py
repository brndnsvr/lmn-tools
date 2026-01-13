"""
XML parser for extracting metrics from NETCONF responses.

Walks the XML response tree alongside a configuration specification
to extract metrics and labels according to defined rules.
"""

import logging
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any

from lxml import etree

from .debug import get_debug_helper
from .utils import (
    extract_element_text,
    get_local_name,
    parse_string_map_definition,
    parse_timestamp,
    safe_float,
    sanitize_instance_id,
    sanitize_metric_name,
)

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """Represents a single metric value extracted from XML."""
    name: str                           # Metric name (e.g., "rx_optical_power")
    value: float                        # Numeric value
    labels: dict[str, str] = field(default_factory=dict)  # Associated labels
    instance_id: str | None = None   # LogicMonitor instance ID
    instance_name: str | None = None # Human-readable instance name
    help_text: str | None = None     # Metric description


@dataclass
class DiscoveredInstance:
    """Represents a discovered instance for LogicMonitor Active Discovery."""
    instance_id: str                    # Unique ID (sanitized)
    instance_name: str                  # Display name
    description: str = ""               # Optional description
    properties: dict[str, str] = field(default_factory=dict)  # auto.* properties


@dataclass
class MetricConfig:
    """Configuration for a single metric from YAML config."""
    name: str
    xpath: str
    metric_type: str = "gauge"
    help_text: str = ""
    string_map: dict[str, int] | None = None
    parse_timestamp: bool = False


@dataclass
class InterfaceConfig:
    """Configuration for an interface type (OTS, OSC, etc.)."""
    name: str                           # Interface type name
    xpath: str                          # XPath to interface list
    instance_key: str                   # Element that identifies each instance
    instance_name_key: str | None = None  # Element for display name
    description_key: str | None = None    # Element for description
    metrics: list[MetricConfig] = field(default_factory=list)
    properties: list[str] = field(default_factory=list)  # Additional properties


class XmlParser:
    """
    Parser for extracting metrics from NETCONF XML responses.

    This class handles:
    - Walking XML response trees
    - Matching elements against configuration specs
    - Extracting metric values with transformations
    - Handling parent label propagation
    - Building instance hierarchies for LogicMonitor
    """

    def __init__(
        self,
        namespaces: dict[str, str] | None = None,
        debug: bool = False
    ):
        """
        Initialize the XML parser.

        Args:
            namespaces: Dict of prefix -> namespace URI for XPath queries
            debug: Enable debug logging
        """
        self.namespaces = namespaces or {}
        self.debug = debug
        self._debug_helper = get_debug_helper(enabled=debug)

        # Add common namespaces
        self._default_namespaces = {
            "nc": "urn:ietf:params:xml:ns:netconf:base:1.0",
            "ne": "http://coriant.com/yang/os/ne",
        }

    def parse_response(
        self,
        data: etree._Element,
        config: dict[str, Any]
    ) -> tuple[list[DiscoveredInstance], list[MetricValue]]:
        """
        Parse a NETCONF response and extract instances and metrics.

        Args:
            data: The XML data element from NETCONF response
            config: Configuration dict defining what to extract

        Returns:
            Tuple of (discovered_instances, metric_values)
        """
        instances = []
        metrics = []

        # Output parsing config in debug mode
        self._debug_helper.parsing_start(config)

        # Get namespace map from config
        ns = config.get("namespaces", {})
        ns.update(self._default_namespaces)
        ns.update(self.namespaces)

        # Track instances by type for summary
        instances_by_type: dict[str, int] = {}

        # Process each interface type defined in config
        for iface_type, iface_config in config.get("interfaces", {}).items():
            iface_instances, iface_metrics = self._process_interface_type(
                data=data,
                iface_type=iface_type,
                iface_config=iface_config,
                namespaces=ns
            )
            instances.extend(iface_instances)
            metrics.extend(iface_metrics)
            instances_by_type[iface_type] = len(iface_instances)

        # Process chassis/global metrics
        if "chassis" in config:
            chassis_metrics = self._process_chassis_metrics(
                data=data,
                chassis_config=config["chassis"],
                namespaces=ns
            )
            metrics.extend(chassis_metrics)

        return instances, metrics

    def _process_interface_type(
        self,
        data: etree._Element,
        iface_type: str,
        iface_config: dict[str, Any],
        namespaces: dict[str, str]
    ) -> tuple[list[DiscoveredInstance], list[MetricValue]]:
        """
        Process a single interface type (OTS, OSC, OMS, etc.).

        Args:
            data: XML data element
            iface_type: Interface type name (e.g., "ots")
            iface_config: Configuration for this interface type
            namespaces: Namespace map for XPath

        Returns:
            Tuple of (instances, metrics) for this interface type
        """
        instances = []
        metrics = []

        xpath = iface_config.get("xpath", "")
        instance_key = iface_config.get("instance_key", "alias-name")
        instance_name_key = iface_config.get("instance_name_key", instance_key)
        description_key = iface_config.get("description_key")
        fallback_id_key = iface_config.get("fallback_id_key")  # e.g., "ots-name"
        metric_configs = iface_config.get("metrics", [])
        property_keys = iface_config.get("properties", [])

        # Find all interface elements
        interface_elements = self._find_elements(data, xpath, namespaces)

        logger.debug(f"Found {len(interface_elements)} {iface_type} interfaces")

        # Output interface search results in debug mode
        self._debug_helper.interface_search(
            iface_type=iface_type,
            xpath=xpath,
            found_count=len(interface_elements)
        )

        for elem in interface_elements:
            # Extract instance ID - prefer alias-name, fallback to interface name
            raw_id = self._get_child_text(elem, instance_key, namespaces)

            # Fallback: use interface-specific name (e.g., ots-name, osc-name)
            if not raw_id and fallback_id_key:
                raw_id = self._get_child_text(elem, fallback_id_key, namespaces)

            # Final fallback: construct from interface type + element position
            if not raw_id:
                # Try to get the interface name element (e.g., ots-name)
                name_key = f"{iface_type}-name"
                raw_id = self._get_child_text(elem, name_key, namespaces)

            if not raw_id:
                logger.warning(f"No instance ID found for {iface_type} element, skipping")
                continue

            instance_id = sanitize_instance_id(raw_id)

            # Extract instance name (prefer alias-name for display)
            instance_name = None
            if instance_name_key:
                instance_name = self._get_child_text(
                    elem, instance_name_key, namespaces
                )
            # Fallback to raw_id if no instance name
            if not instance_name:
                instance_name = raw_id

            # Extract description (typically the interface name like OTS-1-1-1)
            description = ""
            if description_key:
                description = self._get_child_text(
                    elem, description_key, namespaces
                ) or ""

            # Extract properties for auto.* fields
            properties = {}
            for prop_key in property_keys:
                prop_value = self._get_child_text(elem, prop_key, namespaces)
                if prop_value:
                    prop_name = sanitize_metric_name(prop_key)
                    properties[prop_name] = prop_value

            # Add interface type as property
            properties["interface_type"] = iface_type

            # Create discovered instance
            instance = DiscoveredInstance(
                instance_id=instance_id,
                instance_name=instance_name,
                description=description,
                properties=properties
            )
            instances.append(instance)

            # Output instance discovery in debug mode
            self._debug_helper.instance_found(
                instance_id=instance_id,
                instance_name=instance_name,
                iface_type=iface_type,
                properties=properties
            )

            # Extract metrics for this instance
            for metric_config in metric_configs:
                metric_value = self._extract_metric(
                    element=elem,
                    metric_config=metric_config,
                    instance_id=instance_id,
                    namespaces=namespaces
                )
                if metric_value is not None:
                    metrics.append(metric_value)

        return instances, metrics

    def _process_chassis_metrics(
        self,
        data: etree._Element,
        chassis_config: dict[str, Any],
        namespaces: dict[str, str]
    ) -> list[MetricValue]:
        """
        Process chassis-level (global) metrics.

        Args:
            data: XML data element
            chassis_config: Configuration for chassis metrics
            namespaces: Namespace map

        Returns:
            List of chassis metric values
        """
        metrics: list[MetricValue] = []

        xpath = chassis_config.get("xpath", "")
        metric_configs = chassis_config.get("metrics", [])

        # Find chassis element
        if xpath:
            chassis_elements = self._find_elements(data, xpath, namespaces)
            if not chassis_elements:
                return metrics
            chassis_elem = chassis_elements[0]
        else:
            chassis_elem = data

        # Extract each metric
        for metric_config in metric_configs:
            metric_value = self._extract_metric(
                element=chassis_elem,
                metric_config=metric_config,
                instance_id="_chassis_",  # Special chassis instance
                namespaces=namespaces
            )
            if metric_value is not None:
                metrics.append(metric_value)

        return metrics

    def _extract_metric(
        self,
        element: etree._Element,
        metric_config: dict[str, Any],
        instance_id: str,
        namespaces: dict[str, str]
    ) -> MetricValue | None:
        """
        Extract a single metric value from an element.

        Args:
            element: Parent XML element
            metric_config: Configuration for this metric
            instance_id: Instance ID to associate with metric
            namespaces: Namespace map

        Returns:
            MetricValue or None if extraction fails
        """
        name = metric_config.get("name", "")
        xpath = metric_config.get("xpath", "")
        string_map_def = metric_config.get("string_map")
        do_parse_timestamp = metric_config.get("parse_timestamp", False)
        help_text = metric_config.get("help", "")

        # Find the metric element
        raw_value = self._get_child_text(element, xpath, namespaces)

        if raw_value is None:
            logger.debug(f"No value found for metric {name} at {xpath}")
            return None

        # Apply transformations
        value = self._transform_value(
            raw_value=raw_value,
            string_map=string_map_def,
            do_parse_timestamp=do_parse_timestamp
        )

        if value is None:
            logger.debug(f"Failed to transform value for {name}: {raw_value}")
            # Output metric extraction failure in debug mode
            self._debug_helper.metric_extracted(
                metric_name=name,
                raw_value=raw_value,
                converted_value=None,
                instance_id=instance_id
            )
            return None

        # Output metric extraction success in debug mode
        self._debug_helper.metric_extracted(
            metric_name=name,
            raw_value=raw_value,
            converted_value=value,
            instance_id=instance_id
        )

        return MetricValue(
            name=name,
            value=value,
            instance_id=instance_id,
            help_text=help_text
        )

    def _transform_value(
        self,
        raw_value: str,
        string_map: dict[str, int] | None = None,
        do_parse_timestamp: bool = False
    ) -> float | None:
        """
        Transform a raw string value to numeric.

        Applies transformations in order:
        1. String map conversion
        2. Timestamp parsing
        3. Direct float conversion

        Args:
            raw_value: Raw string value from XML
            string_map: Optional string->int mapping
            do_parse_timestamp: Whether to parse as timestamp

        Returns:
            Numeric value or None if conversion fails
        """
        if raw_value is None:
            return None

        raw_value = raw_value.strip()

        # Apply string map if defined
        if string_map:
            if isinstance(string_map, str):
                string_map = parse_string_map_definition(string_map)
            if raw_value in string_map:
                return float(string_map[raw_value])
            # String map defined but value not in map - return default 0
            logger.debug(f"Value '{raw_value}' not in string_map, using 0")
            return 0.0

        # Parse timestamp if requested
        if do_parse_timestamp:
            ts = parse_timestamp(raw_value)
            if ts is not None:
                return ts
            return None

        # Try direct float conversion
        return safe_float(raw_value)

    def _find_elements(
        self,
        root: etree._Element,
        xpath: str,
        namespaces: dict[str, str]
    ) -> list[etree._Element]:
        """
        Find elements matching an XPath expression.

        Handles both namespaced and non-namespaced XPath queries.

        Args:
            root: Root element to search from
            xpath: XPath expression
            namespaces: Namespace map

        Returns:
            List of matching elements
        """
        if not xpath:
            return [root]

        try:
            # Try with namespaces first
            elements = root.xpath(xpath, namespaces=namespaces)
            if elements:
                result: list[etree._Element] = elements
                return result
        except Exception as e:
            logger.debug(f"XPath with namespaces failed: {e}")

        # Try without namespace prefix
        try:
            # Convert namespaced path to local-name() based path
            local_xpath = self._convert_to_local_xpath(xpath)
            elements = root.xpath(local_xpath)
            if elements:
                result2: list[etree._Element] = elements
                return result2
        except Exception as e:
            logger.debug(f"Local XPath failed: {e}")

        # Fallback: try simple element finding
        try:
            elements = self._find_by_local_name(root, xpath)
            return elements
        except Exception:
            pass

        return []

    def _convert_to_local_xpath(self, xpath: str) -> str:
        """
        Convert XPath to use local-name() for namespace-agnostic matching.

        Example: "ne:services/ne:optical-interfaces/ne:ots"
             ->  "*[local-name()='services']/*[local-name()='optical-interfaces']/*[local-name()='ots']"

        Example: ".//ots" -> ".//*[local-name()='ots']"
        """
        parts = xpath.split('/')
        converted = []

        for part in parts:
            if not part:
                converted.append('')
                continue

            # Handle special XPath operators
            if part == '.':
                converted.append('.')
                continue
            elif part == '..':
                converted.append('..')
                continue

            # Remove namespace prefix if present
            if ':' in part:
                part = part.split(':')[-1]

            if part == '*':
                converted.append('*')
            elif part.startswith('@'):
                converted.append(part)
            elif '[' in part:
                # Handle predicates
                base = part.split('[')[0]
                pred = '[' + '['.join(part.split('[')[1:])
                converted.append(f"*[local-name()='{base}']{pred}")
            else:
                converted.append(f"*[local-name()='{part}']")

        return '/'.join(converted)

    def _find_by_local_name(
        self,
        root: etree._Element,
        path: str
    ) -> list[etree._Element]:
        """
        Find elements by walking path segments using local names.

        This is a fallback when XPath doesn't work due to namespace issues.
        """
        parts = [p for p in path.split('/') if (p and ':' not in p) or True]
        # Strip namespace prefixes
        parts = [p.split(':')[-1] if ':' in p else p for p in parts]

        current = [root]

        for part in parts:
            if not part:
                continue

            next_elements = []
            for elem in current:
                for child in elem:
                    local_name = get_local_name(child.tag)
                    if local_name == part:
                        next_elements.append(child)

            current = next_elements

            if not current:
                break

        return current

    def _get_child_text(
        self,
        element: etree._Element,
        path: str,
        namespaces: dict[str, str]
    ) -> str | None:
        """
        Get text content of a child element.

        Args:
            element: Parent element
            path: Path to child (can be simple name or XPath)
            namespaces: Namespace map

        Returns:
            Text content or None
        """
        # Handle nested paths
        if '/' in path:
            children = self._find_elements(element, path, namespaces)
            if children:
                return extract_element_text(children[0])
            return None

        # Simple child element lookup
        # Strip namespace prefix if present
        local_path = path.split(':')[-1] if ':' in path else path

        # Try direct child lookup
        for child in element:
            child_local = get_local_name(child.tag)
            if child_local == local_path:
                return extract_element_text(child)

        return None

    def discover_instances(
        self,
        data: etree._Element,
        config: dict[str, Any]
    ) -> list[DiscoveredInstance]:
        """
        Discover instances from NETCONF data for Active Discovery.

        Args:
            data: XML data element from NETCONF response
            config: Configuration dict

        Returns:
            List of discovered instances
        """
        instances, _ = self.parse_response(data, config)

        # Output discovery summary in debug mode
        by_type: dict[str, int] = {}
        for instance in instances:
            iface_type = instance.properties.get("interface_type", "unknown")
            by_type[iface_type] = by_type.get(iface_type, 0) + 1
        self._debug_helper.discovery_summary(instances, by_type)

        return instances

    def collect_metrics(
        self,
        data: etree._Element,
        config: dict[str, Any]
    ) -> list[MetricValue]:
        """
        Collect metrics from NETCONF data for BATCHSCRIPT collection.

        Args:
            data: XML data element from NETCONF response
            config: Configuration dict

        Returns:
            List of metric values
        """
        _, metrics = self.parse_response(data, config)

        # Output collection summary in debug mode
        by_instance: dict[str, int] = {}
        for metric in metrics:
            if metric.instance_id:
                by_instance[metric.instance_id] = by_instance.get(metric.instance_id, 0) + 1
        self._debug_helper.collection_summary(metrics, by_instance)

        return metrics

    def iter_instances(
        self,
        data: etree._Element,
        config: dict[str, Any]
    ) -> Generator[tuple[DiscoveredInstance, list[MetricValue]], None, None]:
        """
        Iterate over instances with their associated metrics.

        Useful for streaming output without loading all data into memory.

        Args:
            data: XML data element
            config: Configuration dict

        Yields:
            Tuples of (instance, metrics_for_instance)
        """
        instances, all_metrics = self.parse_response(data, config)

        # Group metrics by instance
        metrics_by_instance: dict[str, list[MetricValue]] = {}
        for metric in all_metrics:
            if metric.instance_id:
                if metric.instance_id not in metrics_by_instance:
                    metrics_by_instance[metric.instance_id] = []
                metrics_by_instance[metric.instance_id].append(metric)

        # Yield each instance with its metrics
        for instance in instances:
            instance_metrics = metrics_by_instance.get(instance.instance_id, [])
            yield instance, instance_metrics
