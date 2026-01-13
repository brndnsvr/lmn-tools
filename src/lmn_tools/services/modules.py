"""
Service for LogicMonitor LogicModules (DataSources, PropertySources, etc).

Provides operations for managing all LogicModule types through a unified interface.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class ModuleType(str, Enum):
    """LogicModule types."""

    DATASOURCE = "datasource"
    PROPERTYSOURCE = "propertysource"
    EVENTSOURCE = "eventsource"
    CONFIGSOURCE = "configsource"
    TOPOLOGYSOURCE = "topologysource"


# Mapping of module types to API paths
MODULE_PATHS: dict[ModuleType, str] = {
    ModuleType.DATASOURCE: "/setting/datasources",
    ModuleType.PROPERTYSOURCE: "/setting/propertyrules",
    ModuleType.EVENTSOURCE: "/setting/eventsources",
    ModuleType.CONFIGSOURCE: "/setting/configsources",
    ModuleType.TOPOLOGYSOURCE: "/setting/topologysources",
}


class LogicModuleService(BaseService):
    """
    Service for managing LogicModules (DataSources, PropertySources, etc).

    Supports all five LogicModule types through a unified interface,
    with specialized methods for DataSource sub-resources (datapoints, graphs).

    Usage:
        # DataSources
        ds_svc = LogicModuleService(client, ModuleType.DATASOURCE)
        datasources = ds_svc.list(filter="name~Infinera")

        # PropertySources
        ps_svc = LogicModuleService(client, ModuleType.PROPERTYSOURCE)
        propertysources = ps_svc.list()

        # Get DataSource datapoints
        datapoints = ds_svc.get_datapoints(21328173)
    """

    def __init__(self, client: LMClient, module_type: ModuleType | str = ModuleType.DATASOURCE):
        """
        Initialize the LogicModule service.

        Args:
            client: Configured LMClient instance
            module_type: Type of LogicModule to manage
        """
        super().__init__(client)
        if isinstance(module_type, str):
            module_type = ModuleType(module_type.lower())
        self.module_type = module_type
        self._base_path = MODULE_PATHS[module_type]

    @property
    def base_path(self) -> str:
        """Return the base API path for this module type."""
        return self._base_path

    # =========================================================================
    # DataSource-specific methods
    # =========================================================================

    def get_datapoints(self, module_id: int) -> list[dict[str, Any]]:
        """
        Get datapoints for a DataSource.

        Args:
            module_id: DataSource ID

        Returns:
            List of datapoint dictionaries
        """
        response = self.client.get(f"{self.base_path}/{module_id}/datapoints")
        items: list[dict[str, Any]] = response.get("items", response.get("data", {}).get("items", []))
        return items

    def get_graphs(self, module_id: int) -> list[dict[str, Any]]:
        """
        Get graphs for a DataSource.

        Args:
            module_id: DataSource ID

        Returns:
            List of graph dictionaries
        """
        response = self.client.get(f"{self.base_path}/{module_id}/graphs")
        items: list[dict[str, Any]] = response.get("items", response.get("data", {}).get("items", []))
        return items

    def get_overview_graphs(self, module_id: int) -> list[dict[str, Any]]:
        """
        Get overview graphs for a DataSource.

        Args:
            module_id: DataSource ID

        Returns:
            List of overview graph dictionaries
        """
        response = self.client.get(f"{self.base_path}/{module_id}/ographs")
        items: list[dict[str, Any]] = response.get("items", response.get("data", {}).get("items", []))
        return items

    def get_audit_log(self, module_id: int) -> list[dict[str, Any]]:
        """
        Get audit log for a LogicModule.

        Args:
            module_id: LogicModule ID

        Returns:
            List of audit log entries
        """
        response = self.client.get(f"{self.base_path}/{module_id}/audit")
        items: list[dict[str, Any]] = response.get("items", response.get("data", {}).get("items", []))
        return items

    # =========================================================================
    # Export/Import operations
    # =========================================================================

    def export_json(self, module_id: int) -> dict[str, Any]:
        """
        Export a LogicModule as JSON.

        Args:
            module_id: LogicModule ID

        Returns:
            Full module definition as dictionary
        """
        return self.get(module_id)

    def clone(self, module_id: int, new_name: str, new_display_name: str | None = None) -> dict[str, Any]:
        """
        Clone a LogicModule with a new name.

        Args:
            module_id: Source module ID
            new_name: Name for the cloned module
            new_display_name: Display name (defaults to new_name)

        Returns:
            Created module dictionary
        """
        original = self.export_json(module_id)

        # Remove ID and timestamps
        original.pop("id", None)
        original.pop("checksum", None)
        original.pop("registeredOn", None)
        original.pop("modifiedOn", None)
        original.pop("version", None)

        # Set new names
        original["name"] = new_name
        original["displayName"] = new_display_name or new_name

        return self.create(original)

    # =========================================================================
    # Search and filter helpers
    # =========================================================================

    def find_by_display_name(self, display_name: str, exact: bool = True) -> dict[str, Any] | None:
        """
        Find a LogicModule by display name.

        Args:
            display_name: Display name to search for
            exact: Use exact match (True) or contains match (False)

        Returns:
            Module dictionary or None if not found
        """
        return self.find_by_name(display_name, name_field="displayName", exact=exact)

    def list_by_group(self, group: str) -> list[dict[str, Any]]:
        """
        List LogicModules in a specific group.

        Args:
            group: Group name

        Returns:
            List of modules in the group
        """
        return self.list(filter=f'group:"{group}"')

    def list_by_collect_method(self, method: str) -> list[dict[str, Any]]:
        """
        List DataSources by collection method.

        Args:
            method: Collection method (e.g., 'script', 'snmp', 'webservice')

        Returns:
            List of DataSources using that method
        """
        if self.module_type != ModuleType.DATASOURCE:
            return []
        return self.list(filter=f'collectMethod:"{method}"')

    def list_multi_instance(self) -> list[dict[str, Any]]:
        """
        List DataSources that have multiple instances.

        Returns:
            List of multi-instance DataSources
        """
        if self.module_type != ModuleType.DATASOURCE:
            return []
        return self.list(filter="hasMultiInstances:true")

    def search(self, query: str) -> list[dict[str, Any]]:
        """
        Search LogicModules by name or display name.

        Args:
            query: Search term (partial match)

        Returns:
            List of matching modules
        """
        # Search both name and displayName
        results = self.list(filter=f"name~*{query}*")
        display_results = self.list(filter=f"displayName~*{query}*")

        # Merge and deduplicate by ID
        seen_ids = {m["id"] for m in results}
        for m in display_results:
            if m["id"] not in seen_ids:
                results.append(m)
                seen_ids.add(m["id"])

        return results


# =========================================================================
# Convenience factory functions
# =========================================================================


def datasource_service(client: LMClient) -> LogicModuleService:
    """Create a service for DataSources."""
    return LogicModuleService(client, ModuleType.DATASOURCE)


def propertysource_service(client: LMClient) -> LogicModuleService:
    """Create a service for PropertySources."""
    return LogicModuleService(client, ModuleType.PROPERTYSOURCE)


def eventsource_service(client: LMClient) -> LogicModuleService:
    """Create a service for EventSources."""
    return LogicModuleService(client, ModuleType.EVENTSOURCE)


def configsource_service(client: LMClient) -> LogicModuleService:
    """Create a service for ConfigSources."""
    return LogicModuleService(client, ModuleType.CONFIGSOURCE)


def topologysource_service(client: LMClient) -> LogicModuleService:
    """Create a service for TopologySources."""
    return LogicModuleService(client, ModuleType.TOPOLOGYSOURCE)
