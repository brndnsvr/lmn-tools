"""
Device data collectors for lmn-tools.

Provides protocol-specific collectors for gathering data from
network devices via NETCONF, SNMP, and other protocols.
"""

from __future__ import annotations

from lmn_tools.collectors.base import BaseCollector

__all__ = ["BaseCollector"]
