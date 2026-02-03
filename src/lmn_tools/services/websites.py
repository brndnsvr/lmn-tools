"""
Service for LogicMonitor Websites (Synthetic Monitoring).

Provides operations for managing website monitors and checks.
"""

from __future__ import annotations

from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class WebsiteService(BaseService):
    """Service for managing LogicMonitor website monitors."""

    @property
    def base_path(self) -> str:
        return "/website/websites"

    def list_checks(self, website_id: int, **kwargs: Any) -> list[dict[str, Any]]:
        """List checks for a website."""
        return self.client.get(f"{self.base_path}/{website_id}/checkpoints", **kwargs)

    def list_by_group(self, group_id: int, **kwargs: Any) -> list[dict[str, Any]]:
        """List websites in a group."""
        return self.client.get(
            self.base_path,
            params={"filter": f"groupId:{group_id}", **kwargs},
        )


def website_service(client: LMClient) -> WebsiteService:
    """Create a WebsiteService instance."""
    return WebsiteService(client)
