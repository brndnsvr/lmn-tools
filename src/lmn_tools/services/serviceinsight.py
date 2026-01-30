"""
Service for LogicMonitor Services (Service Insight).

Provides operations for managing service-level aggregations.
"""

from __future__ import annotations

from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class ServiceService(BaseService):
    """
    Service for managing LogicMonitor Services (Service Insight).

    Services aggregate multiple devices and components to provide
    service-level monitoring and health status.

    Usage:
        svc = ServiceService(client)
        services = svc.list()
        status = svc.get_status(service_id)
    """

    @property
    def base_path(self) -> str:
        return "/service/services"

    def search(self, query: str, max_items: int = 50) -> list[dict[str, Any]]:
        """
        Search services by name.

        Args:
            query: Search term
            max_items: Maximum items to return

        Returns:
            List of matching services
        """
        return self.list(filter=f'name~"{query}"', max_items=max_items)

    def list_by_group(
        self,
        group_id: int,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List services in a specific group.

        Args:
            group_id: Service group ID
            max_items: Maximum items to return

        Returns:
            List of services
        """
        return self.list(filter=f"groupId:{group_id}", max_items=max_items)

    def get_status(self, service_id: int) -> dict[str, Any]:
        """
        Get the current status of a service.

        Args:
            service_id: Service ID

        Returns:
            Status information
        """
        service = self.get(service_id)
        data = service.get("data", service) if "data" in service else service
        return {
            "id": service_id,
            "name": data.get("name"),
            "status": data.get("status"),
            "alertStatus": data.get("alertStatus"),
            "sdtStatus": data.get("sdtStatus"),
            "alertDisableStatus": data.get("alertDisableStatus"),
        }

    def get_members(self, service_id: int) -> list[dict[str, Any]]:
        """
        Get the members (devices/instances) of a service.

        Args:
            service_id: Service ID

        Returns:
            List of service members
        """
        service = self.get(service_id)
        data = service.get("data", service) if "data" in service else service
        members: list[dict[str, Any]] = data.get("members", [])
        return members

    def create_simple(
        self,
        name: str,
        group_id: int = 1,
        description: str = "",
        device_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Create a service with simple parameters.

        Args:
            name: Service name
            group_id: Service group ID
            description: Optional description
            device_ids: List of device IDs to include

        Returns:
            Created service
        """
        data: dict[str, Any] = {
            "name": name,
            "groupId": group_id,
            "description": description,
        }
        if device_ids:
            data["members"] = [{"type": "device", "id": did} for did in device_ids]

        return self.create(data)

    def add_device(self, service_id: int, device_id: int) -> dict[str, Any]:
        """
        Add a device to a service.

        Args:
            service_id: Service ID
            device_id: Device ID to add

        Returns:
            Updated service
        """
        current = self.get(service_id)
        data = current.get("data", current) if "data" in current else current
        members = data.get("members", [])
        members.append({"type": "device", "id": device_id})
        return self.update(service_id, {"members": members})


class ServiceGroupService(BaseService):
    """
    Service for managing LogicMonitor Service Groups.

    Usage:
        svc = ServiceGroupService(client)
        groups = svc.list()
    """

    @property
    def base_path(self) -> str:
        return "/service/groups"

    def get_children(self, parent_id: int) -> list[dict[str, Any]]:
        """Get child groups of a parent group."""
        return self.list(filter=f"parentId:{parent_id}")

    def get_services(self, group_id: int) -> list[dict[str, Any]]:
        """Get services in a group."""
        service_svc = ServiceService(self.client)
        return service_svc.list_by_group(group_id)


def service_service(client: LMClient) -> ServiceService:
    """Create a service service."""
    return ServiceService(client)


def service_group_service(client: LMClient) -> ServiceGroupService:
    """Create a service group service."""
    return ServiceGroupService(client)
