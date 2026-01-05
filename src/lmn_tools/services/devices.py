"""
Service for LogicMonitor Devices and Device Groups.

Provides operations for managing devices and their hierarchy.
"""

from __future__ import annotations

from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class DeviceService(BaseService):
    """
    Service for managing LogicMonitor devices.

    Usage:
        svc = DeviceService(client)
        devices = svc.list(filter="displayName~*prod*")
        device = svc.get(123)
    """

    @property
    def base_path(self) -> str:
        return "/device/devices"

    def find_by_hostname(self, hostname: str) -> dict[str, Any] | None:
        """
        Find a device by hostname (displayName).

        Args:
            hostname: Device hostname/displayName

        Returns:
            Device dictionary or None
        """
        return self.find_by_name(hostname, name_field="displayName", exact=True)

    def find_by_ip(self, ip: str) -> dict[str, Any] | None:
        """
        Find a device by IP address.

        Args:
            ip: Device IP address

        Returns:
            Device dictionary or None
        """
        results = self.list(filter=f'name:"{ip}"', max_items=1)
        return results[0] if results else None

    def get_properties(self, device_id: int) -> list[dict[str, Any]]:
        """
        Get device properties.

        Args:
            device_id: Device ID

        Returns:
            List of property dictionaries
        """
        response = self.client.get(f"{self.base_path}/{device_id}/properties")
        return response.get("items", response.get("data", {}).get("items", []))

    def set_property(self, device_id: int, name: str, value: str) -> dict[str, Any]:
        """
        Set a device property.

        Args:
            device_id: Device ID
            name: Property name
            value: Property value

        Returns:
            Created/updated property
        """
        return self.client.post(
            f"{self.base_path}/{device_id}/properties",
            json_data={"name": name, "value": value},
        )

    def get_datasources(
        self,
        device_id: int,
        datasource_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get DataSources applied to a device.

        Args:
            device_id: Device ID
            datasource_name: Optional datasource name filter

        Returns:
            List of device datasources
        """
        params: dict[str, Any] = {}
        if datasource_name:
            params["filter"] = f'dataSourceName:"{datasource_name}"'

        return self.client.get_all(f"{self.base_path}/{device_id}/devicedatasources", params)

    def get_instances(
        self,
        device_id: int,
        device_datasource_id: int,
        instance_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get instances for a device datasource.

        Args:
            device_id: Device ID
            device_datasource_id: Device datasource ID
            instance_name: Optional instance name filter

        Returns:
            List of instances
        """
        params: dict[str, Any] = {}
        if instance_name:
            params["filter"] = f'displayName:"{instance_name}"'

        path = f"{self.base_path}/{device_id}/devicedatasources/{device_datasource_id}/instances"
        return self.client.get_all(path, params)

    def list_by_group(self, group_id: int) -> list[dict[str, Any]]:
        """
        List devices in a group (direct members only).

        Args:
            group_id: Group ID

        Returns:
            List of devices
        """
        return self.list(filter=f"hostGroupIds:{group_id}")

    def list_by_collector(self, collector_id: int) -> list[dict[str, Any]]:
        """
        List devices assigned to a collector.

        Args:
            collector_id: Collector ID

        Returns:
            List of devices
        """
        return self.list(filter=f"currentCollectorId:{collector_id}")

    def list_dead(self) -> list[dict[str, Any]]:
        """
        List devices with dead status.

        Returns:
            List of dead devices
        """
        return self.list(filter="hostStatus:dead")

    def list_alive(self) -> list[dict[str, Any]]:
        """
        List devices with normal/alive status.

        Returns:
            List of alive devices
        """
        return self.list(filter="hostStatus:normal")


class DeviceGroupService(BaseService):
    """
    Service for managing LogicMonitor device groups.

    Usage:
        svc = DeviceGroupService(client)
        groups = svc.list()
        group = svc.get_by_path("/Devices/Production")
    """

    @property
    def base_path(self) -> str:
        return "/device/groups"

    def get_by_path(self, path: str) -> dict[str, Any] | None:
        """
        Get a group by full path.

        Args:
            path: Full path (e.g., '/Devices/Production')

        Returns:
            Group dictionary or None
        """
        return self.find_by_name(path, name_field="fullPath", exact=True)

    def get_devices(self, group_id: int) -> list[dict[str, Any]]:
        """
        Get devices in a group (direct members only).

        Args:
            group_id: Group ID

        Returns:
            List of devices
        """
        return self.client.get_all(f"{self.base_path}/{group_id}/devices")

    def get_properties(self, group_id: int) -> list[dict[str, Any]]:
        """
        Get group properties.

        Args:
            group_id: Group ID

        Returns:
            List of property dictionaries
        """
        response = self.client.get(f"{self.base_path}/{group_id}/properties")
        return response.get("items", response.get("data", {}).get("items", []))

    def get_children(self, parent_id: int = 1) -> list[dict[str, Any]]:
        """
        Get child groups of a parent.

        Args:
            parent_id: Parent group ID (default: 1 = root)

        Returns:
            List of child groups
        """
        return self.list(filter=f"parentId:{parent_id}")

    def get_tree(self, parent_id: int = 1, max_depth: int = 10) -> list[dict[str, Any]]:
        """
        Get group tree structure.

        Args:
            parent_id: Starting parent ID
            max_depth: Maximum depth to traverse

        Returns:
            List of groups with 'children' key
        """
        def _build_tree(pid: int, depth: int) -> list[dict[str, Any]]:
            if depth <= 0:
                return []
            children = self.get_children(pid)
            for child in children:
                child["children"] = _build_tree(child["id"], depth - 1)
            return children

        return _build_tree(parent_id, max_depth)


def device_service(client: LMClient) -> DeviceService:
    """Create a service for devices."""
    return DeviceService(client)


def device_group_service(client: LMClient) -> DeviceGroupService:
    """Create a service for device groups."""
    return DeviceGroupService(client)
