"""
Service for LogicMonitor API Tokens.

Provides operations for managing API tokens for authentication.
"""

from __future__ import annotations

from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class APITokenService(BaseService):
    """
    Service for managing LogicMonitor API Tokens.

    API tokens are used for programmatic access to the LogicMonitor API.
    Each token is associated with a specific admin user.

    Usage:
        svc = APITokenService(client)
        tokens = svc.list_for_user(admin_id)
        svc.create_for_user(admin_id, "Automation token")
    """

    @property
    def base_path(self) -> str:
        return "/setting/admins"

    def list_for_user(
        self,
        admin_id: int,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List API tokens for a specific user.

        Args:
            admin_id: Admin user ID
            max_items: Maximum items to return

        Returns:
            List of API tokens
        """
        params: dict[str, Any] = {"size": 250, "offset": 0}
        if max_items:
            return self.client.get_all(
                f"{self.base_path}/{admin_id}/apitokens",
                params,
                max_items=max_items,
            )
        return self.client.get_all(f"{self.base_path}/{admin_id}/apitokens", params)

    def get_token(self, admin_id: int, token_id: int) -> dict[str, Any]:
        """
        Get a specific API token.

        Args:
            admin_id: Admin user ID
            token_id: Token ID

        Returns:
            Token details
        """
        return self.client.get(f"{self.base_path}/{admin_id}/apitokens/{token_id}")

    def create_for_user(
        self,
        admin_id: int,
        note: str = "",
        roles: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Create an API token for a user.

        Args:
            admin_id: Admin user ID
            note: Description/note for the token
            roles: Optional list of role IDs for the token

        Returns:
            Created token (includes access ID and key)
        """
        data: dict[str, Any] = {"note": note}
        if roles:
            data["roles"] = [{"id": r} for r in roles]

        return self.client.post(
            f"{self.base_path}/{admin_id}/apitokens",
            json_data=data,
        )

    def delete_token(self, admin_id: int, token_id: int) -> dict[str, Any]:
        """
        Delete an API token.

        Args:
            admin_id: Admin user ID
            token_id: Token ID to delete

        Returns:
            Deletion response
        """
        return self.client.delete(f"{self.base_path}/{admin_id}/apitokens/{token_id}")

    def list_all_tokens(self, max_items: int | None = None) -> list[dict[str, Any]]:
        """
        List all API tokens across all users.

        Args:
            max_items: Maximum items to return

        Returns:
            List of all API tokens
        """
        params: dict[str, Any] = {"size": 250, "offset": 0}
        if max_items:
            return self.client.get_all(
                "/setting/apitokens",
                params,
                max_items=max_items,
            )
        return self.client.get_all("/setting/apitokens", params)


def api_token_service(client: LMClient) -> APITokenService:
    """Create an API token service."""
    return APITokenService(client)
