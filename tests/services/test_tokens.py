"""
Tests for APITokenService.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lmn_tools.services.tokens import APITokenService


@pytest.fixture
def service(mock_client: MagicMock) -> APITokenService:
    """Create APITokenService with mock client."""
    return APITokenService(mock_client)


class TestAPITokenService:
    """Tests for APITokenService."""

    def test_base_path(self, service: APITokenService) -> None:
        """Test base_path property."""
        assert service.base_path == "/setting/admins"

    def test_list_for_user(self, service: APITokenService, mock_client: MagicMock) -> None:
        """Test listing API tokens for a user."""
        mock_client.get_all.return_value = [
            {"id": 1, "accessId": "abc123", "note": "CI/CD"},
            {"id": 2, "accessId": "def456", "note": "Automation"},
        ]

        result = service.list_for_user(100)

        mock_client.get_all.assert_called_once()
        call_args = mock_client.get_all.call_args
        assert call_args[0][0] == "/setting/admins/100/apitokens"
        assert len(result) == 2
        assert result[0]["accessId"] == "abc123"

    def test_list_for_user_with_max_items(
        self, service: APITokenService, mock_client: MagicMock
    ) -> None:
        """Test list_for_user with max_items."""
        mock_client.get_all.return_value = []

        service.list_for_user(100, max_items=10)

        call_args = mock_client.get_all.call_args
        assert call_args[1]["max_items"] == 10

    def test_get_token(self, service: APITokenService, mock_client: MagicMock) -> None:
        """Test getting a specific token."""
        mock_client.get.return_value = {
            "id": 1,
            "accessId": "abc123",
            "note": "CI/CD",
            "createdOn": 1700000000000,
        }

        result = service.get_token(100, 1)

        mock_client.get.assert_called_once_with("/setting/admins/100/apitokens/1")
        assert result["accessId"] == "abc123"

    def test_create_for_user(self, service: APITokenService, mock_client: MagicMock) -> None:
        """Test creating an API token."""
        mock_client.post.return_value = {
            "id": 3,
            "accessId": "new123",
            "accessKey": "secret-key-value",
            "note": "New Token",
        }

        result = service.create_for_user(100, "New Token")

        mock_client.post.assert_called_once_with(
            "/setting/admins/100/apitokens",
            json_data={"note": "New Token"},
        )
        assert result["accessId"] == "new123"
        assert result["accessKey"] == "secret-key-value"

    def test_create_for_user_empty_note(
        self, service: APITokenService, mock_client: MagicMock
    ) -> None:
        """Test creating a token with empty note."""
        mock_client.post.return_value = {"id": 4, "accessId": "xyz789"}

        service.create_for_user(100, "")

        call_args = mock_client.post.call_args
        assert call_args[1]["json_data"]["note"] == ""

    def test_create_for_user_with_roles(
        self, service: APITokenService, mock_client: MagicMock
    ) -> None:
        """Test creating a token with roles."""
        mock_client.post.return_value = {"id": 5}

        service.create_for_user(100, "RoleToken", roles=[1, 2, 3])

        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["roles"] == [{"id": 1}, {"id": 2}, {"id": 3}]

    def test_delete_token(self, service: APITokenService, mock_client: MagicMock) -> None:
        """Test deleting an API token."""
        mock_client.delete.return_value = {}

        service.delete_token(100, 1)

        mock_client.delete.assert_called_once_with("/setting/admins/100/apitokens/1")

    def test_list_all_tokens(self, service: APITokenService, mock_client: MagicMock) -> None:
        """Test listing all API tokens across all users."""
        mock_client.get_all.return_value = [
            {"id": 1, "accessId": "abc", "adminId": 100},
            {"id": 2, "accessId": "def", "adminId": 101},
        ]

        result = service.list_all_tokens()

        mock_client.get_all.assert_called_once()
        call_args = mock_client.get_all.call_args
        assert call_args[0][0] == "/setting/apitokens"
        assert len(result) == 2

    def test_list_all_tokens_with_max_items(
        self, service: APITokenService, mock_client: MagicMock
    ) -> None:
        """Test list_all_tokens with max_items limit."""
        mock_client.get_all.return_value = []

        service.list_all_tokens(max_items=50)

        call_args = mock_client.get_all.call_args
        assert call_args[1]["max_items"] == 50
