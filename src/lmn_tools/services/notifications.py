"""
Service for LogicMonitor Recipient Groups.

Provides operations for managing alert notification recipients.
"""

from __future__ import annotations

from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class RecipientGroupService(BaseService):
    """
    Service for managing LogicMonitor Recipient Groups.

    Recipient groups define collections of contacts that receive
    alert notifications.

    Usage:
        svc = RecipientGroupService(client)
        groups = svc.list()
        svc.create({"groupName": "Ops Team", "recipients": [...]})
    """

    @property
    def base_path(self) -> str:
        return "/setting/recipientgroups"

    def search(self, query: str, max_items: int = 50) -> list[dict[str, Any]]:
        """
        Search recipient groups by name.

        Args:
            query: Search term
            max_items: Maximum items to return

        Returns:
            List of matching recipient groups
        """
        return self.list(filter=f'groupName~"{query}"', max_items=max_items)

    def create_simple(
        self,
        name: str,
        description: str = "",
        recipients: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Create a recipient group with simple parameters.

        Args:
            name: Group name
            description: Optional description
            recipients: List of recipient dictionaries

        Returns:
            Created recipient group
        """
        data: dict[str, Any] = {
            "groupName": name,
            "description": description,
            "recipients": recipients or [],
        }
        return self.create(data)

    def add_email_recipient(
        self,
        group_id: int,
        email: str,
        method: str = "email",
    ) -> dict[str, Any]:
        """
        Add an email recipient to a group.

        Args:
            group_id: Recipient group ID
            email: Email address
            method: Contact method (default: email)

        Returns:
            Updated recipient group
        """
        group = self.get(group_id)
        data = group.get("data", group) if "data" in group else group
        recipients = data.get("recipients", [])
        recipients.append({
            "type": "ARBITRARY",
            "method": method,
            "addr": email,
        })
        return self.update(group_id, {"recipients": recipients})

    def add_admin_recipient(
        self,
        group_id: int,
        admin_id: int,
        method: str = "email",
    ) -> dict[str, Any]:
        """
        Add an admin user as a recipient.

        Args:
            group_id: Recipient group ID
            admin_id: Admin user ID
            method: Contact method (default: email)

        Returns:
            Updated recipient group
        """
        group = self.get(group_id)
        data = group.get("data", group) if "data" in group else group
        recipients = data.get("recipients", [])
        recipients.append({
            "type": "ADMIN",
            "method": method,
            "admin": admin_id,
        })
        return self.update(group_id, {"recipients": recipients})

    def get_recipients(self, group_id: int) -> list[dict[str, Any]]:
        """
        Get the list of recipients in a group.

        Args:
            group_id: Recipient group ID

        Returns:
            List of recipient dictionaries
        """
        group = self.get(group_id)
        data = group.get("data", group) if "data" in group else group
        recipients: list[dict[str, Any]] = data.get("recipients", [])
        return recipients


def recipient_group_service(client: LMClient) -> RecipientGroupService:
    """Create a recipient group service."""
    return RecipientGroupService(client)
