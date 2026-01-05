"""
SNMP collector for network devices.

Provides SNMPv2c and SNMPv3 connectivity and data collection.
"""

from __future__ import annotations

from lmn_tools.collectors.snmp.client import SNMPCollector, SNMPCredentials

__all__ = ["SNMPCollector", "SNMPCredentials"]
