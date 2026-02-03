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
    sanitize_instance_id,
    sanitize_metric_name,
    strip_xml_namespaces,
    truncate_string,
)

__all__ = [
    "apply_string_map",
    "bps_to_human",
    "bytes_to_human",
    "dbm_to_mw",
    "extract_base_interface",
    "format_timestamp",
    "make_safe_filename",
    "mw_to_dbm",
    "normalize_hostname",
    "normalize_interface_name",
    "parse_timestamp",
    "percent_to_ratio",
    "ratio_to_percent",
    "safe_bool",
    # Conversion
    "safe_float",
    "safe_int",
    # Sanitization
    "sanitize_instance_id",
    "sanitize_metric_name",
    "strip_xml_namespaces",
    "truncate_string",
]
