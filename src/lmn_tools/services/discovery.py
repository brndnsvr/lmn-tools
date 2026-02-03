"""
Service for LogicMonitor Netscans (Device Discovery).

Provides operations for managing and executing network discovery scans.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class NetscanMethod(str, Enum):
    """Netscan discovery methods."""

    ICMP = "nmap"
    SCRIPT = "script"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    ENHANCED_SCRIPT = "enhancedScript"


class NetscanService(BaseService):
    """
    Service for managing LogicMonitor Netscans.

    Netscans are used to discover devices on the network and add them
    to LogicMonitor for monitoring.

    Usage:
        svc = NetscanService(client)
        scans = svc.list()
        svc.run(netscan_id)  # Execute a scan
    """

    @property
    def base_path(self) -> str:
        return "/setting/netscans"

    def list_by_collector(
        self,
        collector_id: int,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List Netscans assigned to a specific collector.

        Args:
            collector_id: Collector ID

        Returns:
            List of Netscans
        """
        return self.list(filter=f"collector.id:{collector_id}", max_items=max_items)

    def list_by_group(
        self,
        group_id: int,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List Netscans that add devices to a specific group.

        Args:
            group_id: Device group ID

        Returns:
            List of Netscans
        """
        return self.list(filter=f"group.id:{group_id}", max_items=max_items)

    def run(self, netscan_id: int) -> dict[str, Any]:
        """
        Execute a Netscan immediately.

        Args:
            netscan_id: Netscan ID to execute

        Returns:
            Execution result
        """
        return self.client.post(
            f"{self.base_path}/{netscan_id}/executenow",
            json_data={},
        )

    def get_execution_status(self, netscan_id: int) -> dict[str, Any]:
        """
        Get the current execution status of a Netscan.

        Args:
            netscan_id: Netscan ID

        Returns:
            Status information
        """
        netscan = self.get(netscan_id)
        data = netscan.get("data", netscan) if "data" in netscan else netscan
        return {
            "id": netscan_id,
            "name": data.get("name"),
            "nextStart": data.get("nextStart"),
            "lastExecutedOn": data.get("lastExecutedOn"),
            "lastExecutedOnLocal": data.get("lastExecutedOnLocal"),
        }

    def create_icmp_scan(
        self,
        name: str,
        collector_id: int,
        group_id: int,
        subnet: str,
        description: str = "",
    ) -> dict[str, Any]:
        """
        Create an ICMP (ping) based Netscan.

        Args:
            name: Scan name
            collector_id: Collector ID to use
            group_id: Device group to add discovered devices to
            subnet: IP range to scan (CIDR notation)
            description: Optional description

        Returns:
            Created Netscan
        """
        data = {
            "name": name,
            "description": description,
            "method": NetscanMethod.ICMP.value,
            "collector": collector_id,
            "group": {"id": group_id},
            "subnet": subnet,
        }
        return self.create(data)

    def enable(self, netscan_id: int) -> dict[str, Any]:
        """Enable a Netscan."""
        return self.update(netscan_id, {"disabled": False})

    def disable(self, netscan_id: int) -> dict[str, Any]:
        """Disable a Netscan."""
        return self.update(netscan_id, {"disabled": True})


def netscan_service(client: LMClient) -> NetscanService:
    """Create a Netscan service."""
    return NetscanService(client)
