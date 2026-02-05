"""
Service for LogicMonitor Collectors and Collector Groups.

Provides operations for managing collectors and collector groups.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.constants import LMEndpoints
from lmn_tools.services.base import BaseService


class CollectorStatus(Enum):
    """Collector status values."""

    DOWN = 0
    OK = 1
    WARNING = 2


class CollectorService(BaseService):
    """
    Service for managing LogicMonitor collectors.

    Usage:
        svc = CollectorService(client)
        collectors = svc.list()
        down_collectors = svc.list_down()
        status = svc.get_status(collector_id)
    """

    @property
    def base_path(self) -> str:
        return LMEndpoints.COLLECTORS

    def list_by_group(self, group_id: int) -> list[dict[str, Any]]:
        """
        List collectors in a specific group.

        Args:
            group_id: Collector group ID

        Returns:
            List of collectors in the group
        """
        return self.list(filter=f"collectorGroupId:{group_id}")

    def list_by_status(self, status: CollectorStatus) -> list[dict[str, Any]]:
        """
        List collectors by status.

        Args:
            status: Collector status enum value

        Returns:
            List of collectors with the specified status
        """
        return self.list(filter=f"status:{status.value}")

    def list_down(self) -> list[dict[str, Any]]:
        """
        List collectors with down status.

        Returns:
            List of down collectors
        """
        return self.list_by_status(CollectorStatus.DOWN)

    def get_status(self, collector_id: int) -> dict[str, Any]:
        """
        Get collector health metrics.

        Args:
            collector_id: Collector ID

        Returns:
            Status info with uptime, device count, build version
        """
        collector = self.get(collector_id)
        return {
            "status": collector.get("status"),
            "upTime": collector.get("upTime"),
            "numberOfHosts": collector.get("numberOfHosts"),
            "build": collector.get("build"),
        }

    def get_installer_url(
        self,
        platform: str,
        version: str | None = None,
    ) -> dict[str, Any]:
        """
        Get collector installer download URL.

        Args:
            platform: Platform type (linux64, win64, etc.)
            version: Specific version (optional, defaults to latest)

        Returns:
            Download URL and metadata (URL expires in 2 hours)
        """
        path = f"/setting/collector/installers/{platform}"
        if version:
            path = f"{path}/{version}"
        return self.client.get(path)

    def escalate_to_version(
        self,
        collector_id: int,
        version: str,
    ) -> dict[str, Any]:
        """
        Upgrade collector to specific version.

        Args:
            collector_id: Collector ID
            version: Target version string

        Returns:
            Updated collector info
        """
        data = {
            "escalatingChainId": 0,
            "onetimeUpgradeInfo": {"version": version},
        }
        return self.update(collector_id, data)


class CollectorGroupService(BaseService):
    """
    Service for managing collector groups.

    Usage:
        svc = CollectorGroupService(client)
        groups = svc.list()
        collectors = svc.get_collectors(group_id)
    """

    @property
    def base_path(self) -> str:
        return LMEndpoints.COLLECTOR_GROUPS

    def get_collectors(self, group_id: int) -> list[dict[str, Any]]:
        """
        Get collectors in a group.

        Args:
            group_id: Collector group ID

        Returns:
            List of collectors in the group
        """
        return self.client.get_all(f"{self.base_path}/{group_id}/collectors")


def collector_service(client: LMClient) -> CollectorService:
    """Create a service for collectors."""
    return CollectorService(client)


def collector_group_service(client: LMClient) -> CollectorGroupService:
    """Create a service for collector groups."""
    return CollectorGroupService(client)
