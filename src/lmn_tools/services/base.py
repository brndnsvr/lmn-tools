"""
Base service class for LogicMonitor API operations.

Provides common CRUD operations that can be inherited by
resource-specific service classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lmn_tools.api.client import LMClient


class BaseService(ABC):
    """
    Base class for LM API service operations.

    Provides standard CRUD operations (list, get, create, update, delete)
    that work with any API resource. Subclasses define the base_path.

    Usage:
        class DeviceService(BaseService):
            @property
            def base_path(self) -> str:
                return "/device/devices"

        svc = DeviceService(client)
        devices = svc.list(filter="displayName~*prod*")
    """

    def __init__(self, client: LMClient):
        """
        Initialize service with an authenticated API client.

        Args:
            client: Configured LMClient instance
        """
        self.client = client

    @property
    @abstractmethod
    def base_path(self) -> str:
        """Return the base API path for this resource (e.g., '/device/devices')."""
        ...

    def list(
        self,
        filter: str | None = None,
        fields: list[str] | None = None,
        size: int = 250,
        offset: int = 0,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List resources with optional filtering and pagination.

        Args:
            filter: LM filter string (e.g., 'displayName~*prod*')
            fields: List of fields to return
            size: Page size (default 250)
            offset: Starting offset
            max_items: Maximum items to return (None for all)

        Returns:
            List of resource dictionaries
        """
        params: dict[str, Any] = {"size": size, "offset": offset}
        if filter:
            params["filter"] = filter
        if fields:
            params["fields"] = ",".join(fields)

        if max_items:
            return self.client.get_all(self.base_path, params, max_items=max_items)
        return self.client.get_all(self.base_path, params)

    def get(self, id: int) -> dict[str, Any]:
        """
        Get a single resource by ID.

        Args:
            id: Resource ID

        Returns:
            Resource dictionary
        """
        return self.client.get(f"{self.base_path}/{id}")

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new resource.

        Args:
            data: Resource data dictionary

        Returns:
            Created resource dictionary (with ID)
        """
        return self.client.post(self.base_path, json_data=data)

    def update(self, id: int, data: dict[str, Any]) -> dict[str, Any]:
        """
        Update an existing resource.

        Args:
            id: Resource ID
            data: Fields to update

        Returns:
            Updated resource dictionary
        """
        return self.client.patch(f"{self.base_path}/{id}", json_data=data)

    def delete(self, id: int) -> dict[str, Any]:
        """
        Delete a resource.

        Args:
            id: Resource ID

        Returns:
            Deletion response
        """
        return self.client.delete(f"{self.base_path}/{id}")

    def find_by_name(
        self,
        name: str,
        name_field: str = "name",
        exact: bool = True,
    ) -> dict[str, Any] | None:
        """
        Find a resource by name.

        Args:
            name: Name to search for
            name_field: Field name to search (default: 'name')
            exact: Use exact match (True) or contains match (False)

        Returns:
            Resource dictionary or None if not found
        """
        if exact:
            filter_str = f'{name_field}:"{name}"'
        else:
            filter_str = f"{name_field}~*{name}*"

        results = self.list(filter=filter_str, max_items=1)
        return results[0] if results else None

    def count(self, filter: str | None = None) -> int:
        """
        Count resources matching a filter.

        Args:
            filter: Optional filter string

        Returns:
            Total count of matching resources
        """
        params: dict[str, Any] = {"size": 1, "offset": 0}
        if filter:
            params["filter"] = filter

        response = self.client.get(self.base_path, params)
        return response.get("data", {}).get("total", 0)

    def exists(self, id: int) -> bool:
        """
        Check if a resource exists.

        Args:
            id: Resource ID

        Returns:
            True if resource exists
        """
        try:
            self.get(id)
            return True
        except Exception:
            return False
