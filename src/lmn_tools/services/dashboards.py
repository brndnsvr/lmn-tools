"""
Service for LogicMonitor Dashboards and Dashboard Groups.

Provides operations for managing dashboards and their widgets.
"""

from __future__ import annotations

from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class DashboardService(BaseService):
    """
    Service for managing LogicMonitor dashboards.

    Usage:
        svc = DashboardService(client)
        dashboards = svc.list()
        widgets = svc.get_widgets(dashboard_id)
    """

    @property
    def base_path(self) -> str:
        return "/dashboard/dashboards"

    def get_widgets(self, dashboard_id: int) -> list[dict[str, Any]]:
        """
        Get widgets for a dashboard.

        Args:
            dashboard_id: Dashboard ID

        Returns:
            List of widgets
        """
        response = self.client.get(f"{self.base_path}/{dashboard_id}/widgets")
        items = response.get("items", response.get("data", {}).get("items", []))
        if isinstance(items, list):
            return items
        return []

    def list_by_group(self, group_id: int, max_items: int | None = None) -> list[dict[str, Any]]:
        """List dashboards in a specific group."""
        return self.list(filter=f"groupId:{group_id}", max_items=max_items)

    def search(self, query: str, max_items: int = 50) -> list[dict[str, Any]]:
        """Search dashboards by name."""
        return self.list(filter=f'name~"{query}"', max_items=max_items)

    def clone(
        self,
        dashboard_id: int,
        new_name: str,
        group_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Clone a dashboard.

        Args:
            dashboard_id: ID of dashboard to clone
            new_name: Name for the new dashboard
            group_id: Optional group ID for the cloned dashboard

        Returns:
            Cloned dashboard
        """
        response = self.get(dashboard_id)
        original = response.get("data", response) if "data" in response else response

        # Create a copy with new name
        new_dashboard = original.copy()
        new_dashboard["name"] = new_name
        new_dashboard.pop("id", None)
        new_dashboard.pop("groupId", None)

        if group_id:
            new_dashboard["groupId"] = group_id
        elif "groupId" in original:
            new_dashboard["groupId"] = original["groupId"]

        return self.create(new_dashboard)

    def export_json(self, dashboard_id: int) -> dict[str, Any]:
        """Export dashboard as JSON (includes widgets)."""
        response = self.get(dashboard_id)
        dashboard = response.get("data", response) if "data" in response else response
        dashboard["widgets"] = self.get_widgets(dashboard_id)
        return dashboard


class DashboardGroupService(BaseService):
    """
    Service for managing LogicMonitor dashboard groups.

    Usage:
        svc = DashboardGroupService(client)
        groups = svc.list()
        children = svc.get_children(parent_id)
    """

    @property
    def base_path(self) -> str:
        return "/dashboard/groups"

    def get_children(self, parent_id: int) -> list[dict[str, Any]]:
        """Get child groups of a parent group."""
        return self.list(filter=f"parentId:{parent_id}")

    def get_by_path(self, path: str) -> dict[str, Any] | None:
        """
        Find a dashboard group by its full path.

        Args:
            path: Full path like "Parent/Child/Grandchild"

        Returns:
            Group dict or None if not found
        """
        results = self.list(filter=f'fullPath:"{path}"', max_items=1)
        return results[0] if results else None

    def get_dashboards(self, group_id: int) -> list[dict[str, Any]]:
        """Get dashboards in a group."""
        dashboard_svc = DashboardService(self.client)
        return dashboard_svc.list_by_group(group_id)


def dashboard_service(client: LMClient) -> DashboardService:
    """Create a dashboard service."""
    return DashboardService(client)


def dashboard_group_service(client: LMClient) -> DashboardGroupService:
    """Create a dashboard group service."""
    return DashboardGroupService(client)


class WidgetService(BaseService):
    """
    Service for managing LogicMonitor dashboard widgets.

    Usage:
        svc = WidgetService(client)
        widget = svc.get(widget_id)
        svc.update(widget_id, {"name": "New Name"})
    """

    @property
    def base_path(self) -> str:
        return "/dashboard/widgets"

    def list_by_dashboard(self, dashboard_id: int) -> list[dict[str, Any]]:
        """
        List widgets for a dashboard.

        Args:
            dashboard_id: Dashboard ID

        Returns:
            List of widgets
        """
        response = self.client.get(f"/dashboard/dashboards/{dashboard_id}/widgets")
        items = response.get("items", response.get("data", {}).get("items", []))
        if isinstance(items, list):
            return items
        return []

    def create_for_dashboard(
        self,
        dashboard_id: int,
        widget_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create a widget on a dashboard.

        Args:
            dashboard_id: Dashboard ID
            widget_data: Widget configuration

        Returns:
            Created widget
        """
        widget_data["dashboardId"] = dashboard_id
        return self.client.post(
            f"/dashboard/dashboards/{dashboard_id}/widgets",
            json_data=widget_data,
        )

    def clone(
        self,
        widget_id: int,
        target_dashboard_id: int,
    ) -> dict[str, Any]:
        """
        Clone a widget to another dashboard.

        Args:
            widget_id: Widget ID to clone
            target_dashboard_id: Target dashboard ID

        Returns:
            Cloned widget
        """
        response = self.get(widget_id)
        original = response.get("data", response) if "data" in response else response

        # Create a copy without ID
        new_widget = original.copy()
        new_widget.pop("id", None)
        new_widget["dashboardId"] = target_dashboard_id

        return self.create_for_dashboard(target_dashboard_id, new_widget)


def widget_service(client: LMClient) -> WidgetService:
    """Create a widget service."""
    return WidgetService(client)
