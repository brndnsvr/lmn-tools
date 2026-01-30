"""
Service for LogicMonitor Topology Maps (Resource Maps).

Provides operations for managing network topology visualizations.
"""

from __future__ import annotations

from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class TopologyService(BaseService):
    """
    Service for managing LogicMonitor Topology Maps.

    Topology maps visualize network relationships between devices
    and resources.

    Usage:
        svc = TopologyService(client)
        maps = svc.list()
        map_data = svc.get_map_data(map_id)
    """

    @property
    def base_path(self) -> str:
        return "/topology/topologies"

    def search(self, query: str, max_items: int = 50) -> list[dict[str, Any]]:
        """
        Search topology maps by name.

        Args:
            query: Search term
            max_items: Maximum items to return

        Returns:
            List of matching topology maps
        """
        return self.list(filter=f'name~"{query}"', max_items=max_items)

    def get_map_data(self, map_id: int) -> dict[str, Any]:
        """
        Get the full topology map data including nodes and edges.

        Args:
            map_id: Topology map ID

        Returns:
            Map data with vertices and edges
        """
        return self.client.get(f"{self.base_path}/{map_id}/data")

    def export_map(self, map_id: int) -> dict[str, Any]:
        """
        Export a topology map as JSON (includes configuration and data).

        Args:
            map_id: Topology map ID

        Returns:
            Complete map export
        """
        config = self.get(map_id)
        config_data = config.get("data", config) if "data" in config else config
        map_data = self.get_map_data(map_id)
        map_data_inner = map_data.get("data", map_data) if "data" in map_data else map_data

        return {
            "config": config_data,
            "data": map_data_inner,
        }

    def create_from_devices(
        self,
        name: str,
        device_ids: list[int],
        description: str = "",
    ) -> dict[str, Any]:
        """
        Create a topology map from a list of devices.

        Args:
            name: Map name
            device_ids: List of device IDs to include
            description: Optional description

        Returns:
            Created topology map
        """
        data: dict[str, Any] = {
            "name": name,
            "description": description,
            "type": "manual",
            "vertices": [{"type": "device", "id": did} for did in device_ids],
        }
        return self.create(data)

    def add_device(self, map_id: int, device_id: int) -> dict[str, Any]:
        """
        Add a device to an existing topology map.

        Args:
            map_id: Topology map ID
            device_id: Device ID to add

        Returns:
            Updated map
        """
        current = self.get(map_id)
        data = current.get("data", current) if "data" in current else current
        vertices = data.get("vertices", [])
        vertices.append({"type": "device", "id": device_id})
        return self.update(map_id, {"vertices": vertices})


def topology_service(client: LMClient) -> TopologyService:
    """Create a topology service."""
    return TopologyService(client)
