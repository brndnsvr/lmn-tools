"""
Service for LogicMonitor Integrations.

Provides operations for managing third-party integrations (PagerDuty, Slack, etc).
"""

from __future__ import annotations

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class IntegrationService(BaseService):
    """Service for managing LogicMonitor integrations."""

    @property
    def base_path(self) -> str:
        return "/setting/integrations"


def integration_service(client: LMClient) -> IntegrationService:
    """Create an IntegrationService instance."""
    return IntegrationService(client)
