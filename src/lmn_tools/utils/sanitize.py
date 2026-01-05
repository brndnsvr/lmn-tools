"""
String sanitization utilities for LogicMonitor output.

Provides functions for cleaning and formatting strings for use
in LogicMonitor instance IDs, metric names, dashboard names, etc.
"""

from __future__ import annotations

import re

from lmn_tools.constants import Patterns


def sanitize_instance_id(value: str) -> str:
    """
    Remove invalid characters from LogicMonitor instance ID.

    LogicMonitor instance IDs cannot contain:
    - Colons (:)
    - Hashes (#)
    - Backslashes (\\)
    - Whitespace

    Args:
        value: Raw instance ID value

    Returns:
        Sanitized instance ID with invalid chars replaced by underscore

    Example:
        >>> sanitize_instance_id("ae100:3")
        'ae100_3'
        >>> sanitize_instance_id("port 1/2/3")
        'port_1_2_3'
    """
    if not value:
        return ""

    # Replace invalid characters with underscore
    sanitized = Patterns.INVALID_INSTANCE_ID_CHARS.sub("_", str(value))

    # Collapse multiple consecutive underscores
    sanitized = re.sub(r"_+", "_", sanitized)

    # Strip leading/trailing underscores
    return sanitized.strip("_")


def sanitize_metric_name(name: str) -> str:
    """
    Sanitize string for use as LogicMonitor metric/datapoint name.

    Removes XML namespaces and converts to lowercase with underscores.

    Args:
        name: Raw metric name (may contain XML namespaces)

    Returns:
        Sanitized metric name (lowercase, alphanumeric + underscore)

    Example:
        >>> sanitize_metric_name("{http://example.com}rxPower")
        'rxpower'
        >>> sanitize_metric_name("ne:optical-power")
        'optical_power'
    """
    if not name:
        return ""

    # Remove {namespace} URIs
    name = Patterns.XML_NAMESPACE_URI.sub("", name)

    # Remove prefix: prefixes
    if ":" in name:
        name = name.split(":")[-1]

    # Lowercase
    name = name.lower()

    # Replace non-alphanumeric with underscore
    name = re.sub(r"[^a-z0-9]", "_", name)

    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)

    # Strip leading/trailing underscores
    return name.strip("_")


def sanitize_dashboard_name(name: str) -> str:
    """
    Sanitize string for use as LogicMonitor dashboard name.

    Removes characters that cause issues in dashboard names:
    - Commas (cause CSV parsing issues)
    - Backslashes (cause escaping issues)

    Args:
        name: Raw dashboard name

    Returns:
        Sanitized dashboard name

    Example:
        >>> sanitize_dashboard_name("Site A, Site B Dashboard")
        'Site A - Site B Dashboard'
    """
    if not name:
        return ""

    # Replace commas with " -"
    name = name.replace(",", " -")

    # Replace backslashes with hyphen
    name = name.replace("\\", "-")

    # Collapse multiple spaces
    name = re.sub(r"\s+", " ", name)

    return name.strip()


def extract_base_interface(interface_name: str) -> str:
    """
    Remove unit number from interface name.

    Junos-style interface names have a unit suffix (e.g., ae100.3).
    This function returns the base interface name without the unit.

    Args:
        interface_name: Interface name (e.g., "ae100.3", "ge-0/0/0.0")

    Returns:
        Base interface name without unit (e.g., "ae100", "ge-0/0/0")

    Example:
        >>> extract_base_interface("ae100.3")
        'ae100'
        >>> extract_base_interface("ge-0/0/0.0")
        'ge-0/0/0'
        >>> extract_base_interface("eth0")
        'eth0'
    """
    return Patterns.INTERFACE_UNIT.sub("", interface_name)


def normalize_hostname(hostname: str) -> str:
    """
    Normalize hostname for consistent matching.

    Args:
        hostname: Raw hostname

    Returns:
        Lowercase, stripped hostname

    Example:
        >>> normalize_hostname("  MyRouter.example.com  ")
        'myrouter.example.com'
    """
    return hostname.strip().lower()


def normalize_interface_name(name: str) -> str:
    """
    Normalize interface name for consistent matching.

    Handles variations in interface naming conventions:
    - Strips whitespace
    - Normalizes case

    Args:
        name: Raw interface name

    Returns:
        Normalized interface name

    Example:
        >>> normalize_interface_name(" GE-0/0/0 ")
        'ge-0/0/0'
    """
    return name.strip().lower()


def truncate_string(value: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to maximum length with suffix.

    Args:
        value: String to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to append if truncated

    Returns:
        Truncated string

    Example:
        >>> truncate_string("Very long string here", 15)
        'Very long st...'
    """
    if len(value) <= max_length:
        return value

    return value[: max_length - len(suffix)] + suffix


def strip_xml_namespaces(text: str) -> str:
    """
    Remove XML namespace prefixes and URIs from text.

    Args:
        text: Text containing XML namespaces

    Returns:
        Text with namespaces removed

    Example:
        >>> strip_xml_namespaces("{http://example.com}element")
        'element'
        >>> strip_xml_namespaces("ns:element")
        'element'
    """
    # Remove {namespace} URIs
    text = Patterns.XML_NAMESPACE_URI.sub("", text)

    # Remove prefix: prefixes
    text = Patterns.XML_NAMESPACE_PREFIX.sub("", text)

    return text


def make_safe_filename(name: str) -> str:
    """
    Convert string to safe filename.

    Removes or replaces characters that are invalid in filenames.

    Args:
        name: Raw name

    Returns:
        Safe filename

    Example:
        >>> make_safe_filename("Report 2024/01 <draft>")
        'Report_2024_01_draft'
    """
    if not name:
        return "unnamed"

    # Replace path separators and other invalid chars
    name = re.sub(r'[<>:"/\\|?*]', "_", name)

    # Replace spaces
    name = name.replace(" ", "_")

    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)

    return name.strip("_") or "unnamed"
