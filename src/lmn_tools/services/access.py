"""
Service for LogicMonitor Access Groups (RBAC).

Provides operations for managing role-based access control groups.
"""

from __future__ import annotations

from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class AccessGroupService(BaseService):
    """
    Service for managing LogicMonitor Access Groups.

    Access groups control what resources users can see and modify
    based on device groups, websites, and dashboards.

    Usage:
        svc = AccessGroupService(client)
        groups = svc.list()
        svc.create({"name": "Team Access", ...})
    """

    @property
    def base_path(self) -> str:
        return "/setting/accessgroup"

    def search(self, query: str, max_items: int = 50) -> list[dict[str, Any]]:
        """
        Search access groups by name.

        Args:
            query: Search term
            max_items: Maximum items to return

        Returns:
            List of matching access groups
        """
        return self.list(filter=f'name~"{query}"', max_items=max_items)

    def get_device_groups(self, access_group_id: int) -> list[dict[str, Any]]:
        """
        Get device groups associated with an access group.

        Args:
            access_group_id: Access group ID

        Returns:
            List of device group entries
        """
        group = self.get(access_group_id)
        data = group.get("data", group) if "data" in group else group
        device_groups: list[dict[str, Any]] = data.get("deviceGroups", [])
        return device_groups

    def add_device_group(
        self,
        access_group_id: int,
        device_group_id: int,
        permission: str = "read",
    ) -> dict[str, Any]:
        """
        Add a device group to an access group.

        Args:
            access_group_id: Access group ID
            device_group_id: Device group ID to add
            permission: Permission level (read, write, manage)

        Returns:
            Updated access group
        """
        group = self.get(access_group_id)
        data = group.get("data", group) if "data" in group else group
        device_groups = data.get("deviceGroups", [])
        device_groups.append({
            "id": device_group_id,
            "permission": permission,
        })
        return self.update(access_group_id, {"deviceGroups": device_groups})

    def create_simple(
        self,
        name: str,
        description: str = "",
        device_group_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Create an access group with simple parameters.

        Args:
            name: Access group name
            description: Optional description
            device_group_ids: List of device group IDs to include

        Returns:
            Created access group
        """
        data: dict[str, Any] = {
            "name": name,
            "description": description,
        }
        if device_group_ids:
            data["deviceGroups"] = [{"id": gid, "permission": "read"} for gid in device_group_ids]

        return self.create(data)


def access_group_service(client: LMClient) -> AccessGroupService:
    """Create an access group service."""
    return AccessGroupService(client)
