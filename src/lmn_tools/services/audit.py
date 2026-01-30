"""
Service for LogicMonitor Audit Logs.

Provides operations for querying audit/access logs.
"""

from __future__ import annotations

import time
from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class AuditLogService(BaseService):
    """
    Service for querying LogicMonitor Audit Logs.

    Audit logs track user actions and system changes for compliance
    and security monitoring.

    Usage:
        svc = AuditLogService(client)
        logs = svc.list()
        logs = svc.list_by_user("admin@example.com")
    """

    @property
    def base_path(self) -> str:
        return "/setting/accesslogs"

    def list_by_user(
        self,
        username: str,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List audit logs for a specific user.

        Args:
            username: Username to filter by
            max_items: Maximum items to return

        Returns:
            List of audit logs
        """
        return self.list(filter=f'username:"{username}"', max_items=max_items)

    def list_by_action(
        self,
        action: str,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List audit logs by action type.

        Args:
            action: Action type (e.g., "add", "update", "delete")
            max_items: Maximum items to return

        Returns:
            List of audit logs
        """
        return self.list(filter=f'description~"{action}"', max_items=max_items)

    def list_by_resource(
        self,
        resource_type: str,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List audit logs for a resource type.

        Args:
            resource_type: Resource type (e.g., "device", "dashboard")
            max_items: Maximum items to return

        Returns:
            List of audit logs
        """
        return self.list(filter=f'description~"{resource_type}"', max_items=max_items)

    def list_by_time_range(
        self,
        start_time: int,
        end_time: int | None = None,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List audit logs within a time range.

        Args:
            start_time: Start timestamp (epoch ms)
            end_time: End timestamp (epoch ms), defaults to now
            max_items: Maximum items to return

        Returns:
            List of audit logs
        """
        if end_time is None:
            end_time = int(time.time() * 1000)

        filter_str = f"happenedOn>{start_time},happenedOn<{end_time}"
        return self.list(filter=filter_str, max_items=max_items)

    def list_recent(
        self,
        hours: int = 24,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List recent audit logs.

        Args:
            hours: Number of hours to look back
            max_items: Maximum items to return

        Returns:
            List of audit logs
        """
        now = int(time.time() * 1000)
        start_time = now - (hours * 60 * 60 * 1000)
        return self.list_by_time_range(start_time, now, max_items)

    def list_logins(self, max_items: int | None = None) -> list[dict[str, Any]]:
        """List login events."""
        return self.list(filter='description~"login"', max_items=max_items)

    def list_failed_logins(self, max_items: int | None = None) -> list[dict[str, Any]]:
        """List failed login attempts."""
        return self.list(filter='description~"failed login"', max_items=max_items)


def audit_log_service(client: LMClient) -> AuditLogService:
    """Create an audit log service."""
    return AuditLogService(client)
