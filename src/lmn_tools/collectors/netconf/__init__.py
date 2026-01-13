"""
NETCONF collector for optical transport devices.

Provides connectivity and data collection for devices
such as Coriant/Infinera and Ciena WaveServer.
"""

from __future__ import annotations

from lmn_tools.collectors.netconf.client import DEVICE_CONFIGS, NetconfCollector

__all__ = ["DEVICE_CONFIGS", "NetconfCollector"]
