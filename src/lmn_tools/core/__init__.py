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
    # Settings
    "get_settings",
    "LMToolsSettings",
    "LMCredentials",
    "NetconfCredentials",
    "SNMPv2cCredentials",
    "SNMPv3Credentials",
    # Exceptions
    "LMToolsError",
    "AuthenticationError",
    "APIError",
    "NetconfError",
    "SNMPError",
    "ConfigurationError",
]
