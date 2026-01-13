"""
Value conversion utilities for LogicMonitor metrics.

Provides functions for converting between string values and
numeric values using string maps, parsing timestamps, and
safe type conversions.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from lmn_tools.constants import StringMaps
from lmn_tools.core.exceptions import StringMapError

logger = logging.getLogger(__name__)


def safe_float(
    value: Any,
    default: float | None = None,
) -> float | None:
    """
    Safely convert value to float.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default

    Example:
        >>> safe_float("3.14")
        3.14
        >>> safe_float("invalid", default=0.0)
        0.0
        >>> safe_float(None)
        None
    """
    if value is None:
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(
    value: Any,
    default: int | None = None,
) -> int | None:
    """
    Safely convert value to integer.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Integer value or default

    Example:
        >>> safe_int("42")
        42
        >>> safe_int("3.14")
        3
        >>> safe_int("invalid", default=0)
        0
    """
    if value is None:
        return default

    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_bool(
    value: Any,
    default: bool = False,
) -> bool:
    """
    Safely convert value to boolean.

    Recognizes common boolean string representations:
    - True: "true", "yes", "1", "on", "enabled"
    - False: "false", "no", "0", "off", "disabled"

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Boolean value or default

    Example:
        >>> safe_bool("yes")
        True
        >>> safe_bool("0")
        False
        >>> safe_bool("maybe", default=False)
        False
    """
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        lower = value.lower().strip()
        if lower in ("true", "yes", "1", "on", "enabled"):
            return True
        if lower in ("false", "no", "0", "off", "disabled"):
            return False

    return default


def apply_string_map(
    value: str,
    string_map: dict[str, int] | None = None,
    string_map_name: str | None = None,
    default: int = 0,
    strict: bool = False,
) -> int:
    """
    Convert string value to integer using a string map.

    Can use either a provided dictionary or a named predefined map
    from StringMaps.

    Args:
        value: String value to convert
        string_map: Custom string map dictionary
        string_map_name: Name of predefined StringMaps constant
        default: Default value if not found in map
        strict: If True, raise StringMapError when value not found

    Returns:
        Integer value from map or default

    Raises:
        StringMapError: If strict=True and value not in map

    Example:
        >>> apply_string_map("up", string_map_name="status")
        1
        >>> apply_string_map("down", string_map_name="status")
        0
        >>> apply_string_map("unknown", string_map={"up": 1, "down": 0}, default=-1)
        -1
    """
    # Get string map from name if not provided directly
    if string_map is None and string_map_name:
        try:
            string_map = StringMaps.get_map(string_map_name)
        except KeyError as e:
            logger.warning(f"Unknown string map: {string_map_name}")
            if strict:
                raise StringMapError(value, string_map_name) from e
            return default

    if string_map is None:
        return default

    # Look up value in map
    if value in string_map:
        return string_map[value]

    # Try case-insensitive match
    value_lower = value.lower()
    for key, int_value in string_map.items():
        if key.lower() == value_lower:
            return int_value

    if strict:
        raise StringMapError(value, string_map_name or "custom")

    return default


def parse_timestamp(value: str) -> float | None:
    """
    Parse timestamp string to Unix epoch seconds.

    Handles various ISO 8601 formats and common timestamp patterns.

    Args:
        value: Timestamp string

    Returns:
        Unix timestamp (seconds) or None if invalid

    Example:
        >>> parse_timestamp("2024-01-15T10:30:00Z")
        1705315800.0
        >>> parse_timestamp("2024-01-15")
        1705276800.0
    """
    if not value:
        return None

    # Skip null/zero timestamps
    if value.startswith("0000-01-01") or value == "null":
        return None

    # Try python-dateutil first (most flexible)
    try:
        from dateutil.parser import parse as dateutil_parse  # type: ignore[import-untyped]

        result: float = dateutil_parse(value).timestamp()
        return result
    except ImportError:
        pass
    except (ValueError, TypeError):
        pass

    # Fall back to manual parsing of common formats
    iso_formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
    ]

    for fmt in iso_formats:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.timestamp()
        except ValueError:
            continue

    return None


def format_timestamp(
    timestamp: float,
    format_str: str = "%Y-%m-%dT%H:%M:%SZ",
) -> str:
    """
    Format Unix timestamp as string.

    Args:
        timestamp: Unix timestamp (seconds)
        format_str: strftime format string

    Returns:
        Formatted timestamp string

    Example:
        >>> format_timestamp(1705315800.0)
        '2024-01-15T10:30:00Z'
    """
    dt = datetime.utcfromtimestamp(timestamp)
    return dt.strftime(format_str)


def bytes_to_human(size_bytes: int | float) -> str:
    """
    Convert bytes to human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string

    Example:
        >>> bytes_to_human(1024)
        '1.0 KB'
        >>> bytes_to_human(1048576)
        '1.0 MB'
    """
    if size_bytes < 0:
        return f"-{bytes_to_human(-size_bytes)}"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(size_bytes)

    for unit in units[:-1]:
        if abs(size) < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0

    return f"{size:.1f} {units[-1]}"


def bps_to_human(bps: int | float) -> str:
    """
    Convert bits per second to human-readable string.

    Args:
        bps: Bits per second

    Returns:
        Human-readable rate string

    Example:
        >>> bps_to_human(1000000)
        '1.0 Mbps'
        >>> bps_to_human(10000000000)
        '10.0 Gbps'
    """
    if bps < 0:
        return f"-{bps_to_human(-bps)}"

    units = ["bps", "Kbps", "Mbps", "Gbps", "Tbps"]
    rate = float(bps)

    for unit in units[:-1]:
        if abs(rate) < 1000.0:
            return f"{rate:.1f} {unit}"
        rate /= 1000.0

    return f"{rate:.1f} {units[-1]}"


def dbm_to_mw(dbm: float) -> float:
    """
    Convert dBm to milliwatts.

    Args:
        dbm: Power in dBm

    Returns:
        Power in milliwatts

    Example:
        >>> dbm_to_mw(0)
        1.0
        >>> dbm_to_mw(10)
        10.0
    """
    import math

    return math.pow(10, dbm / 10)


def mw_to_dbm(mw: float) -> float:
    """
    Convert milliwatts to dBm.

    Args:
        mw: Power in milliwatts

    Returns:
        Power in dBm

    Example:
        >>> mw_to_dbm(1.0)
        0.0
        >>> mw_to_dbm(10.0)
        10.0
    """
    import math

    if mw <= 0:
        return float("-inf")
    return 10 * math.log10(mw)


def percent_to_ratio(percent: float) -> float:
    """
    Convert percentage to ratio (0-1).

    Args:
        percent: Percentage value (0-100)

    Returns:
        Ratio value (0-1)

    Example:
        >>> percent_to_ratio(50)
        0.5
    """
    return percent / 100.0


def ratio_to_percent(ratio: float) -> float:
    """
    Convert ratio (0-1) to percentage.

    Args:
        ratio: Ratio value (0-1)

    Returns:
        Percentage value (0-100)

    Example:
        >>> ratio_to_percent(0.5)
        50.0
    """
    return ratio * 100.0
