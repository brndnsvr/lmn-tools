"""
Core module for lmn-tools.

Contains configuration management, exceptions, and base functionality.
"""

from __future__ import annotations

from lmn_tools.core.config import (
    LMCredentials,
    LMToolsSettings,
    NetconfCredentials,
    SNMPv2cCredentials,
    SNMPv3Credentials,
    get_settings,
)
from lmn_tools.core.exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    LMToolsError,
    NetconfError,
    SNMPError,
)

__all__ = [
    "APIError",
    "AuthenticationError",
    "ConfigurationError",
    "LMCredentials",
    # Exceptions
    "LMToolsError",
    "LMToolsSettings",
    "NetconfCredentials",
    "NetconfError",
    "SNMPError",
    "SNMPv2cCredentials",
    "SNMPv3Credentials",
    # Settings
    "get_settings",
]
