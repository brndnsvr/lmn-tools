"""
Tests for RecipientGroupService.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lmn_tools.services.notifications import RecipientGroupService


@pytest.fixture
def service(mock_client: MagicMock) -> RecipientGroupService:
    """Create RecipientGroupService with mock client."""
    return RecipientGroupService(mock_client)


class TestRecipientGroupService:
    """Tests for RecipientGroupService."""

    def test_base_path(self, service: RecipientGroupService) -> None:
        """Test base_path property."""
        assert service.base_path == "/setting/recipientgroups"

    def test_search(self, service: RecipientGroupService, mock_client: MagicMock) -> None:
        """Test searching recipient groups by name."""
        mock_client.get_all.return_value = [{"id": 1, "groupName": "Oncall"}]

        result = service.search("Oncall")

        mock_client.get_all.assert_called_once()
        call_args = mock_client.get_all.call_args
        assert 'groupName~"Oncall"' in call_args[0][1]["filter"]
        assert len(result) == 1

    def test_get_recipients(self, service: RecipientGroupService, mock_client: MagicMock) -> None:
        """Test getting recipients for a group."""
        mock_client.get.return_value = {
            "id": 123,
            "groupName": "Oncall",
            "recipients": [
                {"type": "ADMIN", "method": "email", "addr": "admin@example.com"},
                {"type": "ADMIN", "method": "email", "addr": "ops@example.com"},
            ],
        }

        result = service.get_recipients(123)

        mock_client.get.assert_called_once_with("/setting/recipientgroups/123")
        assert len(result) == 2
        assert result[0]["addr"] == "admin@example.com"

    def test_get_recipients_with_data_wrapper(
        self, service: RecipientGroupService, mock_client: MagicMock
    ) -> None:
        """Test getting recipients when response has data wrapper."""
        mock_client.get.return_value = {
            "data": {"recipients": [{"type": "ADMIN", "addr": "test@example.com"}]}
        }

        result = service.get_recipients(123)

        assert len(result) == 1

    def test_get_recipients_empty(
        self, service: RecipientGroupService, mock_client: MagicMock
    ) -> None:
        """Test getting recipients when group has none."""
        mock_client.get.return_value = {"id": 123, "groupName": "Empty", "recipients": []}

        result = service.get_recipients(123)

        assert result == []

    def test_create_simple(self, service: RecipientGroupService, mock_client: MagicMock) -> None:
        """Test creating a recipient group with simple parameters."""
        mock_client.post.return_value = {"id": 456, "groupName": "NewGroup"}

        service.create_simple(
            name="NewGroup",
            description="Test group",
            recipients=[{"type": "ARBITRARY", "addr": "test@example.com"}],
        )

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["groupName"] == "NewGroup"
        assert data["description"] == "Test group"
        assert len(data["recipients"]) == 1

    def test_create_simple_no_recipients(
        self, service: RecipientGroupService, mock_client: MagicMock
    ) -> None:
        """Test creating a group without recipients."""
        mock_client.post.return_value = {"id": 457}

        service.create_simple("MinimalGroup")

        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["recipients"] == []

    def test_add_email_recipient(
        self, service: RecipientGroupService, mock_client: MagicMock
    ) -> None:
        """Test adding an email recipient to a group."""
        mock_client.get.return_value = {
            "id": 123,
            "groupName": "Oncall",
            "recipients": [{"type": "ADMIN", "method": "email", "addr": "existing@example.com"}],
        }
        mock_client.patch.return_value = {"id": 123}

        service.add_email_recipient(123, "new@example.com")

        mock_client.patch.assert_called_once()
        call_args = mock_client.patch.call_args
        data = call_args[1]["json_data"]
        assert len(data["recipients"]) == 2
        new_recipient = data["recipients"][1]
        assert new_recipient["type"] == "ARBITRARY"
        assert new_recipient["method"] == "email"
        assert new_recipient["addr"] == "new@example.com"

    def test_add_email_recipient_custom_method(
        self, service: RecipientGroupService, mock_client: MagicMock
    ) -> None:
        """Test adding a recipient with custom method."""
        mock_client.get.return_value = {"id": 123, "recipients": []}
        mock_client.patch.return_value = {"id": 123}

        service.add_email_recipient(123, "test@example.com", method="sms")

        call_args = mock_client.patch.call_args
        data = call_args[1]["json_data"]
        assert data["recipients"][0]["method"] == "sms"

    def test_add_admin_recipient(
        self, service: RecipientGroupService, mock_client: MagicMock
    ) -> None:
        """Test adding an admin user as a recipient."""
        mock_client.get.return_value = {"id": 123, "recipients": []}
        mock_client.patch.return_value = {"id": 123}

        service.add_admin_recipient(123, admin_id=100)

        call_args = mock_client.patch.call_args
        data = call_args[1]["json_data"]
        assert len(data["recipients"]) == 1
        new_recipient = data["recipients"][0]
        assert new_recipient["type"] == "ADMIN"
        assert new_recipient["admin"] == 100
        assert new_recipient["method"] == "email"
