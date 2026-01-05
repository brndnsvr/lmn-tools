"""
Utility functions for the LogicMonitor NETCONF Optical collector.

Includes string maps, sanitization, timestamp parsing, and other helpers.
"""

import re
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


# Common string maps for converting status values to numeric
DEFAULT_STRING_MAPS: Dict[str, Dict[str, int]] = {
    "status": {
        "down": 0,
        "up": 1,
    },
    "enabled": {
        "disabled": 0,
        "enabled": 1,
    },
    "active": {
        "Inactive": 0,
        "inactive": 0,
        "Active": 1,
        "active": 1,
    },
    "bool": {
        "false": 0,
        "true": 1,
        "False": 0,
        "True": 1,
        "no": 0,
        "yes": 1,
        "No": 0,
        "Yes": 1,
    },
    "oper_state": {
        "down": 0,
        "up": 1,
        "unknown": -1,
        "testing": 2,
        "dormant": 3,
        "notPresent": 4,
        "lowerLayerDown": 5,
    },
    "admin_state": {
        "down": 0,
        "up": 1,
        "testing": 2,
    },
    "alarm_severity": {
        "cleared": 0,
        "indeterminate": 1,
        "warning": 2,
        "minor": 3,
        "major": 4,
        "critical": 5,
    },
}


def sanitize_instance_id(value: str) -> str:
    """
    Sanitize an instance ID for LogicMonitor.

    LogicMonitor instance IDs cannot contain: ':', '#', '\\', or spaces.
    These characters are replaced with underscores or dashes.

    Args:
        value: The raw instance ID value

    Returns:
        Sanitized instance ID safe for LogicMonitor
    """
    if not value:
        return ""

    # Replace problematic characters with underscores
    # : # \ and spaces are not allowed
    sanitized = re.sub(r'[:#\\\s]', '_', str(value))

    # Collapse multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)

    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')

    return sanitized


def sanitize_metric_name(name: str) -> str:
    """
    Sanitize an element name for use as a metric/label name.

    - Removes XML namespace prefixes ({http://...} and ns:)
    - Converts to lowercase
    - Replaces non-alphanumeric characters with underscores
    - Collapses repeated underscores

    Args:
        name: The raw element or attribute name

    Returns:
        Sanitized name suitable for metric names
    """
    if not name:
        return ""

    # Remove full namespace URIs: {http://example.com}tag -> tag
    name = re.sub(r'\{[^}]+\}', '', name)

    # Remove namespace prefixes: ns:tag -> tag
    if ':' in name:
        name = name.split(':')[-1]

    # Convert to lowercase
    name = name.lower()

    # Replace non-alphanumeric with underscore
    name = re.sub(r'[^a-z0-9]', '_', name)

    # Collapse repeated underscores
    name = re.sub(r'_+', '_', name)

    # Remove leading/trailing underscores
    name = name.strip('_')

    return name


def apply_string_map(
    value: str,
    string_map: Optional[Dict[str, int]] = None,
    default: int = 0
) -> int:
    """
    Apply a string map to convert a string value to numeric.

    Args:
        value: The string value to convert
        string_map: Mapping of string -> int (e.g., {"up": 1, "down": 0})
        default: Default value if string not in map

    Returns:
        Numeric value from map, or default if not found
    """
    if string_map is None:
        return default

    return string_map.get(value, default)


def parse_string_map_definition(definition: str) -> Dict[str, int]:
    """
    Parse a string map definition from config format.

    Format: "key1:value1,key2:value2,..."
    Example: "down:0,up:1"

    Args:
        definition: The string map definition

    Returns:
        Dictionary mapping strings to integers
    """
    result = {}
    if not definition:
        return result

    for item in definition.split(','):
        item = item.strip()
        if ':' in item:
            key, value = item.split(':', 1)
            try:
                result[key.strip()] = int(value.strip())
            except ValueError:
                # Try float, then convert to int
                try:
                    result[key.strip()] = int(float(value.strip()))
                except ValueError:
                    logger.warning(f"Invalid string_map value: {item}")

    return result


def parse_timestamp(value: str) -> Optional[float]:
    """
    Parse various timestamp formats into Unix epoch seconds.

    Supports:
    - ISO 8601 formats (2024-11-26T14:30:00Z)
    - ISO with timezone (2024-11-26T14:30:00+00:00)
    - Common date formats

    Args:
        value: The timestamp string to parse

    Returns:
        Unix epoch timestamp as float, or None if parsing fails
    """
    if not value:
        return None

    # Silently skip null/unset timestamps (e.g., "0000-01-01T00:00:00.000Z")
    # These represent uninitialized values, not parsing errors
    if value.startswith("0000-01-01"):
        return None

    # Try dateutil parser for flexibility
    try:
        from dateutil.parser import parse as dateutil_parse
        dt = dateutil_parse(value)
        return dt.timestamp()
    except ImportError:
        pass
    except (ValueError, TypeError):
        pass

    # Fallback: try common ISO formats manually
    iso_formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in iso_formats:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.timestamp()
        except ValueError:
            continue

    logger.warning(f"Failed to parse timestamp: {value}")
    return None


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """
    Safely convert a value to float.

    Args:
        value: The value to convert
        default: Default value if conversion fails

    Returns:
        Float value, or default if conversion fails
    """
    if value is None:
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """
    Safely convert a value to int.

    Args:
        value: The value to convert
        default: Default value if conversion fails

    Returns:
        Integer value, or default if conversion fails
    """
    if value is None:
        return default

    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def extract_element_text(element, default: str = "") -> str:
    """
    Safely extract text content from an XML element.

    Args:
        element: lxml Element or None
        default: Default value if element or text is None

    Returns:
        Text content or default
    """
    if element is None:
        return default

    text = element.text
    if text is None:
        return default

    return text.strip()


def build_xpath_with_namespaces(xpath: str, namespaces: Dict[str, str]) -> str:
    """
    Build an XPath expression with namespace prefixes.

    For use with lxml's find() methods which require prefixes.

    Args:
        xpath: The XPath expression (may use local names without prefixes)
        namespaces: Dict of prefix -> namespace URI

    Returns:
        XPath with namespaces properly handled
    """
    # This is a simplified version - full namespace handling is complex
    return xpath


def get_local_name(tag: str) -> str:
    """
    Extract the local name from an XML tag, removing namespace.

    Args:
        tag: The full tag name (may include {namespace}localname)

    Returns:
        Just the local name portion
    """
    if tag.startswith('{'):
        return tag.split('}', 1)[-1]
    if ':' in tag:
        return tag.split(':', 1)[-1]
    return tag


def format_dbm(value: Optional[float]) -> str:
    """
    Format a dBm power value for display.

    Args:
        value: Power value in dBm

    Returns:
        Formatted string like "-12.5 dBm"
    """
    if value is None:
        return "N/A"
    return f"{value:.1f} dBm"


def format_db(value: Optional[float]) -> str:
    """
    Format a dB value for display.

    Args:
        value: Value in dB

    Returns:
        Formatted string like "18.3 dB"
    """
    if value is None:
        return "N/A"
    return f"{value:.1f} dB"
