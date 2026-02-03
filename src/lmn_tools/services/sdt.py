"""
Service for LogicMonitor SDT (Scheduled Downtime).

Provides operations for managing maintenance windows.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class SDTType(str, Enum):
    """SDT (Scheduled Downtime) types."""

    DEVICE = "DeviceSDT"
    DEVICE_GROUP = "DeviceGroupSDT"
    DATASOURCE = "DeviceDataSourceSDT"
    INSTANCE = "DeviceDataSourceInstanceSDT"
    DATASOURCE_GROUP = "DeviceDataSourceGroupSDT"
    COLLECTOR = "CollectorSDT"
    WEBSITE = "WebsiteSDT"


class SDTService(BaseService):
    """
    Service for managing LogicMonitor SDT (Scheduled Downtime).

    Usage:
        svc = SDTService(client)
        sdts = svc.list_active()
        svc.create_device_sdt(device_id=123, duration_mins=60, comment="Maintenance")
    """

    @property
    def base_path(self) -> str:
        return "/sdt/sdts"

    def list_active(self) -> list[dict[str, Any]]:
        """List currently active SDTs."""
        now = int(time.time() * 1000)
        return self.list(filter=f"isEffective:true,startDateTime<{now},endDateTime>{now}")

    def list_upcoming(self, days: int = 7) -> list[dict[str, Any]]:
        """
        List upcoming SDTs within a time window.

        Args:
            days: Number of days ahead to look

        Returns:
            List of upcoming SDTs
        """
        now = int(time.time() * 1000)
        future = now + (days * 24 * 60 * 60 * 1000)
        return self.list(filter=f"startDateTime>{now},startDateTime<{future}")

    def list_for_device(self, device_id: int) -> list[dict[str, Any]]:
        """List SDTs for a specific device."""
        return self.list(filter=f"deviceId:{device_id}")

    def create_device_sdt(
        self,
        device_id: int,
        duration_mins: int,
        comment: str = "",
        start_time: int | None = None,
    ) -> dict[str, Any]:
        """
        Create an SDT for a device.

        Args:
            device_id: Device ID
            duration_mins: Duration in minutes
            comment: SDT comment
            start_time: Start timestamp (ms), defaults to now

        Returns:
            Created SDT
        """
        if start_time is None:
            start_time = int(time.time() * 1000)

        end_time = start_time + (duration_mins * 60 * 1000)

        data = {
            "type": SDTType.DEVICE.value,
            "deviceId": device_id,
            "startDateTime": start_time,
            "endDateTime": end_time,
            "comment": comment,
        }
        return self.create(data)

    def create_group_sdt(
        self,
        group_id: int,
        duration_mins: int,
        comment: str = "",
        start_time: int | None = None,
    ) -> dict[str, Any]:
        """
        Create an SDT for a device group.

        Args:
            group_id: Device group ID
            duration_mins: Duration in minutes
            comment: SDT comment
            start_time: Start timestamp (ms), defaults to now

        Returns:
            Created SDT
        """
        if start_time is None:
            start_time = int(time.time() * 1000)

        end_time = start_time + (duration_mins * 60 * 1000)

        data = {
            "type": SDTType.DEVICE_GROUP.value,
            "deviceGroupId": group_id,
            "startDateTime": start_time,
            "endDateTime": end_time,
            "comment": comment,
        }
        return self.create(data)

    def create_datasource_sdt(
        self,
        device_id: int,
        datasource_id: int,
        duration_mins: int,
        comment: str = "",
        start_time: int | None = None,
    ) -> dict[str, Any]:
        """
        Create an SDT for a device datasource.

        Args:
            device_id: Device ID
            datasource_id: DataSource ID
            duration_mins: Duration in minutes
            comment: SDT comment
            start_time: Start timestamp (ms), defaults to now

        Returns:
            Created SDT
        """
        if start_time is None:
            start_time = int(time.time() * 1000)

        end_time = start_time + (duration_mins * 60 * 1000)

        data = {
            "type": SDTType.DATASOURCE.value,
            "deviceId": device_id,
            "dataSourceId": datasource_id,
            "startDateTime": start_time,
            "endDateTime": end_time,
            "comment": comment,
        }
        return self.create(data)


def sdt_service(client: LMClient) -> SDTService:
    """Create an SDTService instance."""
    return SDTService(client)
