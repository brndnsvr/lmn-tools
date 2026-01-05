"""
Utility functions for lmn-tools.

Provides sanitization, conversion, and helper functions.
"""

from __future__ import annotations

from lmn_tools.utils.conversion import (
    apply_string_map,
    bps_to_human,
    bytes_to_human,
    dbm_to_mw,
    format_timestamp,
    mw_to_dbm,
    parse_timestamp,
    percent_to_ratio,
    ratio_to_percent,
    safe_bool,
    safe_float,
    safe_int,
)
from lmn_tools.utils.sanitize import (
    extract_base_interface,
    make_safe_filename,
    normalize_hostname,
    normalize_interface_name,
    sanitize_dashboard_name,
    sanitize_instance_id,
    sanitize_metric_name,
    strip_xml_namespaces,
    truncate_string,
)

__all__ = [
    # Sanitization
    "sanitize_instance_id",
    "sanitize_metric_name",
    "sanitize_dashboard_name",
    "extract_base_interface",
    "normalize_hostname",
    "normalize_interface_name",
    "truncate_string",
    "strip_xml_namespaces",
    "make_safe_filename",
    # Conversion
    "safe_float",
    "safe_int",
    "safe_bool",
    "apply_string_map",
    "parse_timestamp",
    "format_timestamp",
    "bytes_to_human",
    "bps_to_human",
    "dbm_to_mw",
    "mw_to_dbm",
    "percent_to_ratio",
    "ratio_to_percent",
]
